"""Tests de `core.sticker_generator`: mockean el pipeline de Flux para no requerir GPU real."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# Este módulo importa `torch`/`diffusers` a nivel de módulo: sin el extra
# `local-ai` instalado, ni siquiera se puede colectar el test file.
pytest.importorskip("torch")
pytest.importorskip("diffusers")

from designfabricv2.core.progress import Phase, ProgressEventType
from designfabricv2.core.generation.sticker_generator import generate_stickers, slugify


def _mock_pipeline(mocker, images: list[MagicMock]):
    """Parchea `Flux2KleinPipeline.from_pretrained` para devolver imágenes falsas en orden.

    También parchea `torch.Generator` (requiere CUDA real) para que los tests
    corran en cualquier máquina, con o sin GPU.
    """
    mocker.patch("designfabricv2.core.generation.sticker_generator.torch.Generator")
    pipe_instance = MagicMock()
    pipe_instance.side_effect = [MagicMock(images=[img]) for img in images]
    mocker.patch(
        "designfabricv2.core.generation.sticker_generator.Flux2KleinPipeline.from_pretrained",
        return_value=pipe_instance,
    )
    return pipe_instance


def test_slugify_truncates_and_normalizes():
    assert slugify("Hello, World! Test 123") == "hello_world_test_123"
    assert len(slugify("x" * 100)) == 40


def test_generate_stickers_saves_each_image(tmp_path, mocker, fake_reporter):
    fake_image = MagicMock()
    _mock_pipeline(mocker, [fake_image])

    output_dir = str(tmp_path / "output")
    results = generate_stickers(["a cat, sticker style"], output_dir=output_dir, reporter=fake_reporter)

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].filename == f"{output_dir}/sticker_1_a_cat_sticker_style.png"
    fake_image.save.assert_called_once_with(results[0].filename)

    types = [e.type for e in fake_reporter.events]
    assert types[0] is ProgressEventType.STARTED
    assert ProgressEventType.PROGRESS in types
    assert types[-1] is ProgressEventType.COMPLETED
    assert all(e.phase is Phase.IMAGE_GENERATION for e in fake_reporter.events)


def test_generate_stickers_continues_after_individual_failure(tmp_path, mocker, fake_reporter):
    mocker.patch("designfabricv2.core.generation.sticker_generator.torch.Generator")
    pipe_instance = MagicMock()
    good_image = MagicMock()
    pipe_instance.side_effect = [RuntimeError("OOM"), MagicMock(images=[good_image])]
    mocker.patch(
        "designfabricv2.core.generation.sticker_generator.Flux2KleinPipeline.from_pretrained",
        return_value=pipe_instance,
    )

    output_dir = str(tmp_path / "output")
    results = generate_stickers(["prompt one", "prompt two"], output_dir=output_dir, reporter=fake_reporter)

    assert len(results) == 2
    assert results[0].success is False
    assert results[0].error == "OOM"
    assert results[1].success is True

    warnings = [e for e in fake_reporter.events if e.type is ProgressEventType.WARNING]
    assert len(warnings) == 1
