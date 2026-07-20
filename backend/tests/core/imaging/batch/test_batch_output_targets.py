"""Tests de estrategias de salida batch."""

from __future__ import annotations

from pathlib import Path

import pytest

from designfabric.core.imaging.batch.output_targets import DirectoryOutputTarget, create_output_target


def test_directory_output_uses_stem(tmp_path: Path) -> None:
    target = DirectoryOutputTarget(directory=tmp_path)
    assert target.resolve(Path("/in/cat.jpeg")) == tmp_path / "cat.png"


def test_directory_output_disambiguates_collisions(tmp_path: Path) -> None:
    target = DirectoryOutputTarget(directory=tmp_path)

    first = target.resolve(Path("/a/logo.png"))
    second = target.resolve(Path("/b/logo.jpg"))
    third = target.resolve(Path("/c/logo.webp"))

    assert first == tmp_path / "logo.png"
    assert second == tmp_path / "logo_2.png"
    assert third == tmp_path / "logo_3.png"


def test_create_output_target_factory(tmp_path: Path) -> None:
    target = create_output_target("directory", directory=tmp_path)
    assert isinstance(target, DirectoryOutputTarget)

    with pytest.raises(ValueError, match="directory"):
        create_output_target("directory")
