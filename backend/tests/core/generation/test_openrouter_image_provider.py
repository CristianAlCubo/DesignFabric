"""Tests de OpenRouterImageProvider con client mock."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from designfabric.core.generation.image_providers import OpenRouterImageProvider, create_image_provider
from designfabric.core.generation.openrouter.errors import OpenRouterConfigError
from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime
from designfabric.core.progress import ProgressEventType


@pytest.fixture(autouse=True)
def _reset_runtime():
    get_openrouter_runtime().reset_for_tests()
    yield
    get_openrouter_runtime().reset_for_tests()


def test_factory_registers_openrouter_image():
    assert isinstance(create_image_provider("openrouter"), OpenRouterImageProvider)


def test_generate_images_writes_png(tmp_path, mocker, fake_reporter):
    get_openrouter_runtime().update(api_key="sk-test", image_model_id="google/gemini-image")
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    fake = MagicMock()
    fake.generate_image.return_value = png
    mocker.patch(
        "designfabric.core.generation.openrouter.client.build_client_from_runtime",
        return_value=fake,
    )

    results = OpenRouterImageProvider().generate_images(
        ["a fox"],
        output_dir=str(tmp_path),
        reporter=fake_reporter,
    )
    assert len(results) == 1
    assert results[0].success
    assert results[0].filename and Path(results[0].filename).is_file()
    assert fake_reporter.events[0].type is ProgressEventType.STARTED
    assert fake_reporter.events[-1].type is ProgressEventType.COMPLETED


def test_generate_images_requires_model(tmp_path):
    get_openrouter_runtime().update(api_key="sk-test")
    with pytest.raises(OpenRouterConfigError):
        OpenRouterImageProvider().generate_images(["x"], output_dir=str(tmp_path))
