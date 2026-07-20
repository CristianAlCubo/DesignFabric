"""Integración base OpenRouter: client, runtime config y DTOs."""

from designfabric.core.generation.openrouter.client import (
    OpenRouterClient,
    build_client_from_runtime,
)
from designfabric.core.generation.openrouter.errors import (
    OpenRouterApiError,
    OpenRouterAuthError,
    OpenRouterConfigError,
    OpenRouterError,
    OpenRouterRateLimitError,
)
from designfabric.core.generation.openrouter.image_options import (
    resolve_image_request_options,
    supports_transparent_background,
)
from designfabric.core.generation.openrouter.modalities import resolve_image_request_modalities
from designfabric.core.generation.openrouter.models import OpenRouterModel, OutputModality
from designfabric.core.generation.openrouter.runtime_config import (
    OpenRouterRuntimeConfig,
    OpenRouterSnapshot,
    get_openrouter_runtime,
)

__all__ = [
    "OpenRouterApiError",
    "OpenRouterAuthError",
    "OpenRouterClient",
    "OpenRouterConfigError",
    "OpenRouterError",
    "OpenRouterModel",
    "OpenRouterRateLimitError",
    "OpenRouterRuntimeConfig",
    "OpenRouterSnapshot",
    "OutputModality",
    "build_client_from_runtime",
    "get_openrouter_runtime",
    "resolve_image_request_modalities",
    "resolve_image_request_options",
    "supports_transparent_background",
]
