"""Tests de los endpoints de mockup y administración de plantillas."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageChops
from starlette.testclient import TestClient

from designfabric.core.imaging.mockup.prepare import save_template
from tests.api.conftest import wait_until


@pytest.fixture(autouse=True)
def _mockup_templates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Instala una plantilla pequeña generada por código para cada cliente de prueba."""
    templates_dir = tmp_path / "templates"
    monkeypatch.setenv("DESIGNFABRIC_MOCKUP_TEMPLATES_DIR", str(templates_dir))
    base = Image.new("RGB", (120, 160), (45, 55, 65))
    draw = ImageDraw.Draw(base)
    draw.rectangle((20, 20, 100, 140), fill=(190, 190, 190))
    for y in range(22, 139):
        shade = 150 + y % 70
        draw.line((22, y, 98, y), fill=(shade, shade, shade))
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).rectangle((20, 20, 100, 140), fill=255)
    save_template(
        templates_dir / "tee-front-01",
        base,
        template_id="tee-front-01",
        name="Camiseta de prueba",
        corners=((20, 20), (100, 20), (100, 140), (20, 140)),
        px_per_cm=4,
        mask=mask,
        max_print_cm=(10, 15),
        garment_colors={"blanco": "#FFFFFF", "negro": "#1A1A1A", "rojo": "#E02020"},
        dark_garment_colors=("negro",),
    )


def _write_design(path: Path) -> Path:
    design = Image.new("RGBA", (36, 28), (0, 0, 0, 0))
    ImageDraw.Draw(design).rectangle((4, 3, 31, 24), fill=(210, 35, 45, 255))
    design.save(path)
    return path


def _wait_for_terminal(client: TestClient, job_id: str) -> dict:
    def is_done() -> bool:
        return client.get(f"/api/jobs/{job_id}").json()["status"] in {
            "succeeded",
            "failed",
            "cancelled",
        }

    assert wait_until(is_done), "el job de mockup debería resolverse rápido"
    return client.get(f"/api/jobs/{job_id}").json()


def test_mockup_templates_list_and_thumbnail(client: TestClient) -> None:
    response = client.get("/api/mockups/templates")
    assert response.status_code == 200
    templates = response.json()["templates"]
    assert len(templates) == 1
    assert templates[0] == {
        "id": "tee-front-01",
        "name": "Camiseta de prueba",
        "thumbnail_url": "/api/mockups/templates/tee-front-01/thumbnail",
        "garment_colors": {
            "blanco": "#FFFFFF",
            "negro": "#1A1A1A",
            "rojo": "#E02020",
        },
        "max_print_cm": [10.0, 15.0],
        "px_per_cm": 4.0,
        "base_size": [120, 160],
    }

    thumbnail = client.get(templates[0]["thumbnail_url"])
    assert thumbnail.status_code == 200
    assert thumbnail.headers["content-type"] == "image/png"
    assert Image.open(BytesIO(thumbnail.content)).size == (120, 160)


def test_mockup_preview_and_job_export_are_pixel_identical(client: TestClient, tmp_path: Path) -> None:
    design_path = _write_design(tmp_path / "design.png")
    payload = {
        "design_path": str(design_path),
        "template_id": "tee-front-01",
        "garment_color": "rojo",
        "print_width_cm": 5,
        "offset_cm": [0, 0],
    }
    preview_response = client.post("/api/mockups/preview", json={**payload, "max_side": 1280})
    assert preview_response.status_code == 200
    preview_body = preview_response.json()
    assert preview_body["width"] == 120 and preview_body["height"] == 160
    assert preview_body["image_data_url"].startswith("data:image/png;base64,")
    preview_image = Image.open(
        BytesIO(base64.b64decode(preview_body["image_data_url"].split(",", 1)[1]))
    )

    response = client.post("/api/mockups", json=payload)
    assert response.status_code == 202
    final = _wait_for_terminal(client, response.json()["job_id"])
    assert final["status"] == "succeeded"
    assert final["type"] == "mockup"
    result = final["result"]
    assert result["image_url"].startswith("/output/mockups/")
    assert result["output_path"].endswith(".png")
    exported = Image.open(result["output_path"])
    assert ImageChops.difference(preview_image, exported).getbbox() is None
    assert tuple(round(value) for value in exported.info["dpi"]) == (300, 300)


def test_mockup_preview_rejects_unknown_template_and_color(client: TestClient, tmp_path: Path) -> None:
    design_path = _write_design(tmp_path / "design.png")
    payload = {
        "design_path": str(design_path),
        "template_id": "missing-template",
        "garment_color": "blanco",
        "print_width_cm": 5,
    }
    missing = client.post("/api/mockups/preview", json=payload)
    assert missing.status_code == 404

    payload["template_id"] = "tee-front-01"
    payload["garment_color"] = "chartreuse"
    unknown_color = client.post("/api/mockups/preview", json=payload)
    assert unknown_color.status_code == 422

    payload["garment_color"] = "#12GG00"
    invalid_hex = client.post("/api/mockups/preview", json=payload)
    assert invalid_hex.status_code == 422


@pytest.mark.parametrize("width", [0, -1])
def test_mockup_preview_rejects_nonpositive_width(
    client: TestClient, tmp_path: Path, width: float
) -> None:
    design_path = _write_design(tmp_path / "design.png")
    response = client.post(
        "/api/mockups/preview",
        json={
            "design_path": str(design_path),
            "template_id": "tee-front-01",
            "garment_color": "blanco",
            "print_width_cm": width,
        },
    )
    assert response.status_code == 422


def test_mockup_template_prepare_and_update(client: TestClient, tmp_path: Path) -> None:
    photo = Image.new("RGB", (64, 80), (35, 45, 55))
    ImageDraw.Draw(photo).rectangle((8, 8, 55, 72), fill=(190, 190, 190))
    photo_path = tmp_path / "photo.png"
    photo.save(photo_path)

    prepared = client.post("/api/mockups/templates/prepare", json={"photo_path": str(photo_path)})
    assert prepared.status_code == 200
    prepared_body = prepared.json()
    assert prepared_body["base_size"] == [64, 80]
    mask_data_url = prepared_body["mask_data_url"]
    assert mask_data_url.startswith("data:image/png;base64,")

    saved = client.put(
        "/api/mockups/templates/new-shirt",
        json={
            "photo_path": str(photo_path),
            "name": "Nueva plantilla",
            "corners": [[8, 8], [55, 8], [55, 72], [8, 72]],
            "px_per_cm": 3.2,
            "max_print_cm": [12, 16],
            "garment_colors": {"blanco": "#FFFFFF"},
            "mask_data_url": mask_data_url,
        },
    )
    assert saved.status_code == 200
    assert saved.json()["id"] == "new-shirt"
    assert saved.json()["base_size"] == [64, 80]
    assert client.get("/api/mockups/templates/new-shirt/thumbnail").status_code == 200


def test_mockup_template_update_rejects_invalid_id(client: TestClient, tmp_path: Path) -> None:
    photo_path = _write_design(tmp_path / "photo.png")
    response = client.put(
        "/api/mockups/templates/Invalid_ID",
        json={
            "photo_path": str(photo_path),
            "name": "Inválida",
            "corners": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "px_per_cm": 1,
            "max_print_cm": [10, 10],
        },
    )
    assert response.status_code == 422
