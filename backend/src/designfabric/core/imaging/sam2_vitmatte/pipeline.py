"""Orquestación del pipeline SAM2 Tiny + ViTMatte + Guided Filter."""

from __future__ import annotations

import logging

import cv2
import numpy as np

from designfabric.core.imaging.sam2_vitmatte.guided_filter import guided_filter
from designfabric.core.imaging.sam2_vitmatte.mask_selection import clean_mask, select_primary_mask
from designfabric.core.imaging.sam2_vitmatte.postprocess import (
    compose_bgra,
    refine_alpha_edges,
    upscale_alpha,
)
from designfabric.core.imaging.sam2_vitmatte.preprocess import resize_long_side
from designfabric.core.imaging.sam2_vitmatte.sam2_session import Sam2Runner
from designfabric.core.imaging.sam2_vitmatte.trimap import build_trimap
from designfabric.core.imaging.sam2_vitmatte.vitmatte_session import VitMatteRunner

logger = logging.getLogger(__name__)

_WORKING_LONG_SIDE = 1024


class Sam2VitMattePipeline:
    """Ejecuta el pipeline completo de matting sobre una imagen BGR."""

    def __init__(self, sam2: Sam2Runner, vitmatte: VitMatteRunner) -> None:
        self._sam2 = sam2
        self._vitmatte = vitmatte

    def run(self, image_bgr: np.ndarray) -> np.ndarray:
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError(f"Se esperaba BGR uint8; shape={image_bgr.shape}")

        orig_h, orig_w = image_bgr.shape[:2]
        working, _ = resize_long_side(image_bgr, _WORKING_LONG_SIDE)

        masks = self._sam2.predict_masks(working)
        primary = select_primary_mask(masks)
        primary = clean_mask(primary)
        if not np.any(primary):
            logger.warning("SAM2 no detectó sujeto; se devuelve alpha vacío")
            empty = np.zeros((orig_h, orig_w), dtype=np.float32)
            return compose_bgra(image_bgr, empty)

        # Alinear máscara al working size por si el modelo devolvió otra resolución.
        if primary.shape[:2] != working.shape[:2]:
            primary = cv2.resize(
                primary,
                (working.shape[1], working.shape[0]),
                interpolation=cv2.INTER_NEAREST,
            )

        trimap = build_trimap(primary)
        alpha_small = self._vitmatte.predict_alpha(working, trimap)

        if alpha_small.shape[:2] != working.shape[:2]:
            alpha_small = upscale_alpha(alpha_small, working.shape[1], working.shape[0])

        guide = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
        alpha_refined = guided_filter(guide, alpha_small, radius=8, eps=1e-2)
        alpha_refined = refine_alpha_edges(np.clip(alpha_refined, 0.0, 1.0))

        alpha_full = upscale_alpha(alpha_refined, orig_w, orig_h)
        return compose_bgra(image_bgr, alpha_full)
