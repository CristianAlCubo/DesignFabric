"""Fixtures propias de los tests de API.

El pipeline de generación IA (DesignFabric: Ollama + Flux) se mockea para no
requerir GPU/Ollama reales — mismo patrón que usaba
`DesignFabric/backend/tests/api/conftest.py`, ahora apuntando a los routers
donde vive cada `run_batch`/`run_single_image` importado (Fase 4: cada
feature tiene su propio router/handler en vez de un `worker.py` monolítico).

El pipeline de ClearCut (remove-background/scale/batch) NO se mockea: corre
sobre CPU real con imágenes sintéticas pequeñas, así que es rápido sin
mocks (ver `test_remove_background.py`, `test_scale.py`, `test_clearcut_batch.py`).

Las fixtures de imágenes sintéticas se duplican mínimamente acá (en vez de
importarlas de `tests/core/imaging/conftest.py`) porque ese conftest vive
fuera del scope de directorio de `tests/api/` y pytest no las compartiría
automáticamente entre paquetes de test distintos sin un import explícito;
duplicar dos funciones pequeñas es más simple que reestructurar el árbol de
tests para compartir un conftest común.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np
import pytest
from starlette.testclient import TestClient

from designfabricv2.api.app import create_app
from designfabricv2.api.registry import LOCAL_AI_AVAILABLE

if LOCAL_AI_AVAILABLE:
    # Estos módulos importan `torch`/`diffusers`/`langchain` transitivamente:
    # sin el extra `local-ai` instalado no se pueden importar, así que el mock
    # del pipeline de generación IA (más abajo, en `client`) también queda
    # condicionado a `LOCAL_AI_AVAILABLE`.
    from designfabricv2.core.generation.pipeline import BatchResult
    from designfabricv2.core.generation.sticker_generator import StickerResult


@pytest.fixture(autouse=True)
def _skip_model_downloads_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita descargas de red en la suite de API salvo tests que lo anulen."""
    monkeypatch.setenv("CLEARCUT_SKIP_MODEL_DOWNLOAD", "1")


@pytest.fixture
def client(tmp_path, monkeypatch, mocker) -> Iterator[TestClient]:
    """`TestClient` con el pipeline de generación IA mockeado (respuestas instantáneas)."""
    output_dir = str(tmp_path / "output")
    monkeypatch.setenv("DESIGNFABRIC_OUTPUT_DIR", output_dir)

    if LOCAL_AI_AVAILABLE:
        fake_filename = f"{output_dir}/fake/sticker_1_x.png"
        fast_batch_result = BatchResult(
            prompts=["a fake concept, sticker style"],
            results=[StickerResult(prompt="a fake concept, sticker style", filename=fake_filename, success=True)],
        )
        fast_single_result = StickerResult(prompt="a fake prompt", filename=fake_filename, success=True)

        mocker.patch("designfabricv2.api.routers.batch_generation.run_batch", return_value=fast_batch_result)
        mocker.patch("designfabricv2.api.routers.single_image.run_single_image", return_value=fast_single_result)

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def wait_until(predicate, timeout: float = 5.0, interval: float = 0.02) -> bool:
    """Espera activa a que `predicate()` sea verdadero, con timeout — evita sleeps fijos en los tests."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def make_synthetic_white_bg_image(path: Path) -> Path:
    """Genera un PNG pequeño (120x120): fondo blanco sólido y un cuadrado rojo centrado."""
    img = np.full((120, 120, 3), 255, dtype=np.uint8)
    img[30:90, 30:90] = (30, 30, 220)  # BGR rojo
    cv2.imwrite(str(path), img)
    return path


@pytest.fixture
def synthetic_white_bg_path(tmp_path: Path) -> Path:
    return make_synthetic_white_bg_image(tmp_path / "synthetic_white.png")
