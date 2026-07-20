"""Tests del probe de readiness de generación IA."""

from __future__ import annotations

import json

import pytest

from designfabric.core.config import Settings
from designfabric.core.generation import readiness as readiness_mod
from designfabric.core.generation.readiness import (
    GenerationReadiness,
    LocalAiStatus,
    OllamaStatus,
    probe_ollama,
    probe_readiness,
)


def test_probe_ollama_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps({"models": [{"name": "gemma3:4b"}, {"name": "llama3:8b"}]}).encode()

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return payload

    monkeypatch.setattr(readiness_mod.urllib.request, "urlopen", lambda *a, **k: _Resp())
    status = probe_ollama("http://localhost:11434")
    assert status.reachable is True
    assert status.models == ("gemma3:4b", "llama3:8b")
    assert status.error is None


def test_probe_ollama_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_a, **_k):
        raise readiness_mod.urllib.error.URLError("connection refused")

    monkeypatch.setattr(readiness_mod.urllib.request, "urlopen", _boom)
    status = probe_ollama("http://localhost:11434")
    assert status.reachable is False
    assert status.models == ()
    assert status.error is not None


def test_probe_readiness_providers_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        readiness_mod,
        "probe_local_ai",
        lambda: LocalAiStatus(available=True, missing=()),
    )
    monkeypatch.setattr(
        readiness_mod,
        "probe_ollama",
        lambda host: OllamaStatus(host=host, reachable=True, models=("gemma3:4b",)),
    )
    monkeypatch.setattr(
        readiness_mod,
        "probe_flux_weights",
        lambda model_id="x": readiness_mod.FluxStatus(
            model_id=model_id, weights_present=True, cache_hint="/cache"
        ),
    )
    monkeypatch.setattr(
        readiness_mod,
        "probe_cuda",
        lambda: readiness_mod.CudaStatus(available=True, device_name="GPU"),
    )

    ready = probe_readiness(Settings(ollama_host="http://ollama:11434"))
    assert ready.providers.ollama is True
    assert ready.providers.flux is True
    assert ready.has_ollama_model("gemma3:4b")
    assert not ready.has_ollama_model("missing:1b")


def test_probe_readiness_flux_needs_weights_and_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        readiness_mod,
        "probe_local_ai",
        lambda: LocalAiStatus(available=True, missing=()),
    )
    monkeypatch.setattr(
        readiness_mod,
        "probe_ollama",
        lambda host: OllamaStatus(host=host, reachable=True, models=()),
    )
    monkeypatch.setattr(
        readiness_mod,
        "probe_flux_weights",
        lambda model_id="x": readiness_mod.FluxStatus(
            model_id=model_id, weights_present=False, cache_hint="/cache"
        ),
    )
    monkeypatch.setattr(
        readiness_mod,
        "probe_cuda",
        lambda: readiness_mod.CudaStatus(available=True, device_name="GPU"),
    )
    ready = probe_readiness(Settings())
    assert ready.providers.flux is False

    monkeypatch.setattr(
        readiness_mod,
        "probe_flux_weights",
        lambda model_id="x": readiness_mod.FluxStatus(
            model_id=model_id, weights_present=True, cache_hint="/cache"
        ),
    )
    monkeypatch.setattr(
        readiness_mod,
        "probe_cuda",
        lambda: readiness_mod.CudaStatus(available=False),
    )
    ready = probe_readiness(Settings())
    assert ready.providers.flux is False


def test_probe_readiness_skips_remote_when_no_local_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        readiness_mod,
        "probe_local_ai",
        lambda: LocalAiStatus(available=False, missing=("torch",)),
    )
    called = {"ollama": False, "flux": False, "cuda": False}

    def _ollama(host: str) -> OllamaStatus:
        called["ollama"] = True
        return OllamaStatus(host=host, reachable=True, models=())

    def _flux(**_kwargs):
        called["flux"] = True
        return readiness_mod.FluxStatus("x", True)

    def _cuda():
        called["cuda"] = True
        return readiness_mod.CudaStatus(True)

    monkeypatch.setattr(readiness_mod, "probe_ollama", _ollama)
    monkeypatch.setattr(readiness_mod, "probe_flux_weights", _flux)
    monkeypatch.setattr(readiness_mod, "probe_cuda", _cuda)

    ready = probe_readiness(Settings())
    assert ready.providers.ollama is False
    assert ready.providers.flux is False
    assert called == {"ollama": False, "flux": False, "cuda": False}


def test_generation_readiness_to_dict_shape() -> None:
    ready = GenerationReadiness(
        local_ai=LocalAiStatus(available=True, missing=()),
        ollama=OllamaStatus(host="http://h", reachable=True, models=("a",)),
        flux=readiness_mod.FluxStatus("m", True, "/c"),
        cuda=readiness_mod.CudaStatus(True, "dev"),
        providers=readiness_mod.ProviderReadiness(ollama=True, flux=True),
    )
    data = ready.to_dict()
    assert set(data.keys()) == {"local_ai", "ollama", "flux", "cuda", "providers", "openrouter"}
    assert data["providers"]["test_llm"] is True
    assert data["providers"]["openrouter_llm"] is False
    assert data["openrouter"]["configured"] is False
