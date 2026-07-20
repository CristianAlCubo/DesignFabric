"""Providers primitivos de generación de imagen (Strategy + Factory).

Sin lógica de estilo sticker ni conceptos: reciben prompts ya resueltos y
escriben archivos. El dominio (`pipeline` / `prompt_generator`) se construye encima.
"""

from __future__ import annotations

import os
import random
import shutil
from abc import ABC, abstractmethod
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Literal, Protocol

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
from designfabric.jobs.errors import JobCancelled

ImageProviderName = Literal["flux", "openrouter", "test"]
ShouldCancel = Callable[[], bool]

FLUX_MODEL_ID = "black-forest-labs/FLUX.2-klein-4B"
IMAGE_SIZE = 1024
GUIDANCE_SCALE = 1.0
NUM_INFERENCE_STEPS = 4


class _OpenRouterImageClient(Protocol):
    def list_models(self, modality: Literal["text", "image"]) -> list: ...

    def generate_image(
        self,
        prompt: str,
        *,
        model: str,
        modalities: list[str],
        image_options: dict | None = None,
        should_cancel: ShouldCancel | None = None,
    ) -> bytes: ...


class ImageProvider(ABC):
    """Motor de imagen: prompts → archivos en disco."""

    @abstractmethod
    def generate_images(
        self,
        prompts: list[str],
        *,
        output_dir: str,
        reporter: ProgressReporter = NullProgressReporter(),
        should_cancel: ShouldCancel | None = None,
        transparent_background: bool = True,
    ) -> list[StickerResult]:
        """Genera una imagen por prompt. Fallos individuales no abortan el batch."""


def _raise_if_cancelled(
    should_cancel: ShouldCancel | None,
    *,
    partial: list[StickerResult] | None = None,
) -> None:
    if should_cancel is not None and should_cancel():
        raise JobCancelled("Generación de imagen cancelada", partial_result=partial or [])


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
        should_cancel: ShouldCancel | None = None,
        transparent_background: bool = True,
    ) -> list[StickerResult]:
        del transparent_background
        os.makedirs(output_dir, exist_ok=True)
        source = _test_sticker_path()
        emit_phase_started(reporter, Phase.IMAGE_GENERATION, total=len(prompts))
        results: list[StickerResult] = []
        try:
            for i, prompt in enumerate(prompts):
                _raise_if_cancelled(should_cancel, partial=results)
                filename = f"{output_dir}/sticker_{i + 1}_{slugify(prompt)}.png"
                shutil.copyfile(source, filename)
                results.append(StickerResult(prompt=prompt, filename=filename, success=True))
                emit_phase_progress(reporter, Phase.IMAGE_GENERATION, i + 1, len(prompts), detail=filename)
        except JobCancelled:
            raise
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
        should_cancel: ShouldCancel | None = None,
        transparent_background: bool = True,
    ) -> list[StickerResult]:
        del transparent_background
        import torch
        from diffusers import Flux2KleinPipeline

        os.makedirs(output_dir, exist_ok=True)
        device = "cuda"
        dtype = torch.bfloat16

        emit_phase_started(reporter, Phase.IMAGE_GENERATION, total=len(prompts))
        results: list[StickerResult] = []
        try:
            _raise_if_cancelled(should_cancel, partial=results)
            pipe = Flux2KleinPipeline.from_pretrained(FLUX_MODEL_ID, torch_dtype=dtype)
            pipe.enable_model_cpu_offload()
            pipe.set_progress_bar_config(disable=True)

            for i, prompt in enumerate(prompts):
                _raise_if_cancelled(should_cancel, partial=results)
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
        except JobCancelled:
            raise
        except Exception as exc:
            emit_phase_failed(reporter, Phase.IMAGE_GENERATION, str(exc))
            raise
        else:
            emit_phase_completed(reporter, Phase.IMAGE_GENERATION)

        return results


