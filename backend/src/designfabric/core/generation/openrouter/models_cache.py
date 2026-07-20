"""Cache in-memory del catálogo OpenRouter por modalidad (TTL)."""

from __future__ import annotations

import threading
import time
from typing import Callable

from designfabric.core.generation.openrouter.models import OpenRouterModel, OutputModality

_DEFAULT_TTL_S = 300.0


class OpenRouterModelsCache:
    """Cache thread-safe: modality → (expires_at, models)."""

    def __init__(self, ttl_s: float = _DEFAULT_TTL_S) -> None:
        self._ttl_s = ttl_s
        self._lock = threading.RLock()
        self._entries: dict[OutputModality, tuple[float, list[OpenRouterModel]]] = {}

    def get_or_fetch(
        self,
        modality: OutputModality,
        fetcher: Callable[[], list[OpenRouterModel]],
    ) -> list[OpenRouterModel]:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(modality)
            if entry is not None and entry[0] > now:
                return list(entry[1])
        models = fetcher()
        with self._lock:
            self._entries[modality] = (time.monotonic() + self._ttl_s, list(models))
        return list(models)

    def invalidate(self) -> None:
        with self._lock:
            self._entries.clear()


_models_cache = OpenRouterModelsCache()


def get_models_cache() -> OpenRouterModelsCache:
    return _models_cache
