"""Tests de verificación y descarga de modelos."""

from __future__ import annotations

from pathlib import Path

import pytest

from designfabricv2.core.imaging.model_assets import ensure_models
from designfabricv2.core.imaging.upscale_config import UpscaleConfig


def test_ensure_models_downloads_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLEARCUT_SKIP_MODEL_DOWNLOAD", raising=False)
    config = UpscaleConfig(models_dir=str(tmp_path / "models"))
    downloaded: list[str] = []

    def fake_download(url: str, dest: Path) -> None:
        downloaded.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"fake-model")

    report = ensure_models(config=config, project_root=tmp_path, downloader=fake_download)
    assert len(downloaded) == 1
    assert all(item.present and item.downloaded for item in report.models)
    assert (tmp_path / "models" / config.realesrgan_model).is_file()
    assert report.ready_realesrgan
    assert report.ready_span is False


def test_ensure_models_skips_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLEARCUT_SKIP_MODEL_DOWNLOAD", raising=False)
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    config = UpscaleConfig(models_dir=str(models_dir))
    (models_dir / config.realesrgan_model).write_bytes(b"existing")

    calls = 0

    def fake_download(_url: str, _dest: Path) -> None:
        nonlocal calls
        calls += 1

    report = ensure_models(config=config, project_root=tmp_path, downloader=fake_download)
    assert calls == 0
    assert all(item.present and not item.downloaded for item in report.models)


def test_ensure_models_realesrgan_key_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLEARCUT_SKIP_MODEL_DOWNLOAD", raising=False)
    config = UpscaleConfig(models_dir=str(tmp_path / "models"))
    urls: list[str] = []

    def fake_download(url: str, dest: Path) -> None:
        urls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"x")

    report = ensure_models(
        config=config,
        project_root=tmp_path,
        keys={"realesrgan"},
        downloader=fake_download,
    )
    assert len(urls) == 1
    assert len(report.models) == 1
    assert report.models[0].key == "realesrgan"


def test_skip_env_disables_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLEARCUT_SKIP_MODEL_DOWNLOAD", "1")
    config = UpscaleConfig(models_dir=str(tmp_path / "models"))
    calls = 0

    def fake_download(_url: str, _dest: Path) -> None:
        nonlocal calls
        calls += 1

    report = ensure_models(config=config, project_root=tmp_path, downloader=fake_download)
    assert calls == 0
    assert all(not item.present for item in report.models)
