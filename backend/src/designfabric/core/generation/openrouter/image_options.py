"""Política de parámetros opcionales para POST /images (capabilities-driven).

Pura (sin I/O): traduce `supported_parameters` del catálogo Image API al body
extra (p. ej. transparency nativa solo si el modelo la declara y el usuario
la quiere).
"""

from __future__ import annotations

from typing import Any, Mapping


def supports_transparent_background(supported_parameters: Mapping[str, Any] | None) -> bool:
    """True si el catálogo declara ``background=transparent``."""
    params = supported_parameters or {}
    return _enum_allows(params.get("background"), "transparent")


def resolve_image_request_options(
    supported_parameters: Mapping[str, Any] | None,
    *,
    prefer_transparent: bool = True,
) -> dict[str, Any]:
    """Deriva extras del request `/images` a partir de las capabilities del modelo.

    - Sin catálogo / sin params → ``{"output_format": "png"}`` (seguro, sin background).
    - ``background: transparent`` solo si el modelo lo declara y ``prefer_transparent``.
    """
    params = supported_parameters or {}
    options: dict[str, Any] = {}

    output_format = _pick_alpha_format(params.get("output_format"))
    if output_format is None:
        output_format = "png"
    options["output_format"] = output_format

    if (
        prefer_transparent
        and supports_transparent_background(params)
        and output_format in ("png", "webp")
    ):
        options["background"] = "transparent"

    return options


def _pick_alpha_format(descriptor: Any) -> str | None:
    if _enum_allows(descriptor, "png"):
        return "png"
    if _enum_allows(descriptor, "webp"):
        return "webp"
    return None


def _enum_allows(descriptor: Any, value: str) -> bool:
    if not isinstance(descriptor, dict):
        return False
    if descriptor.get("type") != "enum":
        return False
    values = descriptor.get("values")
    if not isinstance(values, list):
        return False
    needle = value.casefold()
    return any(isinstance(v, str) and v.casefold() == needle for v in values)
