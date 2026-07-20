"""Tests del dominio de conceptos encima de un LlmProvider."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from designfabric.core.generation.llm_providers import LlmTestProvider, LLM_TEST_FIXED_TEXT
from designfabric.core.generation.prompt_generator import (
    STYLE_SUFFIX,
    apply_style_suffix,
    generate_concepts,
    unload_ollama,
)
from designfabric.core.progress import Phase, ProgressEventType


def test_apply_style_suffix_appends_fixed_style():
    assert apply_style_suffix("a cat") == f"a cat, {STYLE_SUFFIX}"


def test_generate_concepts_with_test_provider(fake_reporter):
    prompts = generate_concepts(2, llm=LlmTestProvider(), reporter=fake_reporter)

    expected = f"{LLM_TEST_FIXED_TEXT}, {STYLE_SUFFIX}"
    assert prompts == [expected, expected]
    types = [e.type for e in fake_reporter.events]
    assert types[0] is ProgressEventType.STARTED
    assert ProgressEventType.PROGRESS in types
    assert types[-1] is ProgressEventType.COMPLETED
    assert all(e.phase is Phase.PROMPT_GENERATION for e in fake_reporter.events)


def test_generate_concepts_retries_then_succeeds(fake_reporter):
    llm = MagicMock()
    llm.generate_text.side_effect = [RuntimeError("timeout"), "a grumpy owl"]

    prompts = generate_concepts(1, llm=llm, reporter=fake_reporter)

    assert prompts == [f"a grumpy owl, {STYLE_SUFFIX}"]
    warnings = [e for e in fake_reporter.events if e.type is ProgressEventType.WARNING]
    assert len(warnings) == 1


def test_generate_concepts_raises_when_all_concepts_fail(fake_reporter):
    llm = MagicMock()
    llm.generate_text.side_effect = RuntimeError("ollama down")

    with pytest.raises(RuntimeError, match="ningún concepto válido"):
        generate_concepts(1, llm=llm, reporter=fake_reporter)

    assert fake_reporter.events[-1].type is ProgressEventType.FAILED


def test_unload_ollama_swallows_errors_and_warns(mocker, fake_reporter):
    pytest.importorskip("ollama")
    mock_client_cls = mocker.patch("ollama.Client")
    mock_client = MagicMock()
    mock_client.generate.side_effect = RuntimeError("connection refused")
    mock_client_cls.return_value = mock_client
    mocker.patch("ollama.generate", side_effect=RuntimeError("connection refused"))

    unload_ollama(model="fake-model", reporter=fake_reporter, ollama_host="http://localhost:11434")

    assert fake_reporter.events[-1].type is ProgressEventType.WARNING
