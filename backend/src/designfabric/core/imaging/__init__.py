"""ClearCut: pipeline de eliminación de fondo y escalado de imágenes."""

from designfabric.core.imaging.background_remover import (
    BackgroundRemover,
    RemovalConfig,
    process_image,
)
from designfabric.core.imaging.background_removal_strategies import (
    BackgroundRemovalStrategy,
    ColorBackgroundStrategy,
    RemovalModelPaths,
    StrategyName,
    WhiteBackgroundStrategy,
    create_background_removal_strategy,
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
    "BackgroundRemover",
    "process_image",
    "BackgroundRemovalStrategy",
    "WhiteBackgroundStrategy",
    "ColorBackgroundStrategy",
    "RemovalModelPaths",
    "StrategyName",
    "create_background_removal_strategy",
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
