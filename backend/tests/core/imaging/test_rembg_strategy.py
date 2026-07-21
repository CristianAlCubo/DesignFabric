"""Tests de la estrategia rembg_illustration (rembg.remove mockeado)."""

from __future__ import annotations

import numpy as np
import pytest

from designfabric.core.imaging.rembg_strategy import RembgIllustrationStrategy


def test_rembg_strategy_converts_channels_and_composes_bgra(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    def fake_new_session(name: str):
        calls["session_name"] = name
        return "fake-session"

    def fake_remove(rgb: np.ndarray, *, session, alpha_matting: bool) -> np.ndarray:
        calls["session_used"] = session
        calls["alpha_matting"] = alpha_matting
        h, w = rgb.shape[:2]
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        alpha = np.full((h, w), 200, dtype=np.uint8)
        return np.dstack([r, g, b, alpha])

    monkeypatch.setattr("rembg.new_session", fake_new_session)
    monkeypatch.setattr("rembg.remove", fake_remove)

    strategy = RembgIllustrationStrategy()
    image = np.zeros((10, 12, 3), dtype=np.uint8)
    image[:, :, 0] = 10  # B
    image[:, :, 1] = 20  # G
    image[:, :, 2] = 30  # R

    result = strategy.remove_background(image)

    assert calls["session_name"] == "isnet-anime"
    assert calls["alpha_matting"] is False
    assert result.shape == (10, 12, 4)
    assert result.dtype == np.uint8
    # BGR debe conservarse (no invertirse) tras el roundtrip RGB->BGRA.
    assert result[0, 0, 0] == 10
    assert result[0, 0, 1] == 20
    assert result[0, 0, 2] == 30
    assert result[0, 0, 3] == 200


def test_rembg_strategy_reuses_session_across_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    session_calls = []

    def fake_new_session(name: str):
        session_calls.append(name)
        return object()

    def fake_remove(rgb: np.ndarray, *, session, alpha_matting: bool) -> np.ndarray:
        h, w = rgb.shape[:2]
        return np.dstack([rgb, np.full((h, w), 255, dtype=np.uint8)])

    monkeypatch.setattr("rembg.new_session", fake_new_session)
    monkeypatch.setattr("rembg.remove", fake_remove)

    strategy = RembgIllustrationStrategy()
    image = np.zeros((5, 5, 3), dtype=np.uint8)
    strategy.remove_background(image)
    strategy.remove_background(image)

    assert len(session_calls) == 1
