"""Pruebas del comando de preparación de plantillas."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from typer.testing import CliRunner

from designfabric.cli.mockup import app


def test_comando_prepare_crea_la_carpeta_de_plantilla(tmp_path: Path) -> None:
    photo = tmp_path / "foto.png"
    pixels = np.full((50, 60, 3), 25, dtype=np.uint8)
    pixels[8:45, 12:48] = 180
    Image.fromarray(pixels, mode="RGB").save(photo)
    output_dir = tmp_path / "plantillas"

    result = CliRunner().invoke(
        app,
        [
            "prepare",
            str(photo),
            "--id",
            "camiseta-01",
            "--name",
            "Camiseta de prueba",
            "--corners",
            "10,10;50,10;50,40;10,40",
            "--px-per-cm",
            "4",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Plantilla lista" in result.output
    assert (output_dir / "camiseta-01" / "template.json").is_file()


def test_comando_prepare_informa_esquinas_invalidas(tmp_path: Path) -> None:
    photo = tmp_path / "foto.png"
    Image.new("RGB", (20, 20), "white").save(photo)
    result = CliRunner().invoke(
        app,
        ["prepare", str(photo), "--id", "camiseta", "--corners", "mal", "--px-per-cm", "4"],
    )

    assert result.exit_code == 1
    assert "--corners" in result.output
