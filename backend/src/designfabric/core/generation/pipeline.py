"""Facade del pipeline completo de generación.

Reúne la orquestación que antes vivía en `app.py` (generar conceptos,
descargar Ollama, generar imágenes) en dos funciones reutilizables por
cualquier adaptador (CLI, worker de la API): `run_batch` (equivalente al
flujo actual del CLI) y `run_single_image` (nueva funcionalidad: generar una
única imagen a partir de un prompt libre, sin pasar por Ollama).
"""

from __future__ import annotations

from dataclasses import dataclass

from designfabric.core.progress import NullProgressReporter, ProgressReporter
from designfabric.core.generation.prompt_generator import (
    OLLAMA_MODEL_DEFAULT,
    apply_style_suffix,
    generate_concepts,
    unload_ollama,
)
from designfabric.core.generation.sticker_generator import StickerResult, generate_stickers


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Resultado completo de un batch: prompts generados + resultado por imagen."""

    prompts: list[str]
    results: list[StickerResult]

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results if not r.success)


def run_batch(
    num_images: int,
    ollama_model: str = OLLAMA_MODEL_DEFAULT,
    output_dir: str = "output",
    reporter: ProgressReporter = NullProgressReporter(),
    ollama_host: str | None = None,
) -> BatchResult:
    """Genera `num_images` stickers: idea conceptos vía Ollama y los renderiza con Flux.

    Equivalente al flujo actual del CLI (`--n`). `unload_ollama` se ejecuta
    siempre, incluso si la generación de conceptos falla a mitad de camino,
    para no dejar el modelo ocupando VRAM innecesariamente antes de cargar Flux.
    """
    try:
        prompts = generate_concepts(num_images, model=ollama_model, reporter=reporter, ollama_host=ollama_host)
    finally:
        unload_ollama(model=ollama_model, reporter=reporter, ollama_host=ollama_host)

    results = generate_stickers(prompts, output_dir=output_dir, reporter=reporter)
    return BatchResult(prompts=prompts, results=results)


def run_single_image(
    prompt: str,
    apply_style: bool = True,
    output_dir: str = "output",
    reporter: ProgressReporter = NullProgressReporter(),
) -> StickerResult:
    """Genera una única imagen a partir de un prompt libre, sin pasar por Ollama.

    Si `apply_style` es True, se le concatena el mismo `STYLE_SUFFIX` que usa
    el flujo batch para mantener consistencia visual con los stickers generados
    por conceptos automáticos.
    """
    final_prompt = apply_style_suffix(prompt) if apply_style else prompt
    results = generate_stickers([final_prompt], output_dir=output_dir, reporter=reporter)
    return results[0]
