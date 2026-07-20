"""Tests de OpenRouterImageProvider con client mock."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from designfabric.core.generation.image_providers import OpenRouterImageProvider, create_image_provider
from designfabric.core.generation.openrouter.errors import OpenRouterConfigError
from designfabric.core.generation.openrouter.models import OpenRouterModel
from designfabric.core.generation.openrouter.models_cache import get_models_cache
from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime
from designfabric.core.progress import ProgressEventType

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(autouse=True)
def _reset_runtime():
    get_openrouter_runtime().reset_for_tests()
    get_models_cache().invalidate()
    yield
    get_openrouter_runtime().reset_for_tests()
    get_models_cache().invalidate()


def test_factory_registers_openrouter_image():
    assert isinstance(create_image_provider("openrouter"), OpenRouterImageProvider)


def test_generate_images_uses_configured_modalities(tmp_path, mocker, fake_reporter):
    get_openrouter_runtime().update(
        api_key="sk-test",
        image_model_id="google/gemini-image",
        image_model_output_modalities=["image"],
    )
    fake = MagicMock()
    fake.generate_image.return_value = _PNG
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
    fake.generate_image.assert_called_once_with(
        "a fox",
        model="google/gemini-image",
        modalities=["image"],
    )
    fake.list_models.assert_not_called()
    assert fake_reporter.events[0].type is ProgressEventType.STARTED
    assert fake_reporter.events[-1].type is ProgressEventType.COMPLETED


def test_generate_images_resolves_modalities_via_cache(tmp_path, mocker, fake_reporter):
    get_openrouter_runtime().update(api_key="sk-test", image_model_id="black-forest-labs/flux")
    fake = MagicMock()
    fake.generate_image.return_value = _PNG
    fake.list_models.return_value = [
        OpenRouterModel(
            id="black-forest-labs/flux",
            name="FLUX",
            output_modalities=("image",),
        )
    ]
    mocker.patch(
        "designfabric.core.generation.openrouter.client.build_client_from_runtime",
        return_value=fake,
    )

    results = OpenRouterImageProvider().generate_images(
        ["a fox"],
        output_dir=str(tmp_path),
        reporter=fake_reporter,
    )
    assert results[0].success
    fake.list_models.assert_called_once_with("image")
    fake.generate_image.assert_called_once_with(
        "a fox",
        model="black-forest-labs/flux",
        modalities=["image"],
    )


def test_generate_images_image_plus_text_modalities(tmp_path, mocker):
    get_openrouter_runtime().update(
        api_key="sk-test",
        image_model_id="google/gemini-image",
        image_model_output_modalities=["image", "text"],
    )
    fake = MagicMock()
    fake.generate_image.return_value = _PNG
    mocker.patch(
        "designfabric.core.generation.openrouter.client.build_client_from_runtime",
        return_value=fake,
    )

    OpenRouterImageProvider().generate_images(["x"], output_dir=str(tmp_path))
    fake.generate_image.assert_called_once_with(
        "x",
        model="google/gemini-image",
        modalities=["image", "text"],
    )


def test_generate_images_requires_model(tmp_path):
    get_openrouter_runtime().update(api_key="sk-test")
    with pytest.raises(OpenRouterConfigError):
        OpenRouterImageProvider().generate_images(["x"], output_dir=str(tmp_path))
