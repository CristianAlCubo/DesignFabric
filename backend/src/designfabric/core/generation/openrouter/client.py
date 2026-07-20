"""Cliente HTTP de OpenRouter (listado de modelos + chat + imagen)."""

from __future__ import annotations

import base64
import concurrent.futures
import json
import re
import time
from collections.abc import Callable
from typing import Any, Sequence
from urllib.parse import urlencode

import httpx

from designfabric.core.generation.llm_providers import ChatMessage
from designfabric.core.generation.openrouter.errors import (
    OpenRouterApiError,
    OpenRouterAuthError,
    OpenRouterConfigError,
    OpenRouterRateLimitError,
    OpenRouterRequestAborted,
)
from designfabric.core.generation.openrouter.models import OpenRouterModel, OutputModality

_DEFAULT_TIMEOUT = 120.0
_DATA_URL_RE = re.compile(r"^data:(image/[^;]+);base64,(.+)$", re.DOTALL)


class OpenRouterClient:
    """Facade HTTP sobre la API OpenRouter (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = _DEFAULT_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise OpenRouterConfigError("Falta la API key de OpenRouter.")
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://designfabric.local",
            "X-Title": "DesignFabric",
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url,
            headers=self._headers(),
            timeout=self._timeout,
            transport=self._transport,
        )

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code in (401, 403):
            raise OpenRouterAuthError(
                f"OpenRouter rechazó la API key (HTTP {response.status_code})."
            )
        if response.status_code == 429:
            raise OpenRouterRateLimitError("OpenRouter: límite de tasa excedido.")
        if response.status_code >= 400:
            detail = response.text[:500]
            raise OpenRouterApiError(
                f"OpenRouter error HTTP {response.status_code}: {detail}",
                status_code=response.status_code,
            )

    def list_models(self, modality: OutputModality) -> list[OpenRouterModel]:
        """Lista modelos filtrados por modalidad de salida en la API.

        Para ``image``, combina el catálogo general con ``/images/models``
        (que trae ``supported_parameters``: transparency, size, etc.).
        """
        if modality == "image":
            return self._list_image_models()
        return self._list_models_from_path(f"/models?{urlencode({'output_modalities': modality})}")

    def _list_image_models(self) -> list[OpenRouterModel]:
        general = self._list_models_from_path(
            f"/models?{urlencode({'output_modalities': 'image'})}"
        )
        dedicated = self._list_models_from_path("/images/models")
        by_id: dict[str, OpenRouterModel] = {m.id: m for m in general}
        for model in dedicated:
            by_id[model.id] = model
        return list(by_id.values())

    def _list_models_from_path(self, path: str) -> list[OpenRouterModel]:
        with self._client() as client:
            response = client.get(path)
            self._raise_for_status(response)
            payload = response.json()
        raw_items = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(raw_items, list):
            return []
        models: list[OpenRouterModel] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            parsed = OpenRouterModel.from_api(item)
            if parsed is not None:
                models.append(parsed)
        return models

    @staticmethod
    def filter_models(models: Sequence[OpenRouterModel], query: str | None) -> list[OpenRouterModel]:
        if not query or not query.strip():
            return list(models)
        return [m for m in models if m.matches_query(query)]

    def chat_completion(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str,
        temperature: float = 0.9,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Completación de texto; devuelve el content string del primer choice."""
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if extra:
            body.update(extra)
        with self._client() as client:
            response = client.post("/chat/completions", content=json.dumps(body))
            self._raise_for_status(response)
            payload = response.json()
        return _extract_text_content(payload)

    def generate_image(
        self,
        prompt: str,
        *,
        model: str,
        modalities: Sequence[str],
        image_options: dict[str, Any] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> bytes:
        """Genera una imagen y devuelve bytes PNG/JPEG decodificados.

        `modalities` es obligatorio (p. ej. ["image"] o ["image","text"]) —
        debe derivarse de las output_modalities del modelo vía
        `resolve_image_request_modalities`.

        - Solo ``image`` → ``POST /images`` (Image API dedicada; p. ej. gpt-image-2).
        - ``image`` + ``text`` → ``POST /chat/completions`` (modelos multimodales).

        `image_options` (solo path ``/images``) debe venir de
        `resolve_image_request_options` (transparency solo si el modelo la declara).

        Si se pasa `should_cancel`, la request HTTP se puede abortar en vuelo
        cerrando el client (lanza `OpenRouterRequestAborted`).
        """
        mods = [m.strip() for m in modalities if isinstance(m, str) and m.strip()]
        if not mods:
            raise OpenRouterConfigError("Faltan modalities para generar imagen en OpenRouter.")
        use_images_api = "text" not in {m.casefold() for m in mods}
        if use_images_api:
            path = "/images"
            body: dict[str, Any] = {
                "model": model,
                "prompt": prompt,
            }
            body.update(image_options or {"output_format": "png"})
        else:
            path = "/chat/completions"
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "modalities": mods,
            }
        client = self._client()
        try:
            if should_cancel is None:
                response = client.post(path, content=json.dumps(body))
            else:
                response = self._post_cancelable(client, path, body, should_cancel)
            self._raise_for_status(response)
            payload = response.json()
        finally:
            client.close()
        if use_images_api:
            return _extract_images_api_bytes(payload)
        return _extract_chat_image_bytes(payload)

    @staticmethod
    def _post_cancelable(
        client: httpx.Client,
        path: str,
        body: dict[str, Any],
        should_cancel: Callable[[], bool],
    ) -> httpx.Response:
        if should_cancel():
            raise OpenRouterRequestAborted("Generación de imagen cancelada antes de enviar.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                client.post,
                path,
                content=json.dumps(body),
            )
            while True:
                try:
                    return future.result(timeout=0.2)
                except concurrent.futures.TimeoutError:
                    if should_cancel():
                        client.close()
                        try:
                            future.result(timeout=1.0)
                        except Exception:
                            pass
                        raise OpenRouterRequestAborted("Generación de imagen cancelada.")
                    time.sleep(0)


