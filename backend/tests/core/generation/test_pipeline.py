"""Tests e2e del facade con providers test (sin local-ai)."""

from __future__ import annotations

from pathlib import Path

from designfabric.core.generation.image_providers import _test_sticker_path
from designfabric.core.generation.llm_providers import LLM_TEST_FIXED_TEXT
from designfabric.core.generation.pipeline import run_batch, run_single_image
from designfabric.core.generation.prompt_generator import STYLE_SUFFIX


def test_run_batch_with_test_providers(tmp_path, fake_reporter):
    output_dir = str(tmp_path / "batch")
    result = run_batch(
        2,
        output_dir=output_dir,
        reporter=fake_reporter,
        llm_provider="test",
        image_provider="test",
    )

    expected_prompt = f"{LLM_TEST_FIXED_TEXT}, {STYLE_SUFFIX}"
    assert result.prompts == [expected_prompt, expected_prompt]
    assert result.failure_count == 0
    assert len(result.results) == 2
    source = _test_sticker_path().read_bytes()
    for item in result.results:
        assert item.success
        assert item.filename is not None
        assert Path(item.filename).read_bytes() == source


def test_run_single_image_with_test_provider(tmp_path, fake_reporter):
    output_dir = str(tmp_path / "single")
    result = run_single_image(
        "a custom prompt",
        apply_style=True,
        output_dir=output_dir,
        reporter=fake_reporter,
        image_provider="test",
    )

    assert result.success
    assert result.prompt == f"a custom prompt, {STYLE_SUFFIX}"
    assert result.filename is not None
    assert Path(result.filename).read_bytes() == _test_sticker_path().read_bytes()
