"""Facade del pipeline completo de generación.

Orquesta dominio de conceptos + providers primitivos (LLM e imagen).
Reutilizable por CLI y workers de la API.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from designfabric.core.generation.constants import OLLAMA_MODEL_DEFAULT
from designfabric.core.generation.image_providers import ImageProviderName, create_image_provider
from designfabric.core.generation.llm_providers import LlmProviderName, create_llm_provider
from designfabric.core.generation.openrouter.errors import OpenRouterConfigError
from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime
from designfabric.core.generation.prompt_generator import apply_style_suffix, generate_concepts
from designfabric.core.generation.sticker_generator import StickerResult
from designfabric.core.progress import NullProgressReporter, ProgressReporter
from designfabric.jobs.errors import JobCancelled


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Resultado completo de un batch: prompts generados + resultado por imagen."""

    prompts: list[str]
    results: list[StickerResult]
    cancelled: bool = False

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
    transparent_background: bool = True,
    should_cancel: Callable[[], bool] | None = None,
) -> BatchResult:
    """Genera `num_images` stickers: conceptos vía LLM provider e imágenes vía image provider.

    `release` del LLM se ejecuta siempre en `finally` para liberar VRAM antes
    de cargar un motor de imagen local (p. ej. Flux).
    """
    model = resolve_llm_model(llm_provider, ollama_model)
    llm = create_llm_provider(llm_provider)
    prompts: list[str] = []
    try:
        try:
            prompts = generate_concepts(
                num_images,
                llm=llm,
                model=model,
                reporter=reporter,
                ollama_host=ollama_host,
                should_cancel=should_cancel,
            )
        except JobCancelled as exc:
            partial_prompts = exc.partial_result if isinstance(exc.partial_result, list) else []
            raise JobCancelled(
                str(exc),
                partial_result=BatchResult(
                    prompts=partial_prompts,
                    results=[],
                    cancelled=True,
                ),
            ) from exc
    finally:
        llm.release(model=model, host=ollama_host, reporter=reporter)

    image = create_image_provider(image_provider)
    try:
        results = image.generate_images(
            prompts,
            output_dir=output_dir,
            reporter=reporter,
            should_cancel=should_cancel,
            transparent_background=transparent_background,
        )
    except JobCancelled as exc:
        partial_results = exc.partial_result if isinstance(exc.partial_result, list) else []
        raise JobCancelled(
            str(exc),
            partial_result=BatchResult(
                prompts=prompts,
                results=partial_results,
                cancelled=True,
            ),
        ) from exc

    if should_cancel is not None and should_cancel():
        raise JobCancelled(
            "Batch cancelado",
            partial_result=BatchResult(prompts=prompts, results=results, cancelled=True),
        )

    return BatchResult(prompts=prompts, results=results)


def run_single_image(
    prompt: str,
    apply_style: bool = True,
    output_dir: str = "output",
    reporter: ProgressReporter = NullProgressReporter(),
    image_provider: ImageProviderName = "flux",
    transparent_background: bool = True,
    should_cancel: Callable[[], bool] | None = None,
) -> StickerResult:
    """Genera una única imagen a partir de un prompt libre, sin pasar por LLM.

    Si `apply_style` es True, se le concatena el mismo `STYLE_SUFFIX` que usa
    el flujo batch para mantener consistencia visual.
    """
    if should_cancel is not None and should_cancel():
        raise JobCancelled("Imagen única cancelada")

    final_prompt = apply_style_suffix(prompt) if apply_style else prompt
    image = create_image_provider(image_provider)
    try:
        results = image.generate_images(
            [final_prompt],
            output_dir=output_dir,
            reporter=reporter,
            should_cancel=should_cancel,
            transparent_background=transparent_background,
        )
    except JobCancelled:
        raise
    return results[0]
