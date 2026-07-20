"""Constantes de generación IA sin dependencias pesadas (torch/langchain/ollama).

Separado de `prompt_generator.py` a propósito: `api/schemas.py` necesita
`OLLAMA_MODEL_DEFAULT` para el valor default de un campo pydantic, pero
`api/schemas.py` es un módulo transitivamente importado por TODO el backend
(vía `jobs/ws_reporter.py`), incluidas las tabs de ClearCut que no requieren
el extra `local-ai`. Si este valor viviera en `prompt_generator.py` (que sí
importa `ollama`/`langchain_ollama` a nivel de módulo), todo el backend
fallaría al arrancar sin ese extra instalado — justamente lo que la
degradación con gracia de la Fase 2 busca evitar.
"""

from __future__ import annotations

OLLAMA_MODEL_DEFAULT = "gemma3:4b"
