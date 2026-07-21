"""Configuración centralizada de la aplicación.

Todos los valores son sobreescribibles vía variables de entorno con el
prefijo `DESIGNFABRIC_` (ej. `DESIGNFABRIC_OUTPUT_DIR=/otra/ruta`).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from designfabric.core.generation.constants import OLLAMA_MODEL_DEFAULT


class Settings(BaseSettings):
    """Configuración de runtime del backend, cargada de variables de entorno."""

    model_config = SettingsConfigDict(env_prefix="DESIGNFABRIC_")

    output_dir: str = "output"
    ollama_host: str = "http://localhost:11434"
    ollama_model_default: str = OLLAMA_MODEL_DEFAULT
    api_port: int = 8756
    # Solo localhost: es un backend local para la app de escritorio, nunca se expone en red.
    api_host: str = "127.0.0.1"

    # OpenRouter (bootstrap vía env; la app de escritorio sincroniza runtime vía API).
    openrouter_api_key: str | None = None
    openrouter_text_model: str | None = None
    openrouter_image_model: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Modelos locales ONNX para eliminación de fondo (rutas absolutas; sync vía Settings UI).
    sam2_encoder_onnx: str | None = None
    sam2_decoder_onnx: str | None = None
    vitmatte_onnx: str | None = None
    isnet_general_onnx: str | None = None


def get_settings() -> Settings:
    """Punto único de acceso a la configuración (facilita mockear en tests)."""
    return Settings()