def _extract_text_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OpenRouterApiError("Respuesta OpenRouter sin choices.")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise OpenRouterApiError("Respuesta OpenRouter sin message.")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        if parts:
            return "\n".join(parts)
    raise OpenRouterApiError("Respuesta OpenRouter sin texto usable.")


def _extract_images_api_bytes(payload: dict[str, Any]) -> bytes:
    """Parsea la respuesta de ``POST /images`` (``data[].b64_json`` | ``url``)."""
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise OpenRouterApiError("Respuesta OpenRouter /images sin data.")
    first = data[0]
    if not isinstance(first, dict):
        raise OpenRouterApiError("Respuesta OpenRouter /images con item inválido.")
    b64 = first.get("b64_json")
    if isinstance(b64, str) and b64.strip():
        return _decode_image_ref(b64)
    url = first.get("url")
    if isinstance(url, str) and url.strip():
        return _decode_image_ref(url)
    raise OpenRouterApiError("Respuesta OpenRouter /images sin imagen decodificable.")


def _extract_chat_image_bytes(payload: dict[str, Any]) -> bytes:
    """Parsea imagen embebida en ``POST /chat/completions``."""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OpenRouterApiError("Respuesta OpenRouter sin choices (imagen).")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise OpenRouterApiError("Respuesta OpenRouter sin message (imagen).")

    images = message.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict):
            url = first.get("image_url") or first.get("url")
            if isinstance(url, dict):
                url = url.get("url")
            if isinstance(url, str):
                return _decode_image_ref(url)

    content = message.get("content")
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") in ("image_url", "image"):
                image_url = part.get("image_url") or part.get("url")
                if isinstance(image_url, dict):
                    image_url = image_url.get("url")
                if isinstance(image_url, str):
                    return _decode_image_ref(image_url)

    raise OpenRouterApiError("Respuesta OpenRouter sin imagen decodificable.")


def _decode_image_ref(ref: str) -> bytes:
    match = _DATA_URL_RE.match(ref.strip())
    if match:
        return base64.b64decode(match.group(2))
    if ref.startswith("http://") or ref.startswith("https://"):
        with httpx.Client(timeout=_DEFAULT_TIMEOUT) as client:
            response = client.get(ref)
            response.raise_for_status()
            return response.content
    # Asumir base64 crudo
    try:
        return base64.b64decode(ref)
    except Exception as exc:
        raise OpenRouterApiError("No se pudo decodificar la imagen de OpenRouter.") from exc


def build_client_from_runtime(
    *,
    transport: httpx.BaseTransport | None = None,
) -> OpenRouterClient:
    """Construye un client a partir del runtime config actual."""
    from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime

    snap = get_openrouter_runtime().snapshot()
    if not snap.api_key:
        raise OpenRouterConfigError("OpenRouter no está configurado (falta API key).")
    return OpenRouterClient(snap.api_key, base_url=snap.base_url, transport=transport)
