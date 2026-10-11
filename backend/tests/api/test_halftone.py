"""Tests de los endpoints de semitonos (Utilidades)."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from PIL import Image

from tests.api.conftest import wait_until


def _write_png(path: Path, size: tuple[int, int] = (64, 48)) -> Path:
    """Imagen con variación tonal para que el halftone produzca puntos y transparencia."""
    img = Image.new("RGB", size)
    px = img.load()
    w, h = size
    for y in range(h):
        for x in range(w):
            px[x, y] = (x * 255 // (w - 1), y * 255 // (h - 1), 120)
    img.save(path)
    return path


def _wait_for_terminal(client, job_id: str) -> dict:
    def is_done() -> bool:
        return client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed", "cancelled"}

    assert wait_until(is_done), "el job de halftone debería resolverse rápido"
    return client.get(f"/api/jobs/{job_id}").json()


def test_halftone_export_reaches_succeeded_with_transparent_png(client, tmp_path) -> None:
    src = _write_png(tmp_path / "src.png")
    response = client.post(
        "/api/utilities/halftone",
        json={"input_path": str(src), "halftone_method": "halftone", "screen_frequency": 35},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert response.json()["status"] == "queued"

    final = _wait_for_terminal(client, job_id)
    assert final["status"] == "succeeded"
    assert final["result"]["image_url"].startswith("/output/halftone/")
    assert final["result"]["output_path"].endswith(".png")

    # La salida es un PNG RGBA con alpha y DPI 300 (fijo, como el Gradio).
    # PNG guarda la resolución como px/metro entero, así que 300 hace round-trip
    # a ~299.9994: se compara redondeado.
    out = Image.open(final["result"]["output_path"])
    assert out.mode == "RGBA"
    dpi_x, dpi_y = out.info.get("dpi")
    assert round(dpi_x) == 300 and round(dpi_y) == 300


def test_halftone_preview_returns_reduced_data_url(client, tmp_path) -> None:
    src = _write_png(tmp_path / "src.png")
    response = client.post(
        "/api/utilities/halftone/preview",
        json={"input_path": str(src), "preview_max_side": 240},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["image_data_url"].startswith("data:image/png;base64,")
    assert max(body["width"], body["height"]) <= 240

    # El data URL decodifica a un PNG RGBA válido.
    raw = base64.b64decode(body["image_data_url"].split(",", 1)[1])
    decoded = Image.open(BytesIO(raw))
    assert decoded.mode == "RGBA"


def _write_transparent_png(path: Path) -> Path:
    """Sujeto con degradado sobre fondo transparente cuyo RGB es blanco (caso real tras
    quitar el fondo)."""
    img = Image.new("RGBA", (120, 120), (255, 255, 255, 0))
    px = img.load()
    for y in range(30, 90):
        for x in range(30, 90):
            tone = 40 + (x - 30) * 3
            px[x, y] = (tone, tone, tone, 255)
    img.save(path)
    return path


def test_halftone_preview_quick_mode_reports_resolved_params(client, tmp_path) -> None:
    src = _write_transparent_png(tmp_path / "src.png")
    response = client.post(
        "/api/utilities/halftone/preview",
        # En modo rápido los parámetros de trama del payload se ignoran.
        json={"input_path": str(src), "mode": "quick", "garment": "light", "screen_frequency": 90},
    )
    assert response.status_code == 200
    body = response.json()
    resolved = body["resolved"]
    assert resolved["background"] == "transparent"
    assert resolved["garment"] == "light"
    assert resolved["screen_frequency"] != 90
    assert resolved["min_dot_tone"] > 0
    assert body["output_width"] == 60 and body["output_height"] == 60
    assert isinstance(body["warnings"], list) and body["warnings"]


def test_halftone_preview_advanced_mode_uses_params_as_given(client, tmp_path) -> None:
    src = _write_png(tmp_path / "src.png")
    response = client.post(
        "/api/utilities/halftone/preview",
        json={
            "input_path": str(src),
            "mode": "advanced",
            "black_point": 30,
            "white_point": 210,
            "screen_frequency": 40,
            "halftone_method": "diffusion",
        },
    )
    assert response.status_code == 200
    resolved = response.json()["resolved"]
    assert (resolved["black_point"], resolved["white_point"]) == (30, 210)
    assert resolved["screen_frequency"] == 40
    assert any("Difusión" in w for w in response.json()["warnings"])


def test_halftone_export_keeps_transparent_background(client, tmp_path) -> None:
    src = _write_transparent_png(tmp_path / "src.png")
    response = client.post(
        "/api/utilities/halftone",
        json={"input_path": str(src), "mode": "quick", "garment": "dark"},
    )
    final = _wait_for_terminal(client, response.json()["job_id"])
    assert final["status"] == "succeeded"

    out = Image.open(final["result"]["output_path"])
    # Recortado al sujeto (60×60) y sin tinta fuera de él.
    assert out.size == (60, 60)
    assert out.getchannel("A").getextrema()[1] == 255


def test_halftone_rejects_unknown_garment(client, tmp_path) -> None:
    src = _write_png(tmp_path / "src.png")
    response = client.post(
        "/api/utilities/halftone",
        json={"input_path": str(src), "garment": "neon"},
    )
    assert response.status_code == 422


def test_halftone_rejects_out_of_range_frequency(client, tmp_path) -> None:
    src = _write_png(tmp_path / "src.png")
    response = client.post(
        "/api/utilities/halftone",
        json={"input_path": str(src), "screen_frequency": 500},
    )
    assert response.status_code == 422


def test_halftone_rejects_out_of_range_gamma(client, tmp_path) -> None:
    src = _write_png(tmp_path / "src.png")
    response = client.post(
        "/api/utilities/halftone",
        json={"input_path": str(src), "gamma": 9.0},
    )
    assert response.status_code == 422
