"""Configuración OpenRouter mutable en runtime (singleton thread-safe).

Electron (o env) siembra/actualiza estos valores; providers y readiness los leen.
No persiste a disco: la fuente durable es el proceso main de Electron.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from designfabric.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class OpenRouterSnapshot:
    """Vista inmutable del estado actual (sin exponer mutación)."""

    api_key: str | None
    text_model_id: str | None
    image_model_id: str | None
    image_model_output_modalities: tuple[str, ...] | None
    base_url: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    @property
    def llm_ready(self) -> bool:
        return self.configured and bool(self.text_model_id and self.text_model_id.strip())

    @property
    def image_ready(self) -> bool:
        return self.configured and bool(self.image_model_id and self.image_model_id.strip())


_UNSET: object = object()


class OpenRouterRuntimeConfig:
    """Singleton: key + model IDs mutables sin reiniciar el proceso."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._api_key: str | None = None
        self._text_model_id: str | None = None
        self._image_model_id: str | None = None
        self._image_model_output_modalities: tuple[str, ...] | None = None
        self._base_url: str = "https://openrouter.ai/api/v1"
        self._seeded = False

    def seed_from_settings(self, settings: Settings | None = None) -> None:
        """Aplica valores de Settings/env solo si aún no hay overrides de runtime."""
        cfg = settings or get_settings()
        with self._lock:
            if not self._seeded:
                self._api_key = cfg.openrouter_api_key or None
                self._text_model_id = cfg.openrouter_text_model or None
                self._image_model_id = cfg.openrouter_image_model or None
                self._base_url = cfg.openrouter_base_url.rstrip("/")
                self._seeded = True
                return
            # Si ya hubo seed, solo rellenar huecos desde Settings (no pisar PUT).
            if not self._api_key and cfg.openrouter_api_key:
                self._api_key = cfg.openrouter_api_key
            if not self._text_model_id and cfg.openrouter_text_model:
                self._text_model_id = cfg.openrouter_text_model
            if not self._image_model_id and cfg.openrouter_image_model:
                self._image_model_id = cfg.openrouter_image_model
            if cfg.openrouter_base_url:
                self._base_url = cfg.openrouter_base_url.rstrip("/")

    def update(
        self,
        *,
        api_key: str | None = None,
        clear_api_key: bool = False,
        text_model_id: str | None = None,
        image_model_id: str | None = None,
        image_model_output_modalities: list[str] | tuple[str, ...] | None | object = _UNSET,
        clear_text_model: bool = False,
        clear_image_model: bool = False,
        base_url: str | None = None,
    ) -> OpenRouterSnapshot:
        with self._lock:
            self._seeded = True
            if clear_api_key:
                self._api_key = None
            elif api_key is not None:
                stripped = api_key.strip()
                self._api_key = stripped or None
            if clear_text_model:
                self._text_model_id = None
            elif text_model_id is not None:
                stripped = text_model_id.strip()
                self._text_model_id = stripped or None
            if clear_image_model:
                self._image_model_id = None
                self._image_model_output_modalities = None
            else:
                if image_model_id is not None:
                    stripped = image_model_id.strip()
                    self._image_model_id = stripped or None
                    if not self._image_model_id:
                        self._image_model_output_modalities = None
                if image_model_output_modalities is not _UNSET:
                    if image_model_output_modalities is None:
                        self._image_model_output_modalities = None
                    else:
                        cleaned = tuple(
                            m.strip()
                            for m in image_model_output_modalities  # type: ignore[union-attr]
                            if isinstance(m, str) and m.strip()
                        )
                        self._image_model_output_modalities = cleaned or None
            if base_url is not None:
                self._base_url = base_url.rstrip("/")
            return self.snapshot()

    def snapshot(self) -> OpenRouterSnapshot:
        with self._lock:
            return OpenRouterSnapshot(
                api_key=self._api_key,
                text_model_id=self._text_model_id,
                image_model_id=self._image_model_id,
                image_model_output_modalities=self._image_model_output_modalities,
                base_url=self._base_url,
            )

    def reset_for_tests(self) -> None:
        """Limpia estado (solo tests)."""
        with self._lock:
            self._api_key = None
            self._text_model_id = None
            self._image_model_id = None
            self._image_model_output_modalities = None
            self._base_url = "https://openrouter.ai/api/v1"
            self._seeded = False


_runtime = OpenRouterRuntimeConfig()


def get_openrouter_runtime() -> OpenRouterRuntimeConfig:
    return _runtime
