"""Tests de resolve_image_request_options (capabilities → body extras)."""

from __future__ import annotations

from designfabric.core.generation.openrouter.image_options import (
    resolve_image_request_options,
    supports_transparent_background,
)

_TRANSPARENT_PARAMS = {
    "background": {"type": "enum", "values": ["auto", "transparent", "opaque"]},
    "output_format": {"type": "enum", "values": ["png", "jpeg", "webp"]},
}


def test_no_params_defaults_to_png_without_background():
    assert resolve_image_request_options(None) == {"output_format": "png"}
    assert resolve_image_request_options({}) == {"output_format": "png"}


def test_transparent_when_declared_and_preferred():
    assert resolve_image_request_options(_TRANSPARENT_PARAMS) == {
        "output_format": "png",
        "background": "transparent",
    }
    assert resolve_image_request_options(_TRANSPARENT_PARAMS, prefer_transparent=True) == {
        "output_format": "png",
        "background": "transparent",
    }


def test_no_transparent_when_user_disables():
    assert resolve_image_request_options(_TRANSPARENT_PARAMS, prefer_transparent=False) == {
        "output_format": "png"
    }


def test_no_transparent_when_not_declared():
    params = {
        "output_format": {"type": "enum", "values": ["png", "jpeg"]},
        "quality": {"type": "enum", "values": ["low", "medium", "high"]},
    }
    assert resolve_image_request_options(params) == {"output_format": "png"}
    assert supports_transparent_background(params) is False


def test_webp_when_png_unavailable_with_transparent():
    params = {
        "background": {"type": "enum", "values": ["transparent"]},
        "output_format": {"type": "enum", "values": ["webp", "jpeg"]},
    }
    assert resolve_image_request_options(params) == {
        "output_format": "webp",
        "background": "transparent",
    }


def test_background_without_output_format_still_uses_png():
    params = {
        "background": {"type": "enum", "values": ["transparent", "opaque"]},
    }
    assert supports_transparent_background(params) is True
    assert resolve_image_request_options(params) == {
        "output_format": "png",
        "background": "transparent",
    }
