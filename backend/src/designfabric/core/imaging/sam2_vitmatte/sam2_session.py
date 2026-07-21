"""Sesión ONNX lazy para SAM2 Tiny (encoder + decoder, prompt por punto central).

Contrato alineado con los exports de samexporter / vietanhdev:
encoder → (high_res_feats_0, high_res_feats_1, image_embed)
decoder → máscaras a partir de embeddings + puntos.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class Sam2Runner(Protocol):
    def predict_masks(
        self, image_bgr: np.ndarray, point_xy: tuple[float, float] | None = None
    ) -> np.ndarray:
        """Devuelve máscaras candidatas (N,H,W) o (H,W)."""


class Sam2OnnxSession:
    """Inferencia SAM2 Tiny vía onnxruntime (encoder → decoder)."""

    def __init__(self, encoder_path: Path, decoder_path: Path) -> None:
        self._encoder_path = Path(encoder_path)
        self._decoder_path = Path(decoder_path)
        self._encoder: Any | None = None
        self._decoder: Any | None = None
        self._encoder_input_name: str | None = None
        self._encoder_output_names: list[str] = []
        self._decoder_input_names: list[str] = []
        self._decoder_output_names: list[str] = []
        self._encoder_hw: tuple[int, int] = (1024, 1024)

    def _ensure_sessions(self) -> tuple[Any, Any]:
        if self._encoder is not None and self._decoder is not None:
            return self._encoder, self._decoder
        try:
            import onnxruntime as ort  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "onnxruntime no está instalado. Ejecuta `uv sync` e inténtalo de nuevo."
            ) from exc

        for path, label in (
            (self._encoder_path, "encoder SAM2"),
            (self._decoder_path, "decoder SAM2"),
        ):
            if not path.is_file():
                raise RuntimeError(
                    f"Modelo {label} no encontrado: {path}. "
                    "Configura las rutas en Ajustes → Modelos locales."
                )

        self._encoder = ort.InferenceSession(
            str(self._encoder_path),
            providers=["CPUExecutionProvider"],
        )
        self._decoder = ort.InferenceSession(
            str(self._decoder_path),
            providers=["CPUExecutionProvider"],
        )

        enc_inputs = self._encoder.get_inputs()
        self._encoder_input_name = enc_inputs[0].name
        shape = enc_inputs[0].shape
        if len(shape) >= 4 and isinstance(shape[2], int) and isinstance(shape[3], int):
            self._encoder_hw = (int(shape[2]), int(shape[3]))
        self._encoder_output_names = [out.name for out in self._encoder.get_outputs()]
        self._decoder_input_names = [inp.name for inp in self._decoder.get_inputs()]
        self._decoder_output_names = [out.name for out in self._decoder.get_outputs()]

        logger.info(
            "Sesiones SAM2 cargadas (encoder=%s, decoder=%s)",
            self._encoder_path,
            self._decoder_path,
        )
        return self._encoder, self._decoder

    def predict_masks(
        self, image_bgr: np.ndarray, point_xy: tuple[float, float] | None = None
    ) -> np.ndarray:
        encoder, decoder = self._ensure_sessions()
        assert self._encoder_input_name is not None

        orig_h, orig_w = image_bgr.shape[:2]
        input_tensor = self._prepare_encoder_input(image_bgr)
        enc_outputs = encoder.run(
            self._encoder_output_names,
            {self._encoder_input_name: input_tensor},
        )
        if len(enc_outputs) < 3:
            raise RuntimeError(
                f"El encoder SAM2 debe devolver 3 tensores; se obtuvieron {len(enc_outputs)}"
            )
        high_res_feats_0, high_res_feats_1, image_embed = (
            enc_outputs[0],
            enc_outputs[1],
            enc_outputs[2],
        )

        # Prompt: punto explícito si se provee (p.ej. centroide de otra máscara);
        # si no, el centro de la imagen original (coordenadas en espacio original).
        prompt_x, prompt_y = point_xy if point_xy is not None else (orig_w / 2.0, orig_h / 2.0)
        point_coords = np.array([[prompt_x, prompt_y]], dtype=np.float32)
        point_labels = np.array([1], dtype=np.float32)

        decoder_feeds = self._prepare_decoder_feeds(
            image_embed,
            high_res_feats_0,
            high_res_feats_1,
            point_coords,
            point_labels,
            orig_hw=(orig_h, orig_w),
        )
        dec_outputs = decoder.run(self._decoder_output_names, decoder_feeds)
        return self._extract_masks(dec_outputs, orig_h, orig_w)

    def _prepare_encoder_input(self, image_bgr: np.ndarray) -> np.ndarray:
        height, width = self._encoder_hw
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (width, height), interpolation=cv2.INTER_LINEAR)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normed = (resized.astype(np.float32) / 255.0 - mean) / std
        return np.transpose(normed, (2, 0, 1))[None, ...].astype(np.float32)

    def _prepare_decoder_feeds(
        self,
        image_embed: np.ndarray,
        high_res_feats_0: np.ndarray,
        high_res_feats_1: np.ndarray,
        point_coords: np.ndarray,
        point_labels: np.ndarray,
        *,
        orig_hw: tuple[int, int],
    ) -> dict[str, np.ndarray]:
        enc_h, enc_w = self._encoder_hw
        orig_h, orig_w = orig_hw

        coords = point_coords.astype(np.float32)[None, ...]
        labels = point_labels.astype(np.float32)[None, ...]
        coords = coords.copy()
        coords[..., 0] = coords[..., 0] / orig_w * enc_w
        coords[..., 1] = coords[..., 1] / orig_h * enc_h

        num_labels = labels.shape[0]
        mask_input = np.zeros(
            (num_labels, 1, enc_h // 4, enc_w // 4),
            dtype=np.float32,
        )
        has_mask_input = np.array([0], dtype=np.float32)

        # Roles más largos primero: "mask_input" es subcadena de "has_mask_input".
        values_by_role: list[tuple[str, np.ndarray]] = [
            ("has_mask_input", has_mask_input),
            ("mask_input", mask_input),
            ("high_res_feats_0", high_res_feats_0.astype(np.float32)),
            ("high_res_feats_1", high_res_feats_1.astype(np.float32)),
            ("image_embedding", image_embed.astype(np.float32)),
            ("image_embed", image_embed.astype(np.float32)),
            ("point_coords", coords),
            ("point_labels", labels),
        ]

        ordered_defaults = [
            image_embed.astype(np.float32),
            high_res_feats_0.astype(np.float32),
            high_res_feats_1.astype(np.float32),
            coords,
            labels,
            mask_input,
            has_mask_input,
        ]

        feeds: dict[str, np.ndarray] = {}
        for index, name in enumerate(self._decoder_input_names):
            lower = name.lower()
            matched = self._match_decoder_input(lower, values_by_role)
            if matched is None and index < len(ordered_defaults):
                matched = ordered_defaults[index]
            if matched is None:
                raise RuntimeError(f"No se pudo mapear la entrada del decoder SAM2: {name}")
            feeds[name] = matched
        return feeds

    @staticmethod
    def _match_decoder_input(
        lower_name: str,
        values_by_role: list[tuple[str, np.ndarray]],
    ) -> np.ndarray | None:
        for role, value in values_by_role:
            if lower_name == role:
                return value
        for role, value in values_by_role:
            if role in lower_name:
                return value
        return None

    @staticmethod
    def _extract_masks(outputs: list[Any], height: int, width: int) -> np.ndarray:
        if not outputs:
            raise RuntimeError("El decoder SAM2 no produjo salidas")

        masks = np.asarray(outputs[0], dtype=np.float32)
        scores = np.asarray(outputs[1]).reshape(-1) if len(outputs) > 1 else None

        # Formas típicas: (1, N, H, W) o (N, H, W)
        if masks.ndim == 4:
            masks = masks[0]
        if masks.ndim == 2:
            masks = masks[None, ...]
        if masks.ndim != 3:
            raise RuntimeError(f"Forma de máscaras SAM2 no soportada: {masks.shape}")

        if scores is not None and scores.size == masks.shape[0]:
            best = masks[int(np.argmax(scores))]
            masks = best[None, ...]

        resized = []
        for mask in masks:
            if mask.shape[-2:] != (height, width):
                mask = cv2.resize(
                    mask.astype(np.float32),
                    (width, height),
                    interpolation=cv2.INTER_LINEAR,
                )
            resized.append(mask)
        return np.stack(resized, axis=0)
