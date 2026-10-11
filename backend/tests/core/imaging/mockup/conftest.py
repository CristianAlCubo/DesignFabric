"""Fixtures sintéticas para contratos y render de mockups."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture
def mockup_template_dir(tmp_path: Path) -> Path:
    """Genera una plantilla RGB/L de 400×500 sin assets binarios en el repo."""
    template_dir = tmp_path / "tee-front-model-01"
    template_dir.mkdir()
    width, height = 400, 500
    x_gradient = np.linspace(150, 205, width, dtype=np.uint8)
    y_gradient = np.linspace(0, 35, height, dtype=np.uint8)[:, None]
    base = np.empty((height, width, 3), dtype=np.uint8)
    base[:, :, 0] = np.clip(x_gradient[None, :] - y_gradient // 3, 0, 255)
    base[:, :, 1] = np.clip(x_gradient[None, :] - y_gradient // 3, 0, 255)
    base[:, :, 2] = np.clip(x_gradient[None, :] - y_gradient // 3, 0, 255)

    garment_mask = np.zeros((height, width), dtype=np.uint8)
    garment_mask[35:475, 35:365] = 255
    shading = np.clip(128 + (base[:, :, 0].astype(np.int16) - 177), 0, 255).astype(np.uint8)
    yy, xx = np.mgrid[0:height, 0:width]
    displacement = np.rint(128 + 18 * np.sin(xx / 47) * np.cos(yy / 61)).clip(0, 255).astype(
        np.uint8
    )

    Image.fromarray(base, mode="RGB").save(template_dir / "base.png")
    Image.fromarray(garment_mask, mode="L").save(template_dir / "garment_mask.png")
    Image.fromarray(shading, mode="L").save(template_dir / "shading.png")
    Image.fromarray(displacement, mode="L").save(template_dir / "displacement.png")
    metadata = {
        "schema_version": 1,
        "id": "tee-front-model-01",
        "name": "Camiseta frontal – modelo 01",
        "base_size": [width, height],
        "print_area": {"corners": [[70, 105], [330, 105], [330, 410], [70, 410]]},
        "px_per_cm": 10.0,
        "max_print_cm": [26.0, 30.0],
        "default_anchor": "top-center",
        "displacement_strength_px": 6.0,
        "shading_strength": 0.5,
        "highlight_strength": 0.3,
        "garment_colors": {"blanco": "#FFFFFF", "negro": "#1A1A1A"},
        "dark_garment_colors": ["negro"],
    }
    (template_dir / "template.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return template_dir
