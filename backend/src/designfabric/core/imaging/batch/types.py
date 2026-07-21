"""Tipos del dominio de procesamiento por lotes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from designfabric.core.imaging.background_remover import RemovalConfig
from designfabric.core.imaging.background_removal_strategies import StrategyName
from designfabric.core.imaging.upscale_strategies import UpscaleStrategyName

BatchItemStatus = Literal["succeeded", "failed", "skipped"]
ScaleFactor = Literal[2, 4]
PROGRESS_PREFIX = "CLEARCUT_PROGRESS:"
ITEM_PREFIX = "CLEARCUT_ITEM:"


@dataclass(frozen=True, slots=True)
class BatchConfig:
    """Configuración uniforme aplicada a todos los archivos del lote."""

    removal_strategy: StrategyName
    scale_strategy: UpscaleStrategyName
    scale_factor: ScaleFactor
    removal: RemovalConfig = field(default_factory=RemovalConfig)


@dataclass(frozen=True, slots=True)
class BatchItemResult:
    """Resultado del procesamiento de un archivo del lote."""

    input_path: Path
    status: BatchItemStatus
    output_path: Path | None = None
    error: str | None = None
    warning: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "input": str(self.input_path),
            "output": str(self.output_path) if self.output_path is not None else None,
            "status": self.status,
            "error": self.error,
            "warning": self.warning,
        }


@dataclass(frozen=True, slots=True)
class BatchReport:
    """Resumen agregado del lote."""

    items: tuple[BatchItemResult, ...]
    cancelled: bool = False

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def succeeded(self) -> int:
        return sum(1 for item in self.items if item.status == "succeeded")

    @property
    def failed(self) -> int:
        return sum(1 for item in self.items if item.status == "failed")

    @property
    def skipped(self) -> int:
        return sum(1 for item in self.items if item.status == "skipped")

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "cancelled": self.cancelled,
            "items": [item.to_dict() for item in self.items],
        }
