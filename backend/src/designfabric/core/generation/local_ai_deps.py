"""Detección de deps Python del extra `local-ai` (sin FastAPI ni routers)."""

from __future__ import annotations

import importlib

LOCAL_AI_MODULES: tuple[str, ...] = ("torch", "diffusers", "ollama", "langchain_ollama")


def missing_local_ai_modules() -> tuple[str, ...]:
    """Nombres de módulos del extra `local-ai` que no se pueden importar."""
    missing: list[str] = []
    for module_name in LOCAL_AI_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)
    return tuple(missing)


def local_ai_deps_available() -> bool:
    """True si están instaladas las deps de Ollama/FLUX (`local-ai`)."""
    return len(missing_local_ai_modules()) == 0
