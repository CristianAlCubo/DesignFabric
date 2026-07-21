"""Estrategia BiRefNet (principal) → SAM2 (refinamiento opcional) → matte final.

Pipeline:
1. BiRefNet (vía `rembg`, sesión `"birefnet-general"`) produce la máscara de sujeto
   principal — ya reescalada por `rembg` a la resolución de trabajo, sin preproceso
   ONNX manual que portar.
2. SAM2 (opcional): si hay rutas ONNX de SAM2 configuradas (las mismas que usa
   `sam2_vitmatte`, en Ajustes → Modelos locales), se reprompta con el centroide de
   la máscara de BiRefNet. Si el resultado tiene buen solape (IoU) con la máscara de
   BiRefNet se adopta (borde más preciso); si no, se conserva BiRefNet — evita que
   SAM2 enganche el objeto equivocado en ilustraciones con varios elementos.
3. Matte final, automático según qué haya configurado:
   - Si hay `vitmatte_onnx` configurado: trimap + ViTMatte (alpha suave con trimap).
   - Si no: BRIA RMBG (vía `rembg`, sesión `"bria-rmbg"`) como alpha de un solo paso,
     acotado a la región ya detectada.
4. Guided filter + suavizado de bordes + composición BGRA (reutilizados de
   `sam2_vitmatte`).
"""

from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np

from designfabric.core.imaging.background_removal_strategies import (
    BackgroundRemovalStrategy,
    RemovalModelPaths,
)
from designfabric.core.imaging.sam2_vitmatte.guided_filter import guided_filter
from designfabric.core.imaging.sam2_vitmatte.mask_selection import clean_mask, select_primary_mask
from designfabric.core.imaging.sam2_vitmatte.postprocess import (
    compose_bgra,
    refine_alpha_edges,
    upscale_alpha,
)
from designfabric.core.imaging.sam2_vitmatte.preprocess import resize_long_side
from designfabric.core.imaging.sam2_vitmatte.sam2_session import Sam2OnnxSession, Sam2Runner
from designfabric.core.imaging.sam2_vitmatte.trimap import build_trimap
from designfabric.core.imaging.sam2_vitmatte.vitmatte_session import VitMatteOnnxSession, VitMatteRunner

logger = logging.getLogger(__name__)

_WORKING_LONG_SIDE = 1024
_BIREFNET_SESSION_NAME = "birefnet-general"
_BRIA_SESSION_NAME = "bria-rmbg"
_SAM2_IOU_ACCEPT_THRESHOLD = 0.5
_BRIA_GUARD_DILATE_PX = 15


