"""Facade del pipeline completo de generación.

Orquesta dominio de conceptos + providers primitivos (LLM e imagen).
Reutilizable por CLI y workers de la API.
"""

from __future__ import annotations

from dataclasses import dataclass

from designfabric.core.generation.constants import OLLAMA_MODEL_DEFAULT
from designfabric.core.generation.image_providers import ImageProviderName, create_image_provider
from designfabric.core.generation.llm_providers import LlmProviderName, create_llm_provider
from designfabric.core.generation.openrouter.errors import OpenRouterConfigError
from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime
from designfabric.core.generation.prompt_generator import apply_style_suffix, generate_concepts
from designfabric.core.generation.sticker_generator import StickerResult
from designfabric.core.progress import NullProgressReporter, ProgressReporter


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Resultado completo de un batch: prompts generados + resultado por imagen."""

    prompts: list[str]
    results: list[StickerResult]

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results if not r.success)


def resolve_llm_model(
    llm_provider: LlmProviderName,
    ollama_model: str,
) -> str:
    """Resuelve el model id según provider (OpenRouter desde runtime; Ollama del request)."""
    if llm_provider == "openrouter":
        model = (get_openrouter_runtime().snapshot().text_model_id or "").strip()
        if not model:
            raise OpenRouterConfigError(
                "OpenRouter LLM no está listo: falta text_model_id en configuración."
            )
        return model
    return ollama_model


def run_batch(
    num_images: int,
    ollama_model: str = OLLAMA_MODEL_DEFAULT,
    output_dir: str = "output",
    reporter: ProgressReporter = NullProgressReporter(),
    ollama_host: str | None = None,
    llm_provider: LlmProviderName = "ollama",
    image_provider: ImageProviderName = "flux",
) -> BatchResult:
    """Genera `num_images` stickers: conceptos vía LLM provider e imágenes vía image provider.

    `release` del LLM se ejecuta siempre en `finally` para liberar VRAM antes
    de cargar un motor de imagen local (p. ej. Flux).
    """
    model = resolve_llm_model(llm_provider, ollama_model)
    llm = create_llm_provider(llm_provider)
    try:
        prompts = generate_concepts(
            num_images,
            llm=llm,
            model=model,
            reporter=reporter,
            ollama_host=ollama_host,
        )
    finally:
        llm.release(model=model, host=ollama_host, reporter=reporter)

    image = create_image_provider(image_provider)
    results = image.generate_images(prompts, output_dir=output_dir, reporter=reporter)
    return BatchResult(prompts=prompts, results=results)


def run_single_image(
    prompt: str,
    apply_style: bool = True,
    output_dir: str = "output",
    reporter: ProgressReporter = NullProgressReporter(),
    image_provider: ImageProviderName = "flux",
) -> StickerResult:
    """Genera una única imagen a partir de un prompt libre, sin pasar por LLM.

    Si `apply_style` es True, se le concatena el mismo `STYLE_SUFFIX` que usa
    el flujo batch para mantener consistencia visual.
    """
    final_prompt = apply_style_suffix(prompt) if apply_style else prompt
    image = create_image_provider(image_provider)
    results = image.generate_images([final_prompt], output_dir=output_dir, reporter=reporter)
    return results[0]
