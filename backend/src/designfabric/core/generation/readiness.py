"""Probe de readiness de generación IA (solo reporte; sin remediar).

Fuente de verdad para saber si Ollama/FLUX son ejecutables en este entorno.
La remediación (pull, descarga, instalar deps) queda para un panel de
configuración futuro.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from designfabric.core.config import Settings, get_settings
from designfabric.core.generation.image_providers import FLUX_MODEL_ID
from designfabric.core.generation.local_ai_deps import LOCAL_AI_MODULES, missing_local_ai_modules

logger = logging.getLogger(__name__)

_OLLAMA_TIMEOUT_S = 2.0


@dataclass(frozen=True)
class LocalAiStatus:
    available: bool
    missing: tuple[str, ...] = ()


@dataclass(frozen=True)
class OllamaStatus:
    host: str
    reachable: bool
    models: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class FluxStatus:
    model_id: str
    weights_present: bool
    cache_hint: str | None = None


@dataclass(frozen=True)
class CudaStatus:
    available: bool
    device_name: str | None = None


@dataclass(frozen=True)
class ProviderReadiness:
    ollama: bool
    flux: bool
    test_llm: bool = True
    test_image: bool = True
    openrouter_llm: bool = False
    openrouter_image: bool = False


@dataclass(frozen=True)
class OpenRouterStatus:
    configured: bool
    text_model_id: str | None = None
    image_model_id: str | None = None


@dataclass(frozen=True)
class GenerationReadiness:
    """Estado agregado de readiness de generación IA."""

    local_ai: LocalAiStatus
    ollama: OllamaStatus
    flux: FluxStatus
    cuda: CudaStatus
    providers: ProviderReadiness
    openrouter: OpenRouterStatus = OpenRouterStatus(configured=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_ai": {
                "available": self.local_ai.available,
                "missing": list(self.local_ai.missing),
            },
            "ollama": {
                "host": self.ollama.host,
                "reachable": self.ollama.reachable,
                "models": list(self.ollama.models),
                "error": self.ollama.error,
            },
            "flux": {
                "model_id": self.flux.model_id,
                "weights_present": self.flux.weights_present,
                "cache_hint": self.flux.cache_hint,
            },
            "cuda": {
                "available": self.cuda.available,
                "device_name": self.cuda.device_name,
            },
            "providers": {
                "ollama": self.providers.ollama,
                "flux": self.providers.flux,
                "test_llm": self.providers.test_llm,
                "test_image": self.providers.test_image,
                "openrouter_llm": self.providers.openrouter_llm,
                "openrouter_image": self.providers.openrouter_image,
            },
            "openrouter": {
                "configured": self.openrouter.configured,
                "text_model_id": self.openrouter.text_model_id,
                "image_model_id": self.openrouter.image_model_id,
            },
        }

    def has_ollama_model(self, model: str) -> bool:
        if not model or not self.ollama.reachable:
            return False
        names = set(self.ollama.models)
        if model in names:
            return True
        # Tags a veces vienen como "name:tag"; aceptar prefijo "name" si el usuario
        # escribió solo el nombre corto y hay un único match exacto de familia.
        return any(m == model or m.startswith(f"{model}:") for m in names)


def probe_local_ai() -> LocalAiStatus:
    missing = missing_local_ai_modules()
    return LocalAiStatus(available=len(missing) == 0, missing=missing)


def probe_ollama(host: str) -> OllamaStatus:
    url = host.rstrip("/") + "/api/tags"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "DesignFabric/readiness"})
        with urllib.request.urlopen(request, timeout=_OLLAMA_TIMEOUT_S) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return OllamaStatus(host=host, reachable=False, error=str(exc.reason if hasattr(exc, "reason") else exc))
    except Exception as exc:  # noqa: BLE001 — reporte de readiness no debe fallar
        return OllamaStatus(host=host, reachable=False, error=str(exc))

    models: list[str] = []
    for item in payload.get("models") or []:
        name = item.get("name") or item.get("model")
        if isinstance(name, str) and name:
            models.append(name)
    return OllamaStatus(host=host, reachable=True, models=tuple(models))


def probe_flux_weights(model_id: str = FLUX_MODEL_ID) -> FluxStatus:
    try:
        from huggingface_hub import snapshot_download
        from huggingface_hub.constants import HF_HUB_CACHE
    except ImportError:
        return FluxStatus(
            model_id=model_id,
            weights_present=False,
            cache_hint="huggingface_hub no instalado (extra local-ai)",
        )

    cache_hint = str(HF_HUB_CACHE)
    try:
        path = snapshot_download(repo_id=model_id, local_files_only=True)
        return FluxStatus(model_id=model_id, weights_present=True, cache_hint=path)
    except Exception:  # noqa: BLE001 — ausencia de snapshot = no listo
        return FluxStatus(model_id=model_id, weights_present=False, cache_hint=cache_hint)


def probe_cuda() -> CudaStatus:
    try:
        import torch
    except ImportError:
        return CudaStatus(available=False)

    if not torch.cuda.is_available():
        return CudaStatus(available=False)
    try:
        name = torch.cuda.get_device_name(0)
    except Exception:  # noqa: BLE001
        name = None
    return CudaStatus(available=True, device_name=name)


def probe_readiness(settings: Settings | None = None) -> GenerationReadiness:
    """Evalúa el estado completo de readiness (barato, sin descargas)."""
    cfg = settings or get_settings()
    local_ai = probe_local_ai()
    ollama = probe_ollama(cfg.ollama_host) if local_ai.available else OllamaStatus(
        host=cfg.ollama_host,
        reachable=False,
        error="extra local-ai no instalado",
    )
    flux = probe_flux_weights() if local_ai.available else FluxStatus(
        model_id=FLUX_MODEL_ID,
        weights_present=False,
        cache_hint="extra local-ai no instalado",
    )
    cuda = probe_cuda() if local_ai.available else CudaStatus(available=False)

    from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime

    runtime = get_openrouter_runtime()
    runtime.seed_from_settings(cfg)
    or_snap = runtime.snapshot()
    openrouter = OpenRouterStatus(
        configured=or_snap.configured,
        text_model_id=or_snap.text_model_id,
        image_model_id=or_snap.image_model_id,
    )

    providers = ProviderReadiness(
        ollama=local_ai.available and ollama.reachable,
        flux=local_ai.available and flux.weights_present and cuda.available,
        openrouter_llm=or_snap.llm_ready,
        openrouter_image=or_snap.image_ready,
    )
    return GenerationReadiness(
        local_ai=local_ai,
        ollama=ollama,
        flux=flux,
        cuda=cuda,
        providers=providers,
        openrouter=openrouter,
    )


# Re-export útil para mensajes de error
__all__ = [
    "CudaStatus",
    "FluxStatus",
    "GenerationReadiness",
    "LOCAL_AI_MODULES",
    "LocalAiStatus",
    "OllamaStatus",
    "OpenRouterStatus",
    "ProviderReadiness",
    "probe_readiness",
]
