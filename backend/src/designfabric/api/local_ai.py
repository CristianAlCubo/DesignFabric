"""Detección de deps del extra `local-ai` (Ollama/FLUX), sin importar routers."""

from __future__ import annotations

import importlib
import logging

logger = logging.getLogger(__name__)


def local_ai_deps_available() -> bool:
    """True si están instaladas las deps de Ollama/FLUX (`local-ai`)."""
    for module_name in ("torch", "diffusers", "ollama", "langchain_ollama"):
        try:
            importlib.import_module(module_name)
        except ImportError:
            return False
    return True


LOCAL_AI_AVAILABLE: bool = local_ai_deps_available()
if not LOCAL_AI_AVAILABLE:
    logger.warning(
        "Deps de IA local no disponibles (extra 'local-ai'): "
        "providers ollama/flux deshabilitados; test providers siguen disponibles."
    )
