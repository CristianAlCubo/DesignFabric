"""Detección de deps del extra `local-ai` (Ollama/FLUX), sin importar routers."""

from __future__ import annotations

import logging

from designfabric.core.generation.local_ai_deps import (
    LOCAL_AI_MODULES,
    local_ai_deps_available,
    missing_local_ai_modules,
)

logger = logging.getLogger(__name__)

__all__ = [
    "LOCAL_AI_AVAILABLE",
    "LOCAL_AI_MODULES",
    "local_ai_deps_available",
    "missing_local_ai_modules",
]

LOCAL_AI_AVAILABLE: bool = local_ai_deps_available()
if not LOCAL_AI_AVAILABLE:
    logger.warning(
        "Deps de IA local no disponibles (extra 'local-ai'): "
        "providers ollama/flux deshabilitados; test providers siguen disponibles."
    )
