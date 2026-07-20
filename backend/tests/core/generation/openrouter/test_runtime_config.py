"""Tests del runtime config OpenRouter."""

from __future__ import annotations

from designfabric.core.config import Settings
from designfabric.core.generation.openrouter.runtime_config import OpenRouterRuntimeConfig


def test_seed_from_settings_once():
    cfg = OpenRouterRuntimeConfig()
    settings = Settings(
        openrouter_api_key="sk-test",
        openrouter_text_model="text/model",
        openrouter_image_model="image/model",
    )
    cfg.seed_from_settings(settings)
    snap = cfg.snapshot()
    assert snap.api_key == "sk-test"
    assert snap.text_model_id == "text/model"
    assert snap.image_model_id == "image/model"
    assert snap.configured
    assert snap.llm_ready
    assert snap.image_ready

    # Segundo seed no pisa overrides de update
    cfg.update(api_key="sk-other")
    cfg.seed_from_settings(
        Settings(openrouter_api_key="sk-from-env", openrouter_text_model="ignored")
    )
    assert cfg.snapshot().api_key == "sk-other"


def test_update_and_clear():
    cfg = OpenRouterRuntimeConfig()
    cfg.update(
        api_key="  sk-a  ",
        text_model_id="m1",
        image_model_id="m2",
        image_model_output_modalities=["image"],
    )
    snap = cfg.snapshot()
    assert snap.api_key == "sk-a"
    assert snap.llm_ready and snap.image_ready
    assert snap.image_model_output_modalities == ("image",)

    cfg.update(clear_api_key=True, clear_text_model=True, clear_image_model=True)
    snap = cfg.snapshot()
    assert not snap.configured
    assert not snap.llm_ready
    assert not snap.image_ready
    assert snap.image_model_output_modalities is None


def test_image_modalities_unset_vs_null():
    cfg = OpenRouterRuntimeConfig()
    cfg.update(image_model_id="m", image_model_output_modalities=["image", "text"])
    cfg.update(api_key="sk")
    assert cfg.snapshot().image_model_output_modalities == ("image", "text")
    cfg.update(image_model_output_modalities=None)
    assert cfg.snapshot().image_model_output_modalities is None


def test_llm_ready_requires_key_and_model():
    cfg = OpenRouterRuntimeConfig()
    cfg.update(api_key="sk")
    assert not cfg.snapshot().llm_ready
    cfg.update(text_model_id="x")
    assert cfg.snapshot().llm_ready
