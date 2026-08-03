"""Tests de los endpoints de conversión de formato (Utilidades)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from tests.api.conftest import wait_until


def _write_png(path: Path, size: tuple[int, int] = (24, 24), color: tuple[int, int, int] = (10, 120, 200)) -> Path:
    Image.new("RGB", size, color).save(path)
    return path


def _wait_for_terminal(client, job_id: str) -> dict:
    def is_done() -> bool:
        return client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed", "cancelled"}

    assert wait_until(is_done), "el job de conversión debería resolverse rápido"
    return client.get(f"/api/jobs/{job_id}").json()


def test_convert_single_reaches_succeeded_with_image_url(client, tmp_path) -> None:
    src = _write_png(tmp_path / "src.png")
    response = client.post(
        "/api/utilities/convert",
        json={"input_path": str(src), "target_format": "WEBP", "quality": 80},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert response.json()["status"] == "queued"

    final = _wait_for_terminal(client, job_id)
    assert final["status"] == "succeeded"
    assert final["result"]["image_url"].startswith("/output/convert/")
    assert final["result"]["output_path"].endswith(".webp")


def test_convert_batch_reaches_succeeded_with_zip_url(client, tmp_path) -> None:
    images = [str(_write_png(tmp_path / f"img_{i}.png")) for i in range(2)]
    response = client.post(
        "/api/utilities/convert-batch",
        json={"image_paths": images, "target_format": "JPEG", "quality": 90},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    final = _wait_for_terminal(client, job_id)
    assert final["status"] == "succeeded"
    result = final["result"]
    assert result["expected"] == 2
    assert result["produced"] == 2
    assert result["zip_url"].startswith("/output/convert/")
    assert result["zip_url"].endswith(".zip")


def test_convert_rejects_unsupported_format(client, tmp_path) -> None:
    src = _write_png(tmp_path / "src.png")
    response = client.post(
        "/api/utilities/convert",
        json={"input_path": str(src), "target_format": "GIF"},
    )
    assert response.status_code == 422


def test_convert_rejects_out_of_range_quality(client, tmp_path) -> None:
    src = _write_png(tmp_path / "src.png")
    response = client.post(
        "/api/utilities/convert",
        json={"input_path": str(src), "target_format": "JPEG", "quality": 150},
    )
    assert response.status_code == 422


def test_convert_batch_rejects_empty_image_list(client) -> None:
    response = client.post(
        "/api/utilities/convert-batch",
        json={"image_paths": [], "target_format": "PNG"},
    )
    assert response.status_code == 422
