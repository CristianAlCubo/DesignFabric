"""Orquestador del procesamiento por lotes (recorte → escalado)."""

from __future__ import annotations

import json
import logging
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import numpy as np

from designfabric.core.imaging.background_remover import RemovalConfig, process_image
from designfabric.core.imaging.batch.input_sources import InputSource, is_supported_image
from designfabric.core.imaging.batch.output_targets import OutputTarget
from designfabric.core.imaging.batch.types import (
    ITEM_PREFIX,
    PROGRESS_PREFIX,
    BatchConfig,
    BatchItemResult,
    BatchReport,
)
from designfabric.core.imaging.background_removal_strategies import (
    BackgroundRemovalStrategy,
    create_background_removal_strategy,
)
from designfabric.core.imaging.model_path_runtime import get_model_path_runtime
from designfabric.core.imaging.upscale_pipeline import ScaleOutcome, scale_image
from designfabric.core.progress import (
    Phase,
    ProgressReporter,
    emit_phase_completed,
    emit_phase_progress,
    emit_phase_started,
    emit_warning,
)

logger = logging.getLogger(__name__)

RemoveFn = Callable[[Path, Path, BackgroundRemovalStrategy, RemovalConfig], np.ndarray]
ScaleFn = Callable[..., ScaleOutcome]
ProgressCallback = Callable[[int, int, Path], None]
ItemCallback = Callable[[BatchItemResult], None]


class SupportsCancel(Protocol):
    def __call__(self) -> bool: ...


class BatchProcessor:
    """Ejecuta el pipeline completo sobre una fuente de entrada."""

    def __init__(
        self,
        *,
        remove_fn: RemoveFn = process_image,
        scale_fn: ScaleFn = scale_image,
    ) -> None:
        self._remove_fn = remove_fn
        self._scale_fn = scale_fn

    def run(
        self,
        config: BatchConfig,
        source: InputSource,
        target: OutputTarget,
        *,
        on_progress: ProgressCallback | None = None,
        on_item: ItemCallback | None = None,
        should_cancel: SupportsCancel | None = None,
        reporter: ProgressReporter | None = None,
    ) -> BatchReport:
        candidates = source.resolve()
        total = len(candidates)
        results: list[BatchItemResult] = []
        runtime = get_model_path_runtime()
        runtime.seed_from_settings()
        strategy = create_background_removal_strategy(
            config.removal_strategy,
            model_paths=runtime.resolve_paths(),
            max_iterations=config.removal.max_iterations,
        )
        cancelled = False

        if reporter is not None:
            emit_phase_started(reporter, Phase.CLEARCUT_BATCH, total=total)

        for index, input_path in enumerate(candidates, start=1):
            if should_cancel is not None and should_cancel():
                cancelled = True
                break

            if on_progress is not None:
                on_progress(index, total, input_path)
            # `current` = ítems ya terminados; `detail` = archivo que empieza ahora.
            # Así la UI puede mostrar "archivo en curso" sin inflar el avance.
            if reporter is not None:
                emit_phase_progress(
                    reporter,
                    Phase.CLEARCUT_BATCH,
                    index - 1,
                    total,
                    detail=str(input_path),
                )

            item = self._process_one(config, strategy, input_path, target)
            results.append(item)
            if on_item is not None:
                on_item(item)
            if reporter is not None and item.warning is not None:
                emit_warning(reporter, Phase.CLEARCUT_BATCH, item.warning)

            if reporter is not None:
                emit_phase_progress(
                    reporter,
                    Phase.CLEARCUT_BATCH,
                    index,
                    total,
                    detail=str(input_path),
                )

        if reporter is not None:
            emit_phase_completed(reporter, Phase.CLEARCUT_BATCH)

        return BatchReport(items=tuple(results), cancelled=cancelled)

    def _process_one(
        self,
        config: BatchConfig,
        strategy: BackgroundRemovalStrategy,
        input_path: Path,
        target: OutputTarget,
    ) -> BatchItemResult:
        path = Path(input_path)

        if not is_supported_image(path):
            return BatchItemResult(
                input_path=path,
                status="skipped",
                error=f"formato no soportado '{path.suffix}'",
            )

        if not path.is_file():
            return BatchItemResult(
                input_path=path,
                status="failed",
                error=f"No existe el archivo de entrada: {path}",
            )

        temp_path: Path | None = None
        try:
            output_path = target.resolve(path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
                temp_path = Path(handle.name)

            cutout = self._remove_fn(path, temp_path, strategy, config.removal)
            height, width = cutout.shape[:2]
            outcome = self._scale_fn(
                temp_path,
                output_path,
                strategy=config.scale_strategy,
                width=width * config.scale_factor,
                height=height * config.scale_factor,
            )
            warning = outcome.result.warning
            return BatchItemResult(
                input_path=path,
                status="succeeded",
                output_path=output_path,
                warning=warning,
            )
        except Exception as exc:  # noqa: BLE001 — el lote debe continuar
            logger.warning("Fallo al procesar %s: %s", path, exc)
            return BatchItemResult(
                input_path=path,
                status="failed",
                error=str(exc),
            )
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)


def run_batch(
    config: BatchConfig,
    source: InputSource,
    target: OutputTarget,
    *,
    on_progress: ProgressCallback | None = None,
    on_item: ItemCallback | None = None,
    should_cancel: SupportsCancel | None = None,
    reporter: ProgressReporter | None = None,
    processor: BatchProcessor | None = None,
) -> BatchReport:
    """Punto de entrada funcional del motor batch."""
    active = processor or BatchProcessor()
    return active.run(
        config,
        source,
        target,
        on_progress=on_progress,
        on_item=on_item,
        should_cancel=should_cancel,
        reporter=reporter,
    )


def emit_progress_line(current: int, total: int, path: Path) -> None:
    """Escribe una línea de progreso en stderr (protocolo CLI)."""
    sys.stderr.write(f"{PROGRESS_PREFIX}{current}/{total}:{path}\n")
    sys.stderr.flush()


def emit_item_line(item: BatchItemResult) -> None:
    """Escribe el resultado de un ítem en stderr (protocolo CLI)."""
    sys.stderr.write(f"{ITEM_PREFIX}{json.dumps(item.to_dict(), ensure_ascii=False)}\n")
    sys.stderr.flush()
