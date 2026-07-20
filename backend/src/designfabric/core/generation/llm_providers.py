"""Providers primitivos de generación de texto (Strategy + Factory).

Sin lógica de negocio de stickers/conceptos: solo completación y lifecycle
del motor LLM. El dominio (`prompt_generator`) se construye encima.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from designfabric.core.progress import (
    NullProgressReporter,
    Phase,
    ProgressReporter,
    emit_warning,
)

LlmProviderName = Literal["ollama", "openrouter", "test"]

LLM_TEST_FIXED_TEXT = "a curious fox reading a map under a lantern"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Mensaje genérico system/user/assistant, independiente de LangChain."""

    role: Literal["system", "user", "assistant"]
    content: str


class LlmProvider(ABC):
    """Motor de texto: una completación a partir de mensajes."""

    @abstractmethod
    def generate_text(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str,
        host: str | None = None,
    ) -> str:
        """Devuelve el texto crudo de la completación."""

    def release(
        self,
        *,
        model: str,
        host: str | None = None,
        reporter: ProgressReporter = NullProgressReporter(),
    ) -> None:
        """Libera recursos del motor (no-op por defecto)."""


class LlmTestProvider(LlmProvider):
    """Stub: ignora mensajes/modelo y siempre devuelve el mismo texto."""

    def generate_text(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str,
        host: str | None = None,
    ) -> str:
        return LLM_TEST_FIXED_TEXT


class OllamaLlmProvider(LlmProvider):
    """Wrapper fino sobre ChatOllama + cliente ollama (imports lazy)."""

    def generate_text(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str,
        host: str | None = None,
    ) -> str:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        from langchain_ollama import ChatOllama

        llm = ChatOllama(model=model, temperature=0.9, base_url=host)
        lc_messages = []
        for message in messages:
            if message.role == "system":
                lc_messages.append(SystemMessage(content=message.content))
            elif message.role == "user":
                lc_messages.append(HumanMessage(content=message.content))
            else:
                lc_messages.append(AIMessage(content=message.content))
        response = llm.invoke(lc_messages)
        content = response.content
        return content if isinstance(content, str) else str(content)

    def release(
        self,
        *,
        model: str,
        host: str | None = None,
        reporter: ProgressReporter = NullProgressReporter(),
    ) -> None:
        import ollama as ollama_client

        client = ollama_client.Client(host=host) if host else ollama_client
        try:
            client.generate(model=model, prompt="", keep_alive=0)
        except Exception as exc:
            emit_warning(
                reporter,
                Phase.PROMPT_GENERATION,
                f"No se pudo descargar el modelo de Ollama limpiamente: {exc}",
            )


class OpenRouterLlmProvider(LlmProvider):
    """Completación de texto vía OpenRouter (cliente HTTP)."""

    def generate_text(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str,
        host: str | None = None,
    ) -> str:
        from designfabric.core.generation.openrouter.client import build_client_from_runtime
        from designfabric.core.generation.openrouter.errors import OpenRouterConfigError

        if not model or not model.strip():
            raise OpenRouterConfigError("Falta el modelo de texto de OpenRouter.")
        client = build_client_from_runtime()
        return client.chat_completion(messages, model=model)


_PROVIDERS: dict[LlmProviderName, type[LlmProvider]] = {
    "ollama": OllamaLlmProvider,
    "openrouter": OpenRouterLlmProvider,
    "test": LlmTestProvider,
}


def create_llm_provider(name: LlmProviderName) -> LlmProvider:
    """Crea un provider LLM por nombre."""
    try:
        provider_cls = _PROVIDERS[name]
    except KeyError as exc:
        raise ValueError(
            f"Provider LLM desconocido '{name}'. Opciones: {sorted(_PROVIDERS)}"
        ) from exc
    return provider_cls()


def list_llm_provider_names() -> tuple[LlmProviderName, ...]:
    return tuple(_PROVIDERS.keys())
