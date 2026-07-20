"""ClearCut: pipeline de eliminación de fondo para ilustraciones tipo sticker/clipart/DTF."""

from designfabricv2.core.imaging.background_remover import RemovalConfig, StickerProcessor, process_image
from designfabricv2.core.imaging.silhouette_strategies import (
    ColorBackgroundStrategy,
    SilhouetteStrategy,
    StrategyName,
    WhiteBackgroundStrategy,
    create_silhouette_strategy,
)
from designfabricv2.core.imaging.model_assets import EnsureModelsReport, ensure_models
from designfabricv2.core.imaging.upscale_pipeline import ScaleOutcome, get_scale_defaults, scale_image
from designfabricv2.core.imaging.upscale_strategies import (
    RealEsrganUpscaleStrategy,
    UpscaleError,
    UpscaleStrategy,
    UpscaleStrategyName,
    VectorUpscaleStrategy,
    create_upscale_strategy,
)
from designfabricv2.core.imaging.vector_engine import (
    ExportConfig,
    TraceConfig,
    VectorEngine,
    VectorEngineError,
)

__all__ = [
    "RemovalConfig",
    "StickerProcessor",
    "process_image",
    "SilhouetteStrategy",
    "WhiteBackgroundStrategy",
    "ColorBackgroundStrategy",
    "StrategyName",
    "create_silhouette_strategy",
    "ExportConfig",
    "TraceConfig",
    "VectorEngine",
    "VectorEngineError",
    "get_scale_defaults",
    "scale_image",
    "ScaleOutcome",
    "UpscaleStrategy",
    "UpscaleStrategyName",
    "UpscaleError",
    "VectorUpscaleStrategy",
    "RealEsrganUpscaleStrategy",
    "create_upscale_strategy",
    "ensure_models",
    "EnsureModelsReport",
]
