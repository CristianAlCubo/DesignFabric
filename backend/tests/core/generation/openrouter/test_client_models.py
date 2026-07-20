"""Tests del cliente OpenRouter (listado/filtro/parse) con transport mock."""

from __future__ import annotations

import json

import httpx
import pytest

from designfabric.core.generation.llm_providers import ChatMessage
from designfabric.core.generation.openrouter.client import OpenRouterClient
from designfabric.core.generation.openrouter.errors import (
    OpenRouterAuthError,
    OpenRouterConfigError,
)
from designfabric.core.generation.openrouter.models import OpenRouterModel


def _models_payload() -> dict:
    return {
        "data": [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "architecture": {"output_modalities": ["text"]},
            },
            {
                "id": "black-forest-labs/flux",
                "name": "FLUX",
                "architecture": {"output_modalities": ["image"]},
            },
            {
                "id": "google/gemini-image",
                "name": "Gemini Image",
                "architecture": {"output_modalities": ["image", "text"]},
            },
        ]
    }


class _MockTransport(httpx.BaseTransport):
    def __init__(self, handler) -> None:
        self._handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def test_openrouter_model_matches_query():
    model = OpenRouterModel(id="openai/gpt-4o", name="GPT-4o", output_modalities=("text",))
    assert model.matches_query("gpt")
    assert model.matches_query("OPENAI")
    assert not model.matches_query("flux")


def test_filter_models():
    models = [
        OpenRouterModel(id="a/b", name="Alpha", output_modalities=("text",)),
        OpenRouterModel(id="c/d", name="Beta", output_modalities=("text",)),
    ]
    assert len(OpenRouterClient.filter_models(models, None)) == 2
    assert [m.id for m in OpenRouterClient.filter_models(models, "beta")] == ["c/d"]


def test_list_models_parses_and_uses_modality_query():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=_models_payload())

    client = OpenRouterClient("sk-test", transport=_MockTransport(handler))
    models = client.list_models("text")
    assert "output_modalities=text" in seen[0]
    assert {m.id for m in models} == {
        "openai/gpt-4o",
        "black-forest-labs/flux",
        "google/gemini-image",
    }


def test_list_models_401_raises_auth_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    client = OpenRouterClient("bad", transport=_MockTransport(handler))
    with pytest.raises(OpenRouterAuthError):
        client.list_models("text")


def test_client_requires_api_key():
    with pytest.raises(OpenRouterConfigError):
        OpenRouterClient("  ")


def test_chat_completion_extracts_text():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        body = json.loads(request.content.decode())
        assert body["model"] == "openai/gpt-4o"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "hello fox"}}]},
        )

    client = OpenRouterClient("sk-test", transport=_MockTransport(handler))
    text = client.chat_completion(
        [ChatMessage(role="user", content="hi")],
        model="openai/gpt-4o",
    )
    assert text == "hello fox"


def test_generate_image_from_data_url():
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "images": [
                                {"image_url": {"url": f"data:image/png;base64,{png_b64}"}}
                            ]
                        }
                    }
                ]
            },
        )

    client = OpenRouterClient("sk-test", transport=_MockTransport(handler))
    data = client.generate_image("a fox", model="google/gemini-image")
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
