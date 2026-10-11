"""Tests del contrato y la carga de plantillas de mockup."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

from designfabric.core.imaging.mockup.template import MockupRequest, load_template


def test_load_template_reads_contract_and_optional_occlusion(mockup_template_dir: Path) -> None:
    template = load_template(mockup_template_dir)

    assert template.id == "tee-front-model-01"
    assert template.base_size == (400, 500)
    assert template.base.mode == "RGB"
    assert template.garment_mask.mode == "L"
    assert template.garment_mask.size == (400, 500)
    assert template.occlusion is None
    assert template.garment_colors["negro"] == "#1A1A1A"
    assert template.dark_garment_colors == ("negro",)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data.update(schema_version=2), "schema_version"),
        (
            lambda data: data["print_area"].update(
                corners=[[70, 105], [330, 410], [330, 105], [70, 410]]
            ),
            "convexo",
        ),
        (lambda data: data["garment_colors"].update(negro="negro"), "#RRGGBB"),
        (lambda data: data.update(base_size=[400, 0]), "base_size"),
    ],
)
def test_load_template_rejects_invalid_metadata(
    mockup_template_dir: Path, change: Callable[[dict[str, Any]], None], message: str
) -> None:
    json_path = mockup_template_dir / "template.json"
    metadata = json.loads(json_path.read_text(encoding="utf-8"))
    change(metadata)
    json_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_template(mockup_template_dir)


def test_load_template_rejects_png_with_wrong_size(mockup_template_dir: Path) -> None:
    from PIL import Image

    Image.new("L", (399, 500), 255).save(mockup_template_dir / "shading.png")

    with pytest.raises(ValueError, match="shading.png debe medir"):
        load_template(mockup_template_dir)


def test_mockup_request_validates_size_and_offset() -> None:
    request = MockupRequest(garment_color="#ffffff", print_width_cm=20.0)

    assert request.offset_cm == (0.0, 0.0)
    with pytest.raises(ValueError, match="print_width_cm"):
        MockupRequest(garment_color="blanco", print_width_cm=0)
