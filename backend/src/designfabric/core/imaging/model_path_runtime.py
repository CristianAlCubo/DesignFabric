"""Runtime mutable de rutas a modelos ONNX de eliminación de fondo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from designfabric.core.config import Settings, get_settings
from designfabric.core.imaging.background_removal_strategies import RemovalModelPaths


@dataclass
class ModelPathSnapshot:
    sam2_encoder_onnx: str | None
    sam2_decoder_onnx: str | None
    vitmatte_onnx: str | None
    isnet_general_onnx: str | None


class ModelPathRuntime:
    """Estado en memoria (sincronizado desde Settings / API / Electron)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._sam2_encoder_onnx: str | None = None
        self._sam2_decoder_onnx: str | None = None
        self._vitmatte_onnx: str | None = None
        self._isnet_general_onnx: str | None = None
        self._seeded = False

    def seed_from_settings(self, settings: Settings | None = None) -> None:
        with self._lock:
            if self._seeded:
                return
            cfg = settings or get_settings()
            self._sam2_encoder_onnx = cfg.sam2_encoder_onnx
            self._sam2_decoder_onnx = cfg.sam2_decoder_onnx
            self._vitmatte_onnx = cfg.vitmatte_onnx
            self._isnet_general_onnx = cfg.isnet_general_onnx
            self._seeded = True

    def update(
        self,
        *,
        sam2_encoder_onnx: str | None = None,
        sam2_decoder_onnx: str | None = None,
        vitmatte_onnx: str | None = None,
        isnet_general_onnx: str | None = None,
        clear_sam2_encoder: bool = False,
        clear_sam2_decoder: bool = False,
        clear_vitmatte: bool = False,
        clear_isnet_general: bool = False,
    ) -> ModelPathSnapshot:
        with self._lock:
            if clear_sam2_encoder:
                self._sam2_encoder_onnx = None
            elif sam2_encoder_onnx is not None:
                self._sam2_encoder_onnx = sam2_encoder_onnx or None
            if clear_sam2_decoder:
                self._sam2_decoder_onnx = None
            elif sam2_decoder_onnx is not None:
                self._sam2_decoder_onnx = sam2_decoder_onnx or None
            if clear_vitmatte:
                self._vitmatte_onnx = None
            elif vitmatte_onnx is not None:
                self._vitmatte_onnx = vitmatte_onnx or None
            if clear_isnet_general:
                self._isnet_general_onnx = None
            elif isnet_general_onnx is not None:
                self._isnet_general_onnx = isnet_general_onnx or None
            self._seeded = True
            return ModelPathSnapshot(
                self._sam2_encoder_onnx,
                self._sam2_decoder_onnx,
                self._vitmatte_onnx,
                self._isnet_general_onnx,
            )

    def snapshot(self) -> ModelPathSnapshot:
        with self._lock:
            return ModelPathSnapshot(
                self._sam2_encoder_onnx,
                self._sam2_decoder_onnx,
                self._vitmatte_onnx,
                self._isnet_general_onnx,
            )

    def resolve_paths(self) -> RemovalModelPaths:
        """Devuelve las rutas configuradas; los campos ausentes quedan en `None`.

        La validación de qué campos requiere cada estrategia vive en
        `create_background_removal_strategy`, no aquí.
        """
        snap = self.snapshot()
        return RemovalModelPaths(
            sam2_encoder_onnx=Path(snap.sam2_encoder_onnx) if snap.sam2_encoder_onnx else None,
            sam2_decoder_onnx=Path(snap.sam2_decoder_onnx) if snap.sam2_decoder_onnx else None,
            vitmatte_onnx=Path(snap.vitmatte_onnx) if snap.vitmatte_onnx else None,
            isnet_general_onnx=Path(snap.isnet_general_onnx) if snap.isnet_general_onnx else None,
        )

    def reset_for_tests(self) -> None:
        with self._lock:
            self._sam2_encoder_onnx = None
            self._sam2_decoder_onnx = None
            self._vitmatte_onnx = None
            self._isnet_general_onnx = None
            self._seeded = False


_RUNTIME = ModelPathRuntime()


def get_model_path_runtime() -> ModelPathRuntime:
    return _RUNTIME
