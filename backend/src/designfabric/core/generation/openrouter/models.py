"""DTOs internos del catálogo de modelos OpenRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, Mapping

OutputModality = Literal["text", "image"]


@dataclass(frozen=True, slots=True)
class OpenRouterModel:
    """Entrada ligera del catálogo (id + nombre + modalidades + capabilities)."""

    id: str
    name: str
    output_modalities: tuple[str, ...]
    supported_parameters: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

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
        raw_params = payload.get("supported_parameters")
        if isinstance(raw_params, dict):
            params = MappingProxyType(dict(raw_params))
        else:
            params = MappingProxyType({})
        return cls(
            id=model_id,
            name=name,
            output_modalities=cleaned,
            supported_parameters=params,
        )

    def matches_query(self, query: str) -> bool:
        if not query:
            return True
        needle = query.casefold().strip()
        return needle in self.id.casefold() or needle in self.name.casefold()
