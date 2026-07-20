"""Errores tipados del cliente OpenRouter."""

from __future__ import annotations


class OpenRouterError(Exception):
    """Error base de la integración OpenRouter."""


class OpenRouterAuthError(OpenRouterError):
    """API key ausente o rechazada (401/403)."""


class OpenRouterRateLimitError(OpenRouterError):
    """Límite de tasa excedido (429)."""


class OpenRouterApiError(OpenRouterError):
    """Respuesta de error genérica de la API."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenRouterConfigError(OpenRouterError):
    """Configuración incompleta (key o modelo ausente)."""
