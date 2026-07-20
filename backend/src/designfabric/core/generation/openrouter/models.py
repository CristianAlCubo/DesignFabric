"""DTOs internos del catálogo de modelos OpenRouter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

OutputModality = Literal["text", "image"]


@dataclass(frozen=True, slots=True)
class OpenRouterModel:
    """Entrada ligera del catálogo (id + nombre + modalidades de salida)."""

    id: str
    name: str
    output_modalities: tuple[str, ...]

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> OpenRouterModel | None:
        model_id = payload.get("id")
        if not isinstance(model_id, str) or not model_id:
            return None
        name = payload.get("name")
        if not isinstance(name, str) or not name:
            name = model_id
        architecture = payload.get("architecture") or {}
        modalities = architecture.get("output_modalities") if isinstance(architecture, dict) else None
        if not isinstance(modalities, list):
            modalities = []
        cleaned = tuple(str(m) for m in modalities if isinstance(m, str))
        return cls(id=model_id, name=name, output_modalities=cleaned)

    def matches_query(self, query: str) -> bool:
        if not query:
            return True
        needle = query.casefold().strip()
        return needle in self.id.casefold() or needle in self.name.casefold()
