"""Configuración centralizada de la aplicación.

Todos los valores son sobreescribibles vía variables de entorno con el
prefijo `DESIGNFABRIC_` (ej. `DESIGNFABRIC_OUTPUT_DIR=/otra/ruta`).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from designfabricv2.core.generation.constants import OLLAMA_MODEL_DEFAULT


class Settings(BaseSettings):
    """Configuración de runtime del backend, cargada de variables de entorno."""

    model_config = SettingsConfigDict(env_prefix="DESIGNFABRIC_")

    output_dir: str = "output"
    ollama_host: str = "http://localhost:11434"
    ollama_model_default: str = OLLAMA_MODEL_DEFAULT
    api_port: int = 8756
    # Solo localhost: es un backend local para la app de escritorio, nunca se expone en red.
    api_host: str = "127.0.0.1"


def get_settings() -> Settings:
    """Punto único de acceso a la configuración (facilita mockear en tests)."""
    return Settings()
