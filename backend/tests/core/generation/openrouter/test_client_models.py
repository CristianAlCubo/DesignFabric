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


def test_list_image_models_merges_dedicated_catalog_with_capabilities():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        seen.append(path)
        if path.endswith("/images/models"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "openai/gpt-image-1.5",
                            "name": "GPT Image 1.5",
                            "architecture": {"output_modalities": ["image"]},
                            "supported_parameters": {
                                "background": {
                                    "type": "enum",
                                    "values": ["auto", "transparent", "opaque"],
                                },
                                "output_format": {
                                    "type": "enum",
                                    "values": ["png", "jpeg", "webp"],
                                },
                            },
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "google/gemini-image",
                        "name": "Gemini Image",
                        "architecture": {"output_modalities": ["image", "text"]},
                    },
                    {
                        "id": "openai/gpt-image-1.5",
                        "name": "GPT Image 1.5 (general)",
                        "architecture": {"output_modalities": ["image"]},
                    },
                ]
            },
        )

    client = OpenRouterClient("sk-test", transport=_MockTransport(handler))
    models = client.list_models("image")
    assert any(p.endswith("/models") for p in seen)
    assert any(p.endswith("/images/models") for p in seen)
    by_id = {m.id: m for m in models}
    assert set(by_id) == {"google/gemini-image", "openai/gpt-image-1.5"}
    assert "transparent" in by_id["openai/gpt-image-1.5"].supported_parameters["background"]["values"]
    assert by_id["google/gemini-image"].supported_parameters == {}


def test_openrouter_model_parses_supported_parameters():
    model = OpenRouterModel.from_api(
        {
            "id": "openai/gpt-image-1.5",
            "name": "GPT Image 1.5",
            "architecture": {"output_modalities": ["image"]},
            "supported_parameters": {
                "background": {"type": "enum", "values": ["transparent"]},
            },
        }
    )
    assert model is not None
    assert model.supported_parameters["background"]["values"] == ["transparent"]


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


def test_generate_image_uses_images_api_for_image_only():
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/images")
        body = json.loads(request.content)
        assert body["model"] == "openai/gpt-image-2"
        assert body["prompt"] == "a fox"
        assert body["output_format"] == "png"
        assert "background" not in body
        assert "modalities" not in body
        assert "messages" not in body
        return httpx.Response(
            200,
            json={"created": 1, "data": [{"b64_json": png_b64, "media_type": "image/png"}]},
        )

    client = OpenRouterClient("sk-test", transport=_MockTransport(handler))
    data = client.generate_image(
        "a fox",
        model="openai/gpt-image-2",
        modalities=["image"],
    )
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_image_sends_transparent_when_options_say_so():
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["background"] == "transparent"
        assert body["output_format"] == "png"
        return httpx.Response(
            200,
            json={"created": 1, "data": [{"b64_json": png_b64}]},
        )

    client = OpenRouterClient("sk-test", transport=_MockTransport(handler))
    client.generate_image(
        "a fox",
        model="openai/gpt-image-1.5",
        modalities=["image"],
        image_options={"output_format": "png", "background": "transparent"},
    )


def test_generate_image_uses_chat_for_image_plus_text():
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        body = json.loads(request.content)
        assert body["modalities"] == ["image", "text"]
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
    data = client.generate_image(
        "a fox",
        model="google/gemini-image",
        modalities=["image", "text"],
    )
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_image_rejects_empty_modalities():
    client = OpenRouterClient("sk-test")
    with pytest.raises(OpenRouterConfigError, match="modalities"):
        client.generate_image("a fox", model="x", modalities=[])
