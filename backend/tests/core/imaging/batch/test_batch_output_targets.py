"""Tests de estrategias de salida batch."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from designfabric.core.imaging.batch.output_targets import (
    DirectoryOutputTarget,
    ZipOutputTarget,
    create_output_target,
)


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


def test_zip_output_target_subfolder_per_image(tmp_path: Path) -> None:
    zip_path = tmp_path / "out.zip"
    target = ZipOutputTarget(zip_path=zip_path)

    cat_folder = target.resolve(Path("/in/gato.png"))
    dog_folder = target.resolve(Path("/in/perro.png"))
    assert cat_folder == Path("gato")
    assert dog_folder == Path("perro")

    target.write(cat_folder, "thumb_gato.png", b"cat-bytes")
    target.write(dog_folder, "thumb_perro.png", b"dog-bytes")
    target.close()

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        assert names == {"gato/thumb_gato.png", "perro/thumb_perro.png"}
        assert archive.read("gato/thumb_gato.png") == b"cat-bytes"


def test_zip_output_target_disambiguates_duplicate_stems(tmp_path: Path) -> None:
    target = ZipOutputTarget(zip_path=tmp_path / "out.zip")

    first = target.resolve(Path("/a/photo.png"))
    second = target.resolve(Path("/b/photo.jpg"))
    # Repeated calls for the same input path must return the same subfolder.
    first_again = target.resolve(Path("/a/photo.png"))

    assert first == Path("photo")
    assert second == Path("photo_2")
    assert first_again == first

    target.close()


def test_zip_output_target_write_after_close_raises(tmp_path: Path) -> None:
    target = ZipOutputTarget(zip_path=tmp_path / "out.zip")
    folder = target.resolve(Path("/a/photo.png"))
    target.close()

    with pytest.raises(RuntimeError):
        target.write(folder, "photo.png", b"data")


def test_create_output_target_factory_zip(tmp_path: Path) -> None:
    target = create_output_target("zip", zip_path=tmp_path / "out.zip")
    assert isinstance(target, ZipOutputTarget)
    target.close()

    with pytest.raises(ValueError, match="zip_path"):
        create_output_target("zip")
