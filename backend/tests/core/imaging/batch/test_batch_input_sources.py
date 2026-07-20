"""Tests de estrategias de entrada batch."""

from __future__ import annotations

from pathlib import Path

import pytest

from designfabricv2.core.imaging.batch.input_sources import (
    FilesInputSource,
    FolderInputSource,
    create_input_source,
    is_supported_image,
)


def test_is_supported_image_extensions() -> None:
    assert is_supported_image(Path("a.png"))
    assert is_supported_image(Path("a.JPG"))
    assert is_supported_image(Path("a.webp"))
    assert not is_supported_image(Path("a.txt"))
    assert not is_supported_image(Path("a.svg"))


def test_folder_input_empty(tmp_path: Path) -> None:
    source = FolderInputSource(directory=tmp_path)
    assert source.resolve() == []


def test_folder_input_lists_non_recursive(tmp_path: Path) -> None:
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("hi", encoding="utf-8")
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "hidden.png").write_bytes(b"y")

    paths = FolderInputSource(directory=tmp_path).resolve()
    names = {path.name for path in paths}

    assert names == {"a.png", "notes.txt"}
    assert all(path.parent == tmp_path for path in paths)


def test_folder_input_missing_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    with pytest.raises(FileNotFoundError, match="No existe la carpeta"):
        FolderInputSource(directory=missing).resolve()


def test_files_input_returns_paths(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    b = tmp_path / "b.jpg"
    a.write_bytes(b"1")
    b.write_bytes(b"2")

    resolved = FilesInputSource(paths=(a, b)).resolve()
    assert resolved == [a, b]


def test_files_input_empty_raises() -> None:
    with pytest.raises(ValueError, match="vacía"):
        FilesInputSource(paths=()).resolve()


def test_create_input_source_factory(tmp_path: Path) -> None:
    folder = create_input_source("folder", directory=tmp_path)
    assert isinstance(folder, FolderInputSource)

    files = create_input_source("files", paths=[tmp_path / "a.png"])
    assert isinstance(files, FilesInputSource)

    with pytest.raises(ValueError, match="directory"):
        create_input_source("folder")

    with pytest.raises(ValueError, match="paths"):
        create_input_source("files")
