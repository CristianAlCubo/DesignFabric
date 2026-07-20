"""Dominio de conceptos de sticker: orquesta un LlmProvider primitivo.

Contiene la lógica de negocio (SYSTEM_PROMPT, STYLE_SUFFIX, retries, limpieza).
No importa SDKs de Ollama/LangChain directamente.
"""

from __future__ import annotations

from designfabric.core.generation.constants import OLLAMA_MODEL_DEFAULT
from designfabric.core.generation.llm_providers import ChatMessage, LlmProvider, create_llm_provider
from designfabric.core.progress import (
    NullProgressReporter,
    Phase,
    ProgressReporter,
    emit_phase_completed,
    emit_phase_failed,
    emit_phase_progress,
    emit_phase_started,
    emit_warning,
)

STYLE_SUFFIX = (
    "vector graphic style, sticker asset for t-shirt design, "
    "bold clean outlines, flat solid colors, high contrast, "
    "thick white border outline, isolated on a solid white background, "
    "print-ready, professional vector art, sharp edges, no gradients."
)

SYSTEM_PROMPT_TEXT = (
    "Eres un director creativo especializado en diseño de stickers para ropa. "
    "Propones sujetos y escenas originales, vívidas y con detalle realista "
    "(personajes, animales, objetos o criaturas en una acción o escena concreta), "
    "pensados para convertirse luego en arte vectorial tipo sticker. "
    "No menciones estilo visual, técnica de dibujo, colores ni acabado: describe solo el sujeto y la escena."
)

CONCEPT_USER_PROMPT = (
    "Genera un único concepto de sujeto y escena original. Responde "
    "únicamente con la descripción en inglés, en una sola línea, sin "
    "comillas ni texto adicional. "
    "Ejemplo: a grumpy owl perched on a stack of old books, wearing tiny reading glasses"
)


def _clean_concept(text: str) -> str:
    """Normaliza la respuesta cruda del LLM a una sola línea sin comillas."""
    concept = text.strip().strip("`").strip()
    if concept.startswith('"') and concept.endswith('"'):
        concept = concept[1:-1]
    return concept.splitlines()[0].strip()


def apply_style_suffix(concept: str) -> str:
    """Combina un concepto/prompt libre con el sufijo de estilo sticker fijo."""
    return f"{concept}, {STYLE_SUFFIX}"


def generate_concepts(
    num_images: int,
    llm: LlmProvider | None = None,
    model: str = OLLAMA_MODEL_DEFAULT,
    reporter: ProgressReporter = NullProgressReporter(),
    ollama_host: str | None = None,
) -> list[str]:
    """Genera sujetos/escenas vía el LlmProvider inyectado (Ollama por defecto).

    Se hace una llamada por concepto para evitar respuestas truncadas.
    Devuelve la lista de prompts finales (concepto + `STYLE_SUFFIX`).
    """
    provider = llm if llm is not None else create_llm_provider("ollama")
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT_TEXT),
        ChatMessage(role="user", content=CONCEPT_USER_PROMPT),
    ]

    emit_phase_started(reporter, Phase.PROMPT_GENERATION, total=num_images)
    try:
        concepts: list[str] = []
        for i in range(num_images):
            concept = None
            for intento in range(1, 3):
                try:
                    raw = provider.generate_text(messages, model=model, host=ollama_host)
                    concept = _clean_concept(raw)
                    break
                except Exception as e:
                    emit_warning(
                        reporter,
                        Phase.PROMPT_GENERATION,
                        f"Intento {intento} fallido generando un concepto: {e}",
                    )

            if concept is None:
                emit_warning(reporter, Phase.PROMPT_GENERATION, "Se descarta este concepto tras agotar los reintentos.")
                emit_phase_progress(reporter, Phase.PROMPT_GENERATION, i + 1, num_images)
                continue

            concepts.append(concept)
            emit_phase_progress(reporter, Phase.PROMPT_GENERATION, i + 1, num_images, detail=concept[:50])

        if not concepts:
            raise RuntimeError("No se generó ningún concepto válido")
    except Exception as e:
        emit_phase_failed(reporter, Phase.PROMPT_GENERATION, str(e))
        raise
    else:
        emit_phase_completed(reporter, Phase.PROMPT_GENERATION)

    return [apply_style_suffix(concept) for concept in concepts]


def unload_ollama(
    model: str = OLLAMA_MODEL_DEFAULT,
    reporter: ProgressReporter = NullProgressReporter(),
    ollama_host: str | None = None,
) -> None:
    """Compat: libera VRAM vía el provider Ollama."""
    create_llm_provider("ollama").release(model=model, host=ollama_host, reporter=reporter)
