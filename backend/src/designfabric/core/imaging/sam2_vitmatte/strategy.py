"""Estrategia de eliminación de fondo basada en SAM2 Tiny + ViTMatte."""

from __future__ import annotations

import numpy as np

from designfabric.core.imaging.background_removal_strategies import (
    BackgroundRemovalStrategy,
    RemovalModelPaths,
)
from designfabric.core.imaging.sam2_vitmatte.pipeline import Sam2VitMattePipeline
from designfabric.core.imaging.sam2_vitmatte.sam2_session import Sam2OnnxSession, Sam2Runner
from designfabric.core.imaging.sam2_vitmatte.vitmatte_session import VitMatteOnnxSession, VitMatteRunner


class Sam2VitMatteStrategy(BackgroundRemovalStrategy):
    """SAM2 Tiny ONNX + ViTMatte ONNX + Guided Filter + postprocesado OpenCV."""

    def __init__(
        self,
        model_paths: RemovalModelPaths,
        *,
        sam2: Sam2Runner | None = None,
        vitmatte: VitMatteRunner | None = None,
    ) -> None:
        self._model_paths = model_paths
        if sam2 is not None:
            self._sam2 = sam2
        else:
            assert (
                model_paths.sam2_encoder_onnx and model_paths.sam2_decoder_onnx
            ), "Sam2VitMatteStrategy requiere las rutas ONNX del encoder y decoder SAM2"
            self._sam2 = Sam2OnnxSession(model_paths.sam2_encoder_onnx, model_paths.sam2_decoder_onnx)

        if vitmatte is not None:
            self._vitmatte = vitmatte
        else:
            assert model_paths.vitmatte_onnx, "Sam2VitMatteStrategy requiere la ruta ONNX de ViTMatte"
            self._vitmatte = VitMatteOnnxSession(model_paths.vitmatte_onnx)
        self._pipeline = Sam2VitMattePipeline(self._sam2, self._vitmatte)

    def remove_background(self, image: np.ndarray) -> np.ndarray:
        return self._pipeline.run(image)
