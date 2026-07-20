"""Providers primitivos de generación de imagen (Strategy + Factory).

Sin lógica de estilo sticker ni conceptos: reciben prompts ya resueltos y
escriben archivos. El dominio (`pipeline` / `prompt_generator`) se construye encima.
"""

from __future__ import annotations

import os
import random
import shutil
from abc import ABC, abstractmethod
from importlib import resources
from pathlib import Path
from typing import Literal

from designfabric.core.generation.sticker_generator import StickerResult, slugify
from designfabric.core.progress import (
    NullProgressReporter,
    Phase,
    ProgressReporter,
    emit_phase_completed,
    emit_phase_failed,
    emit_phase_progress,
    emit_phase_started,
    emit_warning,
)

ImageProviderName = Literal["flux", "test"]

FLUX_MODEL_ID = "black-forest-labs/FLUX.2-klein-4B"
IMAGE_SIZE = 1024
GUIDANCE_SCALE = 1.0
NUM_INFERENCE_STEPS = 4


class ImageProvider(ABC):
    """Motor de imagen: prompts → archivos en disco."""

    @abstractmethod
    def generate_images(
        self,
        prompts: list[str],
        *,
        output_dir: str,
        reporter: ProgressReporter = NullProgressReporter(),
    ) -> list[StickerResult]:
        """Genera una imagen por prompt. Fallos individuales no abortan el batch."""


def _test_sticker_path() -> Path:
    """Ruta al PNG fijo empaquetado con el paquete."""
    return Path(str(resources.files("designfabric.core.generation.assets").joinpath("test_sticker.png")))


class TestImageProvider(ImageProvider):
    """Stub: copia siempre el mismo PNG por cada prompt."""

    def generate_images(
        self,
        prompts: list[str],
        *,
        output_dir: str,
        reporter: ProgressReporter = NullProgressReporter(),
    ) -> list[StickerResult]:
        os.makedirs(output_dir, exist_ok=True)
        source = _test_sticker_path()
        emit_phase_started(reporter, Phase.IMAGE_GENERATION, total=len(prompts))
        results: list[StickerResult] = []
        try:
            for i, prompt in enumerate(prompts):
                filename = f"{output_dir}/sticker_{i + 1}_{slugify(prompt)}.png"
                shutil.copyfile(source, filename)
                results.append(StickerResult(prompt=prompt, filename=filename, success=True))
                emit_phase_progress(reporter, Phase.IMAGE_GENERATION, i + 1, len(prompts), detail=filename)
        except Exception as exc:
            emit_phase_failed(reporter, Phase.IMAGE_GENERATION, str(exc))
            raise
        else:
            emit_phase_completed(reporter, Phase.IMAGE_GENERATION)
        return results


class FluxImageProvider(ImageProvider):
    """Wrapper fino sobre Flux2KleinPipeline (imports lazy)."""

    def generate_images(
        self,
        prompts: list[str],
        *,
        output_dir: str,
        reporter: ProgressReporter = NullProgressReporter(),
    ) -> list[StickerResult]:
        import torch
        from diffusers import Flux2KleinPipeline

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
                except Exception as exc:
                    results.append(StickerResult(prompt=prompt, filename=None, success=False, error=str(exc)))
                    emit_warning(reporter, Phase.IMAGE_GENERATION, f"Error generando el sticker {i + 1}: {exc}")
                    emit_phase_progress(reporter, Phase.IMAGE_GENERATION, i + 1, len(prompts))
        except Exception as exc:
            emit_phase_failed(reporter, Phase.IMAGE_GENERATION, str(exc))
            raise
        else:
            emit_phase_completed(reporter, Phase.IMAGE_GENERATION)

        return results


_PROVIDERS: dict[ImageProviderName, type[ImageProvider]] = {
    "flux": FluxImageProvider,
    "test": TestImageProvider,
}


def create_image_provider(name: ImageProviderName) -> ImageProvider:
    """Crea un provider de imagen por nombre."""
    try:
        provider_cls = _PROVIDERS[name]
    except KeyError as exc:
        raise ValueError(
            f"Provider de imagen desconocido '{name}'. Opciones: {sorted(_PROVIDERS)}"
        ) from exc
    return provider_cls()


def list_image_provider_names() -> tuple[ImageProviderName, ...]:
    return tuple(_PROVIDERS.keys())