class OpenRouterImageProvider(ImageProvider):
    """Generación de imagen vía OpenRouter; model id desde runtime config."""

    def generate_images(
        self,
        prompts: list[str],
        *,
        output_dir: str,
        reporter: ProgressReporter = NullProgressReporter(),
        should_cancel: ShouldCancel | None = None,
        transparent_background: bool = True,
    ) -> list[StickerResult]:
        from designfabric.core.generation.openrouter.client import build_client_from_runtime
        from designfabric.core.generation.openrouter.errors import (
            OpenRouterConfigError,
            OpenRouterRequestAborted,
        )
        from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime

        snap = get_openrouter_runtime().snapshot()
        model = (snap.image_model_id or "").strip()
        if not model:
            raise OpenRouterConfigError("Falta el modelo de imagen de OpenRouter.")

        client = build_client_from_runtime()
        modalities = self._resolve_modalities(snap.image_model_output_modalities, model, client)
        image_options = self._resolve_image_options(
            model,
            client,
            modalities,
            prefer_transparent=transparent_background,
        )

        os.makedirs(output_dir, exist_ok=True)
        emit_phase_started(reporter, Phase.IMAGE_GENERATION, total=len(prompts))
        results: list[StickerResult] = []
        try:
            for i, prompt in enumerate(prompts):
                _raise_if_cancelled(should_cancel, partial=results)
                try:
                    image_bytes = client.generate_image(
                        prompt,
                        model=model,
                        modalities=modalities,
                        image_options=image_options,
                        should_cancel=should_cancel,
                    )
                    filename = f"{output_dir}/sticker_{i + 1}_{slugify(prompt)}.png"
                    with open(filename, "wb") as handle:
                        handle.write(image_bytes)
                    results.append(StickerResult(prompt=prompt, filename=filename, success=True))
                    emit_phase_progress(reporter, Phase.IMAGE_GENERATION, i + 1, len(prompts), detail=filename)
                except OpenRouterRequestAborted as exc:
                    raise JobCancelled(str(exc), partial_result=results) from exc
                except JobCancelled:
                    raise
                except Exception as exc:
                    results.append(StickerResult(prompt=prompt, filename=None, success=False, error=str(exc)))
                    emit_warning(reporter, Phase.IMAGE_GENERATION, f"Error generando el sticker {i + 1}: {exc}")
                    emit_phase_progress(reporter, Phase.IMAGE_GENERATION, i + 1, len(prompts))
        except JobCancelled:
            raise
        except Exception as exc:
            emit_phase_failed(reporter, Phase.IMAGE_GENERATION, str(exc))
            raise
        else:
            emit_phase_completed(reporter, Phase.IMAGE_GENERATION)
        return results

    @staticmethod
    def _resolve_modalities(
        configured: tuple[str, ...] | None,
        model_id: str,
        client: _OpenRouterImageClient,
    ) -> list[str]:
        from designfabric.core.generation.openrouter.errors import OpenRouterConfigError
        from designfabric.core.generation.openrouter.modalities import resolve_image_request_modalities
        from designfabric.core.generation.openrouter.models_cache import get_models_cache

        if configured:
            return resolve_image_request_modalities(configured)

        cache = get_models_cache()
        models = cache.get_or_fetch("image", lambda: client.list_models("image"))
        match = next((m for m in models if m.id == model_id), None)
        if match is None:
            raise OpenRouterConfigError(
                f"No se encontraron output_modalities para el modelo de imagen '{model_id}'. "
                "Vuelve a seleccionarlo en Ajustes."
            )
        return resolve_image_request_modalities(match.output_modalities)

    @staticmethod
    def _resolve_image_options(
        model_id: str,
        client: _OpenRouterImageClient,
        modalities: list[str],
        *,
        prefer_transparent: bool,
    ) -> dict | None:
        """Extras de ``/images`` (transparency, etc.) solo si aplica Image API."""
        if "text" in {m.casefold() for m in modalities}:
            return None
        from designfabric.core.generation.openrouter.image_options import (
            resolve_image_request_options,
        )
        from designfabric.core.generation.openrouter.models_cache import get_models_cache

        cache = get_models_cache()
        models = cache.get_or_fetch("image", lambda: client.list_models("image"))
        match = next((m for m in models if m.id == model_id), None)
        params = match.supported_parameters if match is not None else None
        return resolve_image_request_options(params, prefer_transparent=prefer_transparent)


_PROVIDERS: dict[ImageProviderName, type[ImageProvider]] = {
    "flux": FluxImageProvider,
    "openrouter": OpenRouterImageProvider,
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
