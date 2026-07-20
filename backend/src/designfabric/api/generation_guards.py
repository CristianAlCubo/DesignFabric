"""Guards compartidos de readiness para encolar jobs de generación."""

from __future__ import annotations

from fastapi import HTTPException

from designfabric.core.config import Settings, get_settings
from designfabric.core.generation.readiness import GenerationReadiness, probe_readiness


def require_generation_ready(
    *,
    llm_provider: str | None = None,
    image_provider: str | None = None,
    ollama_model: str | None = None,
    settings: Settings | None = None,
    readiness: GenerationReadiness | None = None,
) -> GenerationReadiness:
    """Rechaza el request con 503 si el provider pedido no es ejecutable."""
    ready = readiness or probe_readiness(settings or get_settings())

    if llm_provider == "ollama":
        if not ready.providers.ollama:
            detail = "Ollama no está disponible."
            if not ready.local_ai.available:
                detail = (
                    "El provider ollama requiere el extra 'local-ai'. "
                    "Usa llm_provider=test, o instala local-ai."
                )
            elif ready.ollama.error:
                detail = f"Ollama no responde en {ready.ollama.host}: {ready.ollama.error}"
            else:
                detail = f"Ollama no responde en {ready.ollama.host}."
            raise HTTPException(status_code=503, detail=detail)
        if ollama_model and not ready.has_ollama_model(ollama_model):
            raise HTTPException(
                status_code=503,
                detail=(
                    f"El modelo Ollama '{ollama_model}' no está instalado. "
                    f"Modelos locales: {', '.join(ready.ollama.models) or '(ninguno)'}."
                ),
            )

    if image_provider == "flux":
        if not ready.providers.flux:
            if not ready.local_ai.available:
                detail = (
                    "El provider flux requiere el extra 'local-ai'. "
                    "Usa image_provider=test, o instala local-ai."
                )
            elif not ready.cuda.available:
                detail = "FLUX.2 Klein requiere CUDA; no hay GPU disponible."
            elif not ready.flux.weights_present:
                detail = (
                    f"Pesos de FLUX no encontrados en caché ({ready.flux.model_id}). "
                    "Descárgalos fuera de la app o desde el panel de configuración (próximamente)."
                )
            else:
                detail = "El provider flux no está listo."
            raise HTTPException(status_code=503, detail=detail)

    return ready
