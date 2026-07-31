"""Tests del pipeline de exportación multi-tamaño."""

from __future__ import annotations

import zipfile
from pathlib import Path

import cv2
import numpy as np

from designfabric.core.imaging.ai_upscalers.common import resolve_percent_size
from designfabric.core.imaging.multi_export_pipeline import (
    SizeRow,
    render_filename,
    run_multi_export,
)


def _write_png(path: Path, width: int, height: int) -> None:
    img = np.zeros((height, width, 4), dtype=np.uint8)
    img[..., 3] = 255
    assert cv2.imwrite(str(path), img)


def test_resolve_percent_size_relative_to_each_image() -> None:
    assert resolve_percent_size(4000, 3000, 50) == (2000, 1500)
    assert resolve_percent_size(300, 200, 50) == (150, 100)


def test_resolve_percent_size_minimum_one_pixel() -> None:
    assert resolve_percent_size(10, 10, 1) == (1, 1)


def test_render_filename_default_template() -> None:
    row = SizeRow(label="thumb", mode="px", prefix="thumb_", width=200, height=150)
    assert render_filename(row, stem="gato", width=200, height=150) == "thumb_gato.png"


def test_render_filename_custom_template_with_tokens() -> None:
    row = SizeRow(label="custom", mode="px", template="{name}@{width}x{height}")
    assert render_filename(row, stem="gato", width=200, height=150) == "gato@200x150.png"


def test_run_multi_export_happy_path(tmp_path: Path) -> None:
    gato = tmp_path / "gato.png"
    perro = tmp_path / "perro.png"
    _write_png(gato, 400, 300)
    _write_png(perro, 200, 200)

    sizes = [
        SizeRow(label="thumb", mode="px", prefix="thumb_", width=100),
        SizeRow(label="half", mode="percent", prefix="half_", percent=50),
    ]
    zip_path = tmp_path / "out" / "export.zip"

    report = run_multi_export([gato, perro], sizes, zip_path)

    assert report.expected == 4
    assert report.produced == 4
    assert all(item.status == "succeeded" for item in report.items)

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        assert names == {
            "gato/thumb_gato.png",
            "gato/half_gato.png",
            "perro/thumb_perro.png",
            "perro/half_perro.png",
        }


def test_run_multi_export_partial_failure_continues(tmp_path: Path) -> None:
    gato = tmp_path / "gato.png"
    missing = tmp_path / "no_existe.png"
    _write_png(gato, 100, 100)

    sizes = [SizeRow(label="thumb", mode="px", prefix="thumb_", width=50)]
    zip_path = tmp_path / "export.zip"

    report = run_multi_export([gato, missing], sizes, zip_path)

    assert report.expected == 2
    assert report.produced == 1
    statuses = {item.input_path.name: item.status for item in report.items}
    assert statuses["gato.png"] == "succeeded"
    assert statuses["no_existe.png"] == "failed"

    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == ["gato/thumb_gato.png"]
