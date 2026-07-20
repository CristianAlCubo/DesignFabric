"""Generación de imágenes de stickers vía FLUX.2 Klein (diffusers).

Módulo de dominio puro: no imprime nada directamente, reporta su progreso a
través de un `ProgressReporter` y devuelve resultados estructurados
(`StickerResult`) para que los adaptadores (CLI, API) decidan cómo
mostrarlos o serializarlos.
"""

from __future__ import annotations

import os
import re
import random
from dataclasses import dataclass

import torch
from diffusers import Flux2KleinPipeline

from designfabric.core.progress import (
    Phase,
    ProgressReporter,
    NullProgressReporter,
    emit_phase_started,
    emit_phase_progress,
    emit_phase_completed,
    emit_phase_failed,
    emit_warning,
)

FLUX_MODEL_ID = "black-forest-labs/FLUX.2-klein-4B"
IMAGE_SIZE = 1024
GUIDANCE_SCALE = 1.0
NUM_INFERENCE_STEPS = 4


@dataclass(frozen=True, slots=True)
class StickerResult:
    """Resultado de generar un sticker a partir de un prompt."""

    prompt: str
    filename: str | None
    success: bool
    error: str | None = None


def slugify(text: str, max_len: int = 40) -> str:
    """Convierte texto libre en un slug apto para nombre de archivo."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:max_len]


def generate_stickers(
    prompts: list[str],
    output_dir: str = "output",
    reporter: ProgressReporter = NullProgressReporter(),
) -> list[StickerResult]:
    """Carga Flux2-Klein y genera una imagen por cada prompt ya construido.

    Los fallos individuales se capturan y no abortan el batch completo — la
    función siempre devuelve un `StickerResult` por prompt, exitoso o no.
    """
    os.makedirs(output_dir, exist_ok=True)

    device = "cuda"
    dtype = torch.bfloat16

    emit_phase_started(reporter, Phase.IMAGE_GENERATION, total=len(prompts))
    results: list[StickerResult] = []
    try:
        pipe = Flux2KleinPipeline.from_pretrained(FLUX_MODEL_ID, torch_dtype=dtype)
        pipe.enable_model_cpu_offload()
        pipe.set_progress_bar_config(disable=True)

        for i, prompt in enumerate(prompts):
            try:
                image = pipe(
                    prompt=prompt,
                    height=IMAGE_SIZE,
                    width=IMAGE_SIZE,
                    guidance_scale=GUIDANCE_SCALE,
                    num_inference_steps=NUM_INFERENCE_STEPS,
                    generator=torch.Generator(device=device).manual_seed(random.randint(0, 2**32 - 1)),
                ).images[0]

                filename = f"{output_dir}/sticker_{i + 1}_{slugify(prompt)}.png"
                image.save(filename)
                results.append(StickerResult(prompt=prompt, filename=filename, success=True))
                emit_phase_progress(reporter, Phase.IMAGE_GENERATION, i + 1, len(prompts), detail=filename)
            except Exception as e:
                results.append(StickerResult(prompt=prompt, filename=None, success=False, error=str(e)))
                emit_warning(reporter, Phase.IMAGE_GENERATION, f"Error generando el sticker {i + 1}: {e}")
                emit_phase_progress(reporter, Phase.IMAGE_GENERATION, i + 1, len(prompts))
    except Exception as e:
        emit_phase_failed(reporter, Phase.IMAGE_GENERATION, str(e))
        raise
    else:
        emit_phase_completed(reporter, Phase.IMAGE_GENERATION)

    return results
