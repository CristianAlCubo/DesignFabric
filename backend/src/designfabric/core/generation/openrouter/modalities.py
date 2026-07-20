"""Política de modalidades de request para generación de imagen OpenRouter.

Pura (sin I/O): traduce `output_modalities` del catálogo al parámetro
`modalities` (chat/completions multimodales) o decide el uso de `/images`
cuando el modelo solo declara salida `image`.
"""

from __future__ import annotations

from collections.abc import Sequence

from designfabric.core.generation.openrouter.errors import OpenRouterConfigError


def resolve_image_request_modalities(output_modalities: Sequence[str] | None) -> list[str]:
    """Deriva las modalities del request a partir de las capacidades del modelo.

    - image + text → ["image", "text"]
    - solo image → ["image"]
    - image + otras (p. ej. audio) → image (+ text si está)
    - sin image → OpenRouterConfigError
    """
    mods = {m.strip().casefold() for m in (output_modalities or []) if isinstance(m, str) and m.strip()}
    if "image" not in mods:
        raise OpenRouterConfigError(
            "El modelo seleccionado no declara capacidad de salida 'image'; "
            "no se puede usar como provider de imagen OpenRouter."
        )
    result = ["image"]
    if "text" in mods:
        result.append("text")
    return result
