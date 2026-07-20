"""Tests de readiness OpenRouter."""

from __future__ import annotations

import pytest

from designfabric.core.config import Settings
from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime
from designfabric.core.generation.readiness import probe_readiness


@pytest.fixture(autouse=True)
def _reset_runtime():
    get_openrouter_runtime().reset_for_tests()
    yield
    get_openrouter_runtime().reset_for_tests()


def test_readiness_openrouter_flags_matrix(mocker):
    mocker.patch("designfabric.core.generation.readiness.probe_local_ai")
    mocker.patch("designfabric.core.generation.readiness.probe_ollama")
    mocker.patch("designfabric.core.generation.readiness.probe_flux_weights")
    mocker.patch("designfabric.core.generation.readiness.probe_cuda")

    from designfabric.core.generation.readiness import (
        CudaStatus,
        FluxStatus,
        LocalAiStatus,
        OllamaStatus,
    )

    mocker.patch(
        "designfabric.core.generation.readiness.probe_local_ai",
        return_value=LocalAiStatus(available=False, missing=("torch",)),
    )
    mocker.patch(
        "designfabric.core.generation.readiness.probe_ollama",
        return_value=OllamaStatus(host="http://x", reachable=False),
    )
    mocker.patch(
        "designfabric.core.generation.readiness.probe_flux_weights",
        return_value=FluxStatus(model_id="m", weights_present=False),
    )
    mocker.patch(
        "designfabric.core.generation.readiness.probe_cuda",
        return_value=CudaStatus(available=False),
    )

    ready = probe_readiness(Settings())
    assert ready.providers.openrouter_llm is False
    assert ready.providers.openrouter_image is False
    assert ready.openrouter.configured is False

    get_openrouter_runtime().update(api_key="sk", text_model_id="t/m")
    ready = probe_readiness(Settings())
    assert ready.providers.openrouter_llm is True
    assert ready.providers.openrouter_image is False

    get_openrouter_runtime().update(image_model_id="i/m")
    ready = probe_readiness(Settings())
    assert ready.providers.openrouter_image is True
    assert ready.to_dict()["openrouter"]["text_model_id"] == "t/m"
