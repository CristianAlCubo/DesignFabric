"""Las plantillas que viajan con el instalador (`backend/data/mockup_templates/`)
deben cargar y renderizar."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from designfabric.core.imaging.mockup.render import render_mockup
from designfabric.core.imaging.mockup.template import MockupRequest, load_template

BUNDLED = Path(__file__).resolve().parents[4] / "data" / "mockup_templates"
TEMPLATE_DIRS = sorted(p for p in BUNDLED.iterdir() if (p / "template.json").is_file())


def test_bundled_templates_exist() -> None:
    assert {p.name for p in TEMPLATE_DIRS} >= {"tee-flat-front", "tee-flat-back"}


@pytest.mark.parametrize("template_dir", TEMPLATE_DIRS, ids=lambda p: p.name)
def test_bundled_template_renders(template_dir: Path) -> None:
    template = load_template(template_dir)
    assert template.id == template_dir.name
    design = Image.new("RGBA", (200, 200), (200, 40, 40, 255))
    for color in template.garment_colors:
        render_mockup(
            design, template, MockupRequest(garment_color=color, print_width_cm=20), max_side=400
        )
