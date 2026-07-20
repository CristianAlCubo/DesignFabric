"""ClearCut: pipeline de eliminación de fondo para ilustraciones tipo sticker/clipart/DTF."""

from designfabric.core.imaging.background_remover import RemovalConfig, StickerProcessor, process_image
from designfabric.core.imaging.silhouette_strategies import (
    ColorBackgroundStrategy,
    SilhouetteStrategy,
    StrategyName,
    WhiteBackgroundStrategy,
    create_silhouette_strategy,
)
from designfabric.core.imaging.model_assets import EnsureModelsReport, ensure_models
from designfabric.core.imaging.upscale_pipeline import ScaleOutcome, get_scale_defaults, scale_image
from designfabric.core.imaging.upscale_strategies import (
    RealEsrganUpscaleStrategy,
    UpscaleError,
    UpscaleStrategy,
    UpscaleStrategyName,
    create_upscale_strategy,
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
    "get_scale_defaults",
    "scale_image",
    "ScaleOutcome",
    "UpscaleStrategy",
    "UpscaleStrategyName",
    "UpscaleError",
    "RealEsrganUpscaleStrategy",
    "create_upscale_strategy",
    "ensure_models",
    "EnsureModelsReport",
]
