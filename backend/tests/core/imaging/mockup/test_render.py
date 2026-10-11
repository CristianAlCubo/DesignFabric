"""Pruebas del motor determinista de render de mockups."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

from designfabric.core.imaging.mockup.render import render_mockup
from designfabric.core.imaging.mockup.template import MockupRequest, load_template

_GOLDENS_PATH = Path(__file__).with_name("goldens.json")


def _design() -> Image.Image:
    """Genera un diseño con margen transparente y una figura roja opaca."""
    image = Image.new("RGBA", (140, 100), (0, 0, 0, 0))
    pixels = np.asarray(image).copy()
    pixels[20:80, 20:120] = (224, 35, 52, 255)
    return Image.fromarray(pixels, mode="RGBA")


def _png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG", dpi=(300, 300))
    return buffer.getvalue()


def _render(template_dir: Path, color: str) -> Image.Image:
    return render_mockup(
        _design(),
        load_template(template_dir),
        MockupRequest(garment_color=color, print_width_cm=14.0),
    )


def test_render_is_deterministic_across_three_runs(mockup_template_dir: Path) -> None:
    outputs = [_png_bytes(_render(mockup_template_dir, "blanco")) for _ in range(3)]

    assert outputs[0] == outputs[1] == outputs[2]


def test_render_matches_golden_hashes(mockup_template_dir: Path) -> None:
    outputs = {
        color: sha256(_png_bytes(_render(mockup_template_dir, color))).hexdigest()
        for color in ("blanco", "negro")
    }
    if os.environ.get("UPDATE_GOLDENS") == "1":
        _GOLDENS_PATH.write_text(
            json.dumps(outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    expected = json.loads(_GOLDENS_PATH.read_text(encoding="utf-8"))
    assert outputs == expected


def test_pixels_outside_garment_mask_keep_original_base(
    mockup_template_dir: Path,
) -> None:
    template = load_template(mockup_template_dir)
    result = render_mockup(
        _design(), template, MockupRequest(garment_color="blanco", print_width_cm=14.0)
    )
    outside_mask = np.asarray(template.garment_mask) == 0

    assert np.array_equal(
        np.asarray(result)[outside_mask], np.asarray(template.base)[outside_mask]
    )


def test_neutral_displacement_is_identical_to_zero_strength(
    mockup_template_dir: Path,
) -> None:
    template = load_template(mockup_template_dir)
    neutral_template = replace(
        template,
        displacement=Image.new("L", template.base_size, 128),
    )
    no_displacement_template = replace(neutral_template, displacement_strength_px=0.0)
    request = MockupRequest(garment_color="negro", print_width_cm=14.0)

    neutral = render_mockup(_design(), neutral_template, request)
    no_displacement = render_mockup(_design(), no_displacement_template, request)

    assert _png_bytes(neutral) == _png_bytes(no_displacement)


def test_print_width_uses_template_pixels_per_centimeter(
    mockup_template_dir: Path,
) -> None:
    template = load_template(mockup_template_dir)
    template = replace(
        template,
        displacement=Image.new("L", template.base_size, 128),
        displacement_strength_px=5.0,
        shading_strength=0.0,
        highlight_strength=0.0,
    )
    request = MockupRequest(garment_color="blanco", print_width_cm=10.0)
    result = render_mockup(_design(), template, request)

    rendered = np.asarray(result, dtype=np.uint8)
    # Huella del diseño: lo que cambia al invertir sus colores (mismo alpha).
    design = np.asarray(_design().convert("RGBA")).copy()
    design[:, :, :3] = 255 - design[:, :, :3]
    inverted = render_mockup(Image.fromarray(design, mode="RGBA"), template, request)
    changed = np.any(rendered != np.asarray(inverted, dtype=np.uint8), axis=2)
    ys, xs = np.where(changed & (np.asarray(template.garment_mask) > 0))

    assert abs(int(xs.max() - xs.min() + 1) - 100) <= 2
    assert abs(int(ys.max() - ys.min() + 1) - 60) <= 2


def test_unknown_color_and_oversize_produce_warnings(mockup_template_dir: Path) -> None:
    template = load_template(mockup_template_dir)
    result = render_mockup(
        _design(),
        template,
        MockupRequest(garment_color="turquesa-inexistente", print_width_cm=40.0),
    )

    warnings = result.info["warnings"]
    assert any("Color de prenda desconocido" in warning for warning in warnings)
    assert any("max_print_cm" in warning for warning in warnings)


def test_nearly_fully_occluded_design_produces_warning(
    mockup_template_dir: Path,
) -> None:
    template = load_template(mockup_template_dir)
    covered_template = replace(
        template,
        occlusion=Image.new("L", template.base_size, 255),
    )
    result = render_mockup(
        _design(),
        covered_template,
        MockupRequest(garment_color="blanco", print_width_cm=14.0),
    )

    assert any(
        "casi totalmente ocluido" in warning for warning in result.info["warnings"]
    )


def test_preview_resizes_template_and_preserves_warning_contract(
    mockup_template_dir: Path,
) -> None:
    template = load_template(mockup_template_dir)
    request = MockupRequest(garment_color="negro", print_width_cm=40.0)
    full_size = render_mockup(_design(), template, request)
    preview = render_mockup(_design(), template, request, max_side=200)

    assert preview.size == (160, 200)
    assert preview.size[0] / preview.size[1] == full_size.size[0] / full_size.size[1]
    assert preview.info["warnings"] == full_size.info["warnings"]
    assert preview.info["dpi"] == (300, 300)
