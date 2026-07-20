"""Tests de `core.prompt_generator`: mockean ChatOllama/ollama para no requerir GPU ni Ollama real."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# Este módulo importa `langchain_ollama` a nivel de módulo: sin el extra
# `local-ai` instalado, ni siquiera se puede colectar el test file.
pytest.importorskip("langchain_ollama")

from designfabric.core.progress import Phase, ProgressEventType
from designfabric.core.generation.prompt_generator import (
    STYLE_SUFFIX,
    apply_style_suffix,
    generate_concepts,
    unload_ollama,
)


def _mock_llm(mocker, contents: list[str]):
    """Parchea `ChatOllama` para que `invoke` devuelva respuestas predefinidas en orden."""
    responses = [MagicMock(content=c) for c in contents]
    llm_instance = MagicMock()
    llm_instance.invoke.side_effect = responses
    mocker.patch("designfabric.core.generation.prompt_generator.ChatOllama", return_value=llm_instance)
    return llm_instance


def test_apply_style_suffix_appends_fixed_style():
    assert apply_style_suffix("a cat") == f"a cat, {STYLE_SUFFIX}"


def test_generate_concepts_happy_path(mocker, fake_reporter):
    _mock_llm(mocker, ['"a brave fox exploring a cave"'])

    prompts = generate_concepts(1, model="fake-model", reporter=fake_reporter)

    assert prompts == [f"a brave fox exploring a cave, {STYLE_SUFFIX}"]

    types = [e.type for e in fake_reporter.events]
    assert types[0] is ProgressEventType.STARTED
    assert ProgressEventType.PROGRESS in types
    assert types[-1] is ProgressEventType.COMPLETED
    assert all(e.phase is Phase.PROMPT_GENERATION for e in fake_reporter.events)


def test_generate_concepts_retries_then_succeeds(mocker, fake_reporter):
    llm_instance = MagicMock()
    llm_instance.invoke.side_effect = [RuntimeError("timeout"), MagicMock(content="a grumpy owl")]
    mocker.patch("designfabric.core.generation.prompt_generator.ChatOllama", return_value=llm_instance)

    prompts = generate_concepts(1, reporter=fake_reporter)

    assert prompts == [f"a grumpy owl, {STYLE_SUFFIX}"]
    warnings = [e for e in fake_reporter.events if e.type is ProgressEventType.WARNING]
    assert len(warnings) == 1


def test_generate_concepts_raises_when_all_concepts_fail(mocker, fake_reporter):
    llm_instance = MagicMock()
    llm_instance.invoke.side_effect = RuntimeError("ollama down")
    mocker.patch("designfabric.core.generation.prompt_generator.ChatOllama", return_value=llm_instance)

    with pytest.raises(RuntimeError, match="no generó ningún concepto"):
        generate_concepts(1, reporter=fake_reporter)

    assert fake_reporter.events[-1].type is ProgressEventType.FAILED


def test_unload_ollama_swallows_errors_and_warns(mocker, fake_reporter):
    mock_generate = mocker.patch("designfabric.core.generation.prompt_generator.ollama_client.generate")
    mock_generate.side_effect = RuntimeError("connection refused")

    unload_ollama(model="fake-model", reporter=fake_reporter)

    mock_generate.assert_called_once_with(model="fake-model", prompt="", keep_alive=0)
    assert fake_reporter.events[-1].type is ProgressEventType.WARNING
