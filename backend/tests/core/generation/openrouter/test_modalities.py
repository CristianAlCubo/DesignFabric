"""Tests de la policy resolve_image_request_modalities."""

from __future__ import annotations

import pytest

from designfabric.core.generation.openrouter.errors import OpenRouterConfigError
from designfabric.core.generation.openrouter.modalities import resolve_image_request_modalities


def test_image_only():
    assert resolve_image_request_modalities(["image"]) == ["image"]


def test_image_and_text():
    assert resolve_image_request_modalities(["image", "text"]) == ["image", "text"]
    assert resolve_image_request_modalities(["text", "image"]) == ["image", "text"]


def test_image_with_other_modalities_keeps_image_and_optional_text():
    assert resolve_image_request_modalities(["image", "audio"]) == ["image"]
    assert resolve_image_request_modalities(["audio", "image", "text"]) == ["image", "text"]


def test_missing_image_raises():
    with pytest.raises(OpenRouterConfigError, match="image"):
        resolve_image_request_modalities(["text"])
    with pytest.raises(OpenRouterConfigError):
        resolve_image_request_modalities([])
    with pytest.raises(OpenRouterConfigError):
        resolve_image_request_modalities(None)
