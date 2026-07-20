"""Procesamiento por lotes: recorte + escalado con configuración uniforme."""

from designfabric.core.imaging.batch.input_sources import (
    FilesInputSource,
    FolderInputSource,
    InputSource,
    create_input_source,
    is_supported_image,
)
from designfabric.core.imaging.batch.output_targets import (
    DirectoryOutputTarget,
    OutputTarget,
    create_output_target,
)
from designfabric.core.imaging.batch.processor import (
    BatchProcessor,
    emit_item_line,
    emit_progress_line,
    run_batch,
)
from designfabric.core.imaging.batch.types import (
    ITEM_PREFIX,
    PROGRESS_PREFIX,
    BatchConfig,
    BatchItemResult,
    BatchItemStatus,
    BatchReport,
    ScaleFactor,
)

__all__ = [
    "ITEM_PREFIX",
    "PROGRESS_PREFIX",
    "BatchConfig",
    "BatchItemResult",
    "BatchItemStatus",
    "BatchProcessor",
    "BatchReport",
    "DirectoryOutputTarget",
    "FilesInputSource",
    "FolderInputSource",
    "InputSource",
    "OutputTarget",
    "ScaleFactor",
    "create_input_source",
    "create_output_target",
    "emit_item_line",
    "emit_progress_line",
    "is_supported_image",
    "run_batch",
]
