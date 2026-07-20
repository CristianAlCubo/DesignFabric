"""Tests API de settings/models OpenRouter."""

from __future__ import annotations

import pytest

from designfabric.core.generation.openrouter.client import OpenRouterClient
from designfabric.core.generation.openrouter.models_cache import get_models_cache
from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime


@pytest.fixture(autouse=True)
def _reset_openrouter_runtime():
    runtime = get_openrouter_runtime()
    runtime.reset_for_tests()
    get_models_cache().invalidate()
    yield
    runtime.reset_for_tests()
    get_models_cache().invalidate()


def test_get_settings_unconfigured(client):
    res = client.get("/api/settings/openrouter")
    assert res.status_code == 200
    body = res.json()
    assert body["configured"] is False
    assert body["text_model_id"] is None


def test_put_and_get_settings(client):
    res = client.put(
        "/api/settings/openrouter",
        json={
            "api_key": "sk-test-key",
            "text_model_id": "openai/gpt-4o",
            "image_model_id": "black-forest-labs/flux",
            "image_model_output_modalities": ["image"],
        },
    )
    assert res.status_code == 200
    assert res.json()["configured"] is True
    assert res.json()["text_model_id"] == "openai/gpt-4o"
    assert res.json()["image_model_output_modalities"] == ["image"]

    get_res = client.get("/api/settings/openrouter")
    assert get_res.json()["configured"] is True
    assert get_res.json()["image_model_output_modalities"] == ["image"]
    assert "api_key" not in get_res.json()


def test_put_preserves_modalities_when_omitted(client):
    client.put(
        "/api/settings/openrouter",
        json={
            "api_key": "sk-test",
            "image_model_id": "google/gemini-image",
            "image_model_output_modalities": ["image", "text"],
        },
    )
    res = client.put("/api/settings/openrouter", json={"text_model_id": "openai/gpt-4o"})
    assert res.json()["image_model_output_modalities"] == ["image", "text"]
    assert res.json()["text_model_id"] == "openai/gpt-4o"


def test_clear_image_model_clears_modalities(client):
    client.put(
        "/api/settings/openrouter",
        json={
            "api_key": "sk-test",
            "image_model_id": "google/gemini-image",
            "image_model_output_modalities": ["image"],
        },
    )
    res = client.put("/api/settings/openrouter", json={"clear_image_model": True})
    assert res.json()["image_model_id"] is None
    assert res.json()["image_model_output_modalities"] is None


def test_clear_api_key(client):
    client.put("/api/settings/openrouter", json={"api_key": "sk-x"})
    res = client.put("/api/settings/openrouter", json={"clear_api_key": True})
    assert res.json()["configured"] is False


def test_list_models_without_key_returns_503(client):
    res = client.get("/api/openrouter/models", params={"modality": "text"})
    assert res.status_code == 503


def test_list_models_with_mock_client(client, mocker):
    client.put("/api/settings/openrouter", json={"api_key": "sk-test"})

    from designfabric.core.generation.openrouter.models import OpenRouterModel

    fake_models = [
        OpenRouterModel(id="openai/gpt-4o", name="GPT-4o", output_modalities=("text",)),
        OpenRouterModel(id="meta/llama", name="Llama", output_modalities=("text",)),
    ]
    mocker.patch.object(OpenRouterClient, "list_models", return_value=fake_models)

    res = client.get("/api/openrouter/models", params={"modality": "text", "q": "gpt"})
    assert res.status_code == 200
    ids = [m["id"] for m in res.json()["models"]]
    assert ids == ["openai/gpt-4o"]


def test_batch_openrouter_without_config_returns_503(client):
    res = client.post(
        "/api/jobs/batch",
        json={"num_images": 1, "llm_provider": "openrouter", "image_provider": "test"},
    )
    assert res.status_code == 503


def test_batch_openrouter_with_config_queues(client):
    client.put(
        "/api/settings/openrouter",
        json={
            "api_key": "sk-test",
            "text_model_id": "openai/gpt-4o",
            "image_model_id": "google/gemini-image",
        },
    )
    res = client.post(
        "/api/jobs/batch",
        json={"num_images": 1, "llm_provider": "openrouter", "image_provider": "test"},
    )
    assert res.status_code == 202
