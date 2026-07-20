"""Tests de OpenRouterLlmProvider con client mock."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from designfabric.core.generation.llm_providers import ChatMessage, OpenRouterLlmProvider, create_llm_provider
from designfabric.core.generation.openrouter.errors import OpenRouterConfigError
from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime


@pytest.fixture(autouse=True)
def _reset_runtime():
    get_openrouter_runtime().reset_for_tests()
    yield
    get_openrouter_runtime().reset_for_tests()


def test_factory_registers_openrouter():
    provider = create_llm_provider("openrouter")
    assert isinstance(provider, OpenRouterLlmProvider)


def test_generate_text_delegates_to_client(mocker):
    get_openrouter_runtime().update(api_key="sk-test", text_model_id="openai/gpt-4o")
    fake = MagicMock()
    fake.chat_completion.return_value = "a fox"
    mocker.patch(
        "designfabric.core.generation.openrouter.client.build_client_from_runtime",
        return_value=fake,
    )

    text = OpenRouterLlmProvider().generate_text(
        [ChatMessage(role="user", content="hi")],
        model="openai/gpt-4o",
    )
    assert text == "a fox"
    fake.chat_completion.assert_called_once()


def test_generate_text_requires_model():
    get_openrouter_runtime().update(api_key="sk-test")
    with pytest.raises(OpenRouterConfigError):
        OpenRouterLlmProvider().generate_text([], model="")