class BiRefNetSam2MatteStrategy(BackgroundRemovalStrategy):
    """BiRefNet + SAM2 opcional + (ViTMatte o BRIA RMBG) + guided filter."""

    def __init__(
        self,
        model_paths: RemovalModelPaths,
        *,
        sam2: Sam2Runner | None = None,
        vitmatte: VitMatteRunner | None = None,
    ) -> None:
        self._model_paths = model_paths
        self._birefnet_session: Any | None = None
        self._bria_session: Any | None = None

        if sam2 is not None:
            self._sam2: Sam2Runner | None = sam2
        elif model_paths.sam2_encoder_onnx and model_paths.sam2_decoder_onnx:
            self._sam2 = Sam2OnnxSession(model_paths.sam2_encoder_onnx, model_paths.sam2_decoder_onnx)
        else:
            self._sam2 = None

        if vitmatte is not None:
            self._vitmatte: VitMatteRunner | None = vitmatte
        elif model_paths.vitmatte_onnx:
            self._vitmatte = VitMatteOnnxSession(model_paths.vitmatte_onnx)
        else:
            self._vitmatte = None

    def remove_background(self, image_bgr: np.ndarray) -> np.ndarray:
        orig_h, orig_w = image_bgr.shape[:2]
        working, _ = resize_long_side(image_bgr, _WORKING_LONG_SIDE)

        primary_mask = clean_mask(self._predict_birefnet_mask(working))
        if not np.any(primary_mask):
            logger.warning("BiRefNet no detectó sujeto; se devuelve alpha vacío")
            empty = np.zeros((orig_h, orig_w), dtype=np.float32)
            return compose_bgra(image_bgr, empty)

        refined_mask = primary_mask
        if self._sam2 is not None:
            refined_mask = self._maybe_refine_with_sam2(working, primary_mask)

        if self._vitmatte is not None:
            trimap = build_trimap(refined_mask)
            alpha_small = self._vitmatte.predict_alpha(working, trimap)
            if alpha_small.shape[:2] != working.shape[:2]:
                alpha_small = upscale_alpha(alpha_small, working.shape[1], working.shape[0])
        else:
            alpha_small = self._predict_bria_alpha(working, refined_mask)

        guide = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
        alpha_refined = guided_filter(guide, alpha_small, radius=8, eps=1e-2)
        alpha_refined = refine_alpha_edges(np.clip(alpha_refined, 0.0, 1.0))

        alpha_full = upscale_alpha(alpha_refined, orig_w, orig_h)
        return compose_bgra(image_bgr, alpha_full)

    def _ensure_birefnet_session(self) -> Any:
        if self._birefnet_session is None:
            from rembg import new_session  # type: ignore[import-untyped]

            self._birefnet_session = new_session(_BIREFNET_SESSION_NAME)
            logger.info("Sesión rembg cargada (%s)", _BIREFNET_SESSION_NAME)
        return self._birefnet_session

    def _ensure_bria_session(self) -> Any:
        if self._bria_session is None:
            from rembg import new_session

            self._bria_session = new_session(_BRIA_SESSION_NAME)
            logger.info("Sesión rembg cargada (%s)", _BRIA_SESSION_NAME)
        return self._bria_session

    def _predict_birefnet_mask(self, working: np.ndarray) -> np.ndarray:
        from rembg import remove

        session = self._ensure_birefnet_session()
        rgb = cv2.cvtColor(working, cv2.COLOR_BGR2RGB)
        mask = np.asarray(remove(rgb, session=session, only_mask=True))
        if mask.ndim == 3:
            mask = mask[:, :, 0]
        return (mask > 127).astype(np.uint8) * 255

    def _predict_bria_alpha(self, working: np.ndarray, refined_mask: np.ndarray) -> np.ndarray:
        from rembg import remove

        session = self._ensure_bria_session()
        rgb = cv2.cvtColor(working, cv2.COLOR_BGR2RGB)
        raw = np.asarray(remove(rgb, session=session, only_mask=True))
        if raw.ndim == 3:
            raw = raw[:, :, 0]
        alpha = raw.astype(np.float32) / 255.0

        guard_kernel = np.ones((_BRIA_GUARD_DILATE_PX, _BRIA_GUARD_DILATE_PX), dtype=np.uint8)
        guard = cv2.dilate(refined_mask, guard_kernel)
        return np.where(guard > 0, alpha, 0.0).astype(np.float32)

    def _maybe_refine_with_sam2(self, working: np.ndarray, primary_mask: np.ndarray) -> np.ndarray:
        assert self._sam2 is not None
        centroid = self._mask_centroid(primary_mask)
        if centroid is None:
            return primary_mask

        sam_masks = self._sam2.predict_masks(working, point_xy=centroid)
        sam_mask = clean_mask(select_primary_mask(sam_masks))
        if self._iou(primary_mask, sam_mask) >= _SAM2_IOU_ACCEPT_THRESHOLD:
            return sam_mask
        return primary_mask

    @staticmethod
    def _mask_centroid(mask: np.ndarray) -> tuple[float, float] | None:
        moments = cv2.moments(mask, binaryImage=True)
        if moments["m00"] == 0:
            return None
        return (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])

    @staticmethod
    def _iou(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
        a_bool = mask_a > 0
        b_bool = mask_b > 0
        union = np.logical_or(a_bool, b_bool).sum()
        if union == 0:
            return 0.0
        intersection = np.logical_and(a_bool, b_bool).sum()
        return float(intersection) / float(union)
