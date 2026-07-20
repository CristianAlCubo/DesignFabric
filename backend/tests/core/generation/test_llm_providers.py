"""Tests de providers LLM primitivos (sin lógica de conceptos)."""

from __future__ import annotations

import pytest

from designfabric.core.generation.llm_providers import (
    LLM_TEST_FIXED_TEXT,
    ChatMessage,
    LlmTestProvider,
    create_llm_provider,
)


def test_create_llm_provider_test():
    provider = create_llm_provider("test")
    assert isinstance(provider, LlmTestProvider)


def test_create_llm_provider_rejects_unknown():
    with pytest.raises(ValueError, match="desconocido"):
        create_llm_provider("nope")  # type: ignore[arg-type]


def test_llm_test_provider_always_returns_same_text():
    provider = LlmTestProvider()
    messages = [ChatMessage(role="user", content="anything")]
    assert provider.generate_text(messages, model="ignored") == LLM_TEST_FIXED_TEXT
    assert provider.generate_text([ChatMessage(role="system", content="x")], model="m") == LLM_TEST_FIXED_TEXT


def test_llm_test_provider_release_is_noop(fake_reporter):
    LlmTestProvider().release(model="x", reporter=fake_reporter)
    assert fake_reporter.events == []
