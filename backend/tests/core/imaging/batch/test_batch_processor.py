"""Tests del orquestador batch."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from designfabric.core.imaging.background_remover import RemovalConfig
from designfabric.core.imaging.batch.input_sources import FilesInputSource, FolderInputSource
from designfabric.core.imaging.batch.output_targets import DirectoryOutputTarget
from designfabric.core.imaging.batch.processor import BatchProcessor, emit_item_line, run_batch
from designfabric.core.imaging.batch.types import ITEM_PREFIX, BatchConfig, BatchItemResult
from designfabric.core.imaging.background_removal_strategies import BackgroundRemovalStrategy
from designfabric.core.imaging.upscale_pipeline import ScaleOutcome
from designfabric.core.imaging.upscale_strategies import UpscaleResult
from designfabric.core.progress import Phase, ProgressEvent, ProgressEventType


class FakeProgressReporter:
    """Reporter de prueba: acumula los eventos recibidos en una lista."""

    def __init__(self) -> None:
        self.events: list[ProgressEvent] = []

    def emit(self, event: ProgressEvent) -> None:
        self.events.append(event)


def _fake_outcome(output_path: Path, warning: str | None = None) -> ScaleOutcome:
    return ScaleOutcome(
        output_path=output_path,
        result=UpscaleResult(
            png_bytes=b"png",
            backend="fake",
            device="cpu",
            scale_factor=2.0,
            source_size=(10, 10),
            final_size=(20, 20),
            inference_ms=0.0,
            warning=warning,
        ),
    )


def test_processor_success_and_factor_dimensions(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(b"1")
    b.write_bytes(b"2")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    seen_exports: list[tuple[int | None, int | None]] = []

    def remove_fn(
        input_path: Path,
        output_path: Path,
        _strategy: BackgroundRemovalStrategy,
        _config: RemovalConfig,
    ) -> np.ndarray:
        output_path.write_bytes(b"cut")
        return np.zeros((100, 200, 4), dtype=np.uint8)

    def scale_fn(
        input_path: Path,
        output_path: Path,
        **kwargs: Any,
    ) -> ScaleOutcome:
        seen_exports.append((kwargs.get("width"), kwargs.get("height")))
        output_path.write_bytes(b"scaled")
        return _fake_outcome(output_path)

    processor = BatchProcessor(remove_fn=remove_fn, scale_fn=scale_fn)
    report = processor.run(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=2,
        ),
        FilesInputSource(paths=(a, b)),
        DirectoryOutputTarget(directory=out_dir),
    )

    assert report.total == 2
    assert report.succeeded == 2
    assert report.failed == 0
    assert seen_exports == [(400, 200), (400, 200)]
    assert (out_dir / "a.png").is_file()
    assert (out_dir / "b.png").is_file()


def test_processor_continues_after_failure(tmp_path: Path) -> None:
    good = tmp_path / "good.png"
    bad = tmp_path / "bad.png"
    good.write_bytes(b"1")
    bad.write_bytes(b"2")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def remove_fn(
        input_path: Path,
        output_path: Path,
        _strategy: BackgroundRemovalStrategy,
        _config: RemovalConfig,
    ) -> np.ndarray:
        if input_path.name == "bad.png":
            raise ValueError("archivo corrupto")
        output_path.write_bytes(b"cut")
        return np.zeros((50, 50, 4), dtype=np.uint8)

    def scale_fn(input_path: Path, output_path: Path, **_kwargs: Any) -> ScaleOutcome:
        output_path.write_bytes(b"scaled")
        return _fake_outcome(output_path)

    report = BatchProcessor(remove_fn=remove_fn, scale_fn=scale_fn).run(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=4,
        ),
        FilesInputSource(paths=(bad, good)),
        DirectoryOutputTarget(directory=out_dir),
    )

    assert report.succeeded == 1
    assert report.failed == 1
    assert report.items[0].status == "failed"
    assert report.items[0].error == "archivo corrupto"
    assert report.items[1].status == "succeeded"
    assert report.items[1].output_path == out_dir / "good.png"


def test_processor_skips_unsupported(tmp_path: Path) -> None:
    (tmp_path / "ok.png").write_bytes(b"1")
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def remove_fn(
        input_path: Path,
        output_path: Path,
        _strategy: BackgroundRemovalStrategy,
        _config: RemovalConfig,
    ) -> np.ndarray:
        output_path.write_bytes(b"cut")
        return np.zeros((10, 10, 4), dtype=np.uint8)

    def scale_fn(input_path: Path, output_path: Path, **_kwargs: Any) -> ScaleOutcome:
        output_path.write_bytes(b"scaled")
        return _fake_outcome(output_path, warning="aviso")

    report = BatchProcessor(remove_fn=remove_fn, scale_fn=scale_fn).run(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=2,
        ),
        FolderInputSource(directory=tmp_path),
        DirectoryOutputTarget(directory=out_dir),
    )

    assert report.total == 2
    assert report.skipped == 1
    assert report.succeeded == 1
    skipped = next(item for item in report.items if item.status == "skipped")
    assert "formato no soportado" in (skipped.error or "")
    succeeded = next(item for item in report.items if item.status == "succeeded")
    assert succeeded.warning == "aviso"


def test_processor_missing_file_fails(tmp_path: Path) -> None:
    missing = tmp_path / "gone.png"
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    report = BatchProcessor(
        remove_fn=lambda *_a, **_k: np.zeros((1, 1, 4), dtype=np.uint8),
        scale_fn=lambda *_a, **_k: _fake_outcome(out_dir / "x.png"),
    ).run(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=2,
        ),
        FilesInputSource(paths=(missing,)),
        DirectoryOutputTarget(directory=out_dir),
    )

    assert report.failed == 1
    assert "No existe" in (report.items[0].error or "")


def test_processor_progress_callback(tmp_path: Path) -> None:
    path = tmp_path / "a.png"
    path.write_bytes(b"1")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    events: list[tuple[int, int, Path]] = []

    def remove_fn(
        input_path: Path,
        output_path: Path,
        _strategy: BackgroundRemovalStrategy,
        _config: RemovalConfig,
    ) -> np.ndarray:
        output_path.write_bytes(b"cut")
        return np.zeros((8, 8, 4), dtype=np.uint8)

    def scale_fn(input_path: Path, output_path: Path, **_kwargs: Any) -> ScaleOutcome:
        output_path.write_bytes(b"scaled")
        return _fake_outcome(output_path)

    BatchProcessor(remove_fn=remove_fn, scale_fn=scale_fn).run(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=2,
        ),
        FilesInputSource(paths=(path,)),
        DirectoryOutputTarget(directory=out_dir),
        on_progress=lambda current, total, p: events.append((current, total, p)),
    )

    assert events == [(1, 1, path)]


def test_processor_cancels_between_items(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(b"1")
    b.write_bytes(b"2")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    calls = {"n": 0}
    items: list[str] = []

    def remove_fn(
        input_path: Path,
        output_path: Path,
        _strategy: BackgroundRemovalStrategy,
        _config: RemovalConfig,
    ) -> np.ndarray:
        calls["n"] += 1
        output_path.write_bytes(b"cut")
        return np.zeros((8, 8, 4), dtype=np.uint8)

    def scale_fn(input_path: Path, output_path: Path, **_kwargs: Any) -> ScaleOutcome:
        output_path.write_bytes(b"scaled")
        return _fake_outcome(output_path)

    report = BatchProcessor(remove_fn=remove_fn, scale_fn=scale_fn).run(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=2,
        ),
        FilesInputSource(paths=(a, b)),
        DirectoryOutputTarget(directory=out_dir),
        on_item=lambda item: items.append(item.input_path.name),
        should_cancel=lambda: calls["n"] >= 1,
    )

    assert report.cancelled is True
    assert report.succeeded == 1
    assert report.total == 1
    assert items == ["a.png"]
    assert calls["n"] == 1


def test_emit_item_line_writes_prefix(capsys: pytest.CaptureFixture[str]) -> None:
    item = BatchItemResult(
        input_path=Path("/tmp/a.png"),
        status="succeeded",
        output_path=Path("/tmp/out/a.png"),
    )
    emit_item_line(item)
    err = capsys.readouterr().err
    assert err.startswith(ITEM_PREFIX)
    payload = json.loads(err[len(ITEM_PREFIX) :])
    assert payload["status"] == "succeeded"
    assert payload["input"] == "/tmp/a.png"


def test_processor_reporter_emits_started_progress_completed(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(b"1")
    b.write_bytes(b"2")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def remove_fn(
        input_path: Path,
        output_path: Path,
        _strategy: BackgroundRemovalStrategy,
        _config: RemovalConfig,
    ) -> np.ndarray:
        output_path.write_bytes(b"cut")
        return np.zeros((8, 8, 4), dtype=np.uint8)

    calls = {"n": 0}

    def scale_fn(input_path: Path, output_path: Path, **_kwargs: Any) -> ScaleOutcome:
        output_path.write_bytes(b"scaled")
        calls["n"] += 1
        warning = "aviso" if calls["n"] == 1 else None
        return _fake_outcome(output_path, warning=warning)

    reporter = FakeProgressReporter()
    report = BatchProcessor(remove_fn=remove_fn, scale_fn=scale_fn).run(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=2,
        ),
        FilesInputSource(paths=(a, b)),
        DirectoryOutputTarget(directory=out_dir),
        reporter=reporter,
    )

    assert report.succeeded == 2

    started = [e for e in reporter.events if e.type == ProgressEventType.STARTED]
    progress = [e for e in reporter.events if e.type == ProgressEventType.PROGRESS]
    completed = [e for e in reporter.events if e.type == ProgressEventType.COMPLETED]
    warnings = [e for e in reporter.events if e.type == ProgressEventType.WARNING]

    assert len(started) == 1
    assert started[0].phase == Phase.CLEARCUT_BATCH
    assert started[0].total == 2

    assert len(progress) == 4
    assert progress[0].current == 0
    assert progress[0].total == 2
    assert progress[0].detail == str(a)
    assert progress[1].current == 1
    assert progress[1].total == 2
    assert progress[1].detail == str(a)
    assert progress[2].current == 1
    assert progress[2].total == 2
    assert progress[2].detail == str(b)
    assert progress[3].current == 2
    assert progress[3].total == 2
    assert progress[3].detail == str(b)
    assert all(e.phase == Phase.CLEARCUT_BATCH for e in progress)

    assert len(warnings) == 1
    assert warnings[0].message == "aviso"
    assert warnings[0].phase == Phase.CLEARCUT_BATCH

    assert len(completed) == 1
    assert completed[0].phase == Phase.CLEARCUT_BATCH

    # el reporter fue el último evento emitido (el loop terminó normalmente)
    assert reporter.events[-1].type == ProgressEventType.COMPLETED


def test_processor_reporter_completed_even_when_cancelled(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(b"1")
    b.write_bytes(b"2")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def remove_fn(
        input_path: Path,
        output_path: Path,
        _strategy: BackgroundRemovalStrategy,
        _config: RemovalConfig,
    ) -> np.ndarray:
        output_path.write_bytes(b"cut")
        return np.zeros((8, 8, 4), dtype=np.uint8)

    def scale_fn(input_path: Path, output_path: Path, **_kwargs: Any) -> ScaleOutcome:
        output_path.write_bytes(b"scaled")
        return _fake_outcome(output_path)

    reporter = FakeProgressReporter()
    report = BatchProcessor(remove_fn=remove_fn, scale_fn=scale_fn).run(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=2,
        ),
        FilesInputSource(paths=(a, b)),
        DirectoryOutputTarget(directory=out_dir),
        should_cancel=lambda: True,
        reporter=reporter,
    )

    assert report.cancelled is True
    started = [e for e in reporter.events if e.type == ProgressEventType.STARTED]
    progress = [e for e in reporter.events if e.type == ProgressEventType.PROGRESS]
    completed = [e for e in reporter.events if e.type == ProgressEventType.COMPLETED]
    assert len(started) == 1
    assert progress == []
    assert len(completed) == 1


def test_processor_reporter_and_legacy_callbacks_coexist(tmp_path: Path) -> None:
    path = tmp_path / "a.png"
    path.write_bytes(b"1")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def remove_fn(
        input_path: Path,
        output_path: Path,
        _strategy: BackgroundRemovalStrategy,
        _config: RemovalConfig,
    ) -> np.ndarray:
        output_path.write_bytes(b"cut")
        return np.zeros((8, 8, 4), dtype=np.uint8)

    def scale_fn(input_path: Path, output_path: Path, **_kwargs: Any) -> ScaleOutcome:
        output_path.write_bytes(b"scaled")
        return _fake_outcome(output_path)

    reporter = FakeProgressReporter()
    legacy_progress: list[tuple[int, int, Path]] = []
    legacy_items: list[BatchItemResult] = []

    BatchProcessor(remove_fn=remove_fn, scale_fn=scale_fn).run(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=2,
        ),
        FilesInputSource(paths=(path,)),
        DirectoryOutputTarget(directory=out_dir),
        on_progress=lambda current, total, p: legacy_progress.append((current, total, p)),
        on_item=lambda item: legacy_items.append(item),
        reporter=reporter,
    )

    assert legacy_progress == [(1, 1, path)]
    assert len(legacy_items) == 1
    assert legacy_items[0].status == "succeeded"

    progress_events = [e for e in reporter.events if e.type == ProgressEventType.PROGRESS]
    assert len(progress_events) == 2
    assert progress_events[0].current == 0
    assert progress_events[0].total == 1
    assert progress_events[0].detail == str(path)
    assert progress_events[1].current == 1
    assert progress_events[1].total == 1
    assert progress_events[1].detail == str(path)


def test_processor_no_reporter_keeps_legacy_behavior_intact(tmp_path: Path) -> None:
    path = tmp_path / "a.png"
    path.write_bytes(b"1")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def remove_fn(
        input_path: Path,
        output_path: Path,
        _strategy: BackgroundRemovalStrategy,
        _config: RemovalConfig,
    ) -> np.ndarray:
        output_path.write_bytes(b"cut")
        return np.zeros((8, 8, 4), dtype=np.uint8)

    def scale_fn(input_path: Path, output_path: Path, **_kwargs: Any) -> ScaleOutcome:
        output_path.write_bytes(b"scaled")
        return _fake_outcome(output_path)

    report = BatchProcessor(remove_fn=remove_fn, scale_fn=scale_fn).run(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=2,
        ),
        FilesInputSource(paths=(path,)),
        DirectoryOutputTarget(directory=out_dir),
    )

    assert report.succeeded == 1


def test_run_batch_functional_accepts_reporter(tmp_path: Path) -> None:
    path = tmp_path / "a.png"
    path.write_bytes(b"1")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def remove_fn(
        input_path: Path,
        output_path: Path,
        _strategy: BackgroundRemovalStrategy,
        _config: RemovalConfig,
    ) -> np.ndarray:
        output_path.write_bytes(b"cut")
        return np.zeros((8, 8, 4), dtype=np.uint8)

    def scale_fn(input_path: Path, output_path: Path, **_kwargs: Any) -> ScaleOutcome:
        output_path.write_bytes(b"scaled")
        return _fake_outcome(output_path)

    reporter = FakeProgressReporter()
    report = run_batch(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=2,
        ),
        FilesInputSource(paths=(path,)),
        DirectoryOutputTarget(directory=out_dir),
        reporter=reporter,
        processor=BatchProcessor(remove_fn=remove_fn, scale_fn=scale_fn),
    )

    assert report.succeeded == 1
    types = [e.type for e in reporter.events]
    assert types == [
        ProgressEventType.STARTED,
        ProgressEventType.PROGRESS,
        ProgressEventType.PROGRESS,
        ProgressEventType.COMPLETED,
    ]


def test_run_batch_integration_realesrgan(
    tmp_path: Path,
    synthetic_white_bg_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cv2

    from designfabric.core.imaging.upscale_strategies import RealEsrganUpscaleStrategy

    class _FakeBackend:
        native_scale = 4

        def upscale_to_factor(self, image_bgra: np.ndarray, factor: int) -> np.ndarray:
            h, w = image_bgra.shape[:2]
            return cv2.resize(image_bgra, (w * factor, h * factor), interpolation=cv2.INTER_NEAREST)

    fake = RealEsrganUpscaleStrategy(backend=_FakeBackend())  # type: ignore[arg-type]
    monkeypatch.setattr(
        "designfabric.core.imaging.upscale_pipeline.create_upscale_strategy",
        lambda name: fake,
    )
    monkeypatch.setattr(
        "designfabric.core.imaging.upscale_pipeline.ensure_models_for_strategy",
        lambda *args, **kwargs: None,
    )

    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()

    shutil.copy(synthetic_white_bg_path, input_dir / "one.png")
    shutil.copy(synthetic_white_bg_path, input_dir / "two.png")
    (input_dir / "ignore.txt").write_text("skip", encoding="utf-8")

    report = run_batch(
        BatchConfig(
            removal_strategy="white_background",
            scale_strategy="realesrgan",
            scale_factor=2,
        ),
        FolderInputSource(directory=input_dir),
        DirectoryOutputTarget(directory=output_dir),
    )

    assert report.total == 3
    assert report.succeeded == 2
    assert report.skipped == 1
    assert report.failed == 0
    assert (output_dir / "one.png").is_file()
    assert (output_dir / "two.png").is_file()

    payload = report.to_dict()
    assert payload["succeeded"] == 2
    assert isinstance(payload["items"], list)
