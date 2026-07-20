"""Tests de providers de imagen primitivos."""

from __future__ import annotations

from pathlib import Path

import pytest

from designfabric.core.generation.image_providers import (
    TestImageProvider,
    _test_sticker_path,
    create_image_provider,
)
from designfabric.core.progress import Phase, ProgressEventType


def test_create_image_provider_test():
    provider = create_image_provider("test")
    assert isinstance(provider, TestImageProvider)


def test_create_image_provider_rejects_unknown():
    with pytest.raises(ValueError, match="desconocido"):
        create_image_provider("nope")  # type: ignore[arg-type]


def test_test_sticker_asset_exists():
    path = _test_sticker_path()
    assert path.is_file()
    assert path.stat().st_size > 0


def test_test_image_provider_copies_fixed_png(tmp_path, fake_reporter):
    provider = TestImageProvider()
    output_dir = str(tmp_path / "out")
    results = provider.generate_images(
        ["prompt one", "prompt two"],
        output_dir=output_dir,
        reporter=fake_reporter,
    )

    assert len(results) == 2
    assert all(r.success for r in results)
    source_bytes = _test_sticker_path().read_bytes()
    for result in results:
        assert result.filename is not None
        assert Path(result.filename).read_bytes() == source_bytes

    types = [e.type for e in fake_reporter.events]
    assert types[0] is ProgressEventType.STARTED
    assert ProgressEventType.PROGRESS in types
    assert types[-1] is ProgressEventType.COMPLETED
    assert all(e.phase is Phase.IMAGE_GENERATION for e in fake_reporter.events)
