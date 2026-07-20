"""Generación de conceptos de sujeto/escena vía Ollama (LangChain ChatOllama).

Módulo de dominio puro: no imprime nada directamente, reporta su progreso a
través de un `ProgressReporter` para que CLI y API puedan renderizarlo cada
uno a su manera.
"""

from __future__ import annotations

import ollama as ollama_client
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from designfabric.core.generation.constants import OLLAMA_MODEL_DEFAULT
from designfabric.core.progress import (
    Phase,
    ProgressReporter,
    NullProgressReporter,
    emit_phase_started,
    emit_phase_progress,
    emit_phase_completed,
    emit_phase_failed,
    emit_warning,
)

STYLE_SUFFIX = (
    "vector graphic style, sticker asset for t-shirt design, "
    "bold clean outlines, flat solid colors, high contrast, "
    "thick white border outline, isolated on a solid white background, "
    "print-ready, professional vector art, sharp edges, no gradients."
)

SYSTEM_PROMPT = SystemMessage(
    content=(
        "Eres un director creativo especializado en diseño de stickers para ropa. "
        "Propones sujetos y escenas originales, vívidas y con detalle realista "
        "(personajes, animales, objetos o criaturas en una acción o escena concreta), "
        "pensados para convertirse luego en arte vectorial tipo sticker. "
        "No menciones estilo visual, técnica de dibujo, colores ni acabado: describe solo el sujeto y la escena."
    )
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
    model: str = OLLAMA_MODEL_DEFAULT,
    reporter: ProgressReporter = NullProgressReporter(),
    ollama_host: str | None = None,
) -> list[str]:
    """Usa Ollama (modelo parametrizable) vía LangChain para crear sujetos/escenas realistas y variados.

    Se hace una llamada por concepto (en vez de pedir todos de una vez) para
    evitar respuestas largas que el modelo trunca o formatea mal.

    Devuelve la lista de prompts finales (concepto + `STYLE_SUFFIX`).
    """
    emit_phase_started(reporter, Phase.PROMPT_GENERATION, total=num_images)
    try:
        llm = ChatOllama(model=model, temperature=0.9, base_url=ollama_host)

        concepts: list[str] = []
        for i in range(num_images):
            # Cada llamada es independiente: no se pasan los conceptos ya
            # generados para evitar que el contexto/memoria crezca sin límite.
            human = HumanMessage(
                content=(
                    "Genera un único concepto de sujeto y escena original. Responde "
                    "únicamente con la descripción en inglés, en una sola línea, sin "
                    "comillas ni texto adicional. "
                    "Ejemplo: a grumpy owl perched on a stack of old books, wearing tiny reading glasses"
                )
            )

            concept = None
            for intento in range(1, 3):
                try:
                    response = llm.invoke([SYSTEM_PROMPT, human])
                    concept = _clean_concept(response.content)
                    break
                except Exception as e:
                    emit_warning(
                        reporter, Phase.PROMPT_GENERATION, f"Intento {intento} fallido generando un concepto: {e}"
                    )

            if concept is None:
                emit_warning(reporter, Phase.PROMPT_GENERATION, "Se descarta este concepto tras agotar los reintentos.")
                emit_phase_progress(reporter, Phase.PROMPT_GENERATION, i + 1, num_images)
                continue

            concepts.append(concept)
            emit_phase_progress(reporter, Phase.PROMPT_GENERATION, i + 1, num_images, detail=concept[:50])

        if not concepts:
            raise RuntimeError("Ollama no generó ningún concepto válido")
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
    """Libera la VRAM ocupada por Ollama antes de cargar Flux."""
    client = ollama_client.Client(host=ollama_host) if ollama_host else ollama_client
    try:
        client.generate(model=model, prompt="", keep_alive=0)
    except Exception as e:
        emit_warning(reporter, Phase.PROMPT_GENERATION, f"No se pudo descargar el modelo de Ollama limpiamente: {e}")
