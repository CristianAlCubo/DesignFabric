"""Endpoints para configurar rutas locales a modelos ONNX (SAM2 / ViTMatte)."""

from __future__ import annotations

from fastapi import APIRouter

from designfabric.api.schemas import ModelPathsPublicResponse, ModelPathsUpdateRequest
from designfabric.core.imaging.model_path_runtime import get_model_path_runtime

router = APIRouter(tags=["model-paths"])


def _public() -> ModelPathsPublicResponse:
    snap = get_model_path_runtime().snapshot()
    return ModelPathsPublicResponse(
        sam2_encoder_onnx=snap.sam2_encoder_onnx,
        sam2_decoder_onnx=snap.sam2_decoder_onnx,
        vitmatte_onnx=snap.vitmatte_onnx,
        isnet_general_onnx=snap.isnet_general_onnx,
    )


@router.get("/api/settings/model-paths", response_model=ModelPathsPublicResponse)
def get_model_paths() -> ModelPathsPublicResponse:
    runtime = get_model_path_runtime()
    runtime.seed_from_settings()
    return _public()


@router.put("/api/settings/model-paths", response_model=ModelPathsPublicResponse)
def put_model_paths(payload: ModelPathsUpdateRequest) -> ModelPathsPublicResponse:
    runtime = get_model_path_runtime()
    runtime.seed_from_settings()
    runtime.update(
        sam2_encoder_onnx=payload.sam2_encoder_onnx,
        sam2_decoder_onnx=payload.sam2_decoder_onnx,
        vitmatte_onnx=payload.vitmatte_onnx,
        isnet_general_onnx=payload.isnet_general_onnx,
        clear_sam2_encoder=payload.clear_sam2_encoder,
        clear_sam2_decoder=payload.clear_sam2_decoder,
        clear_vitmatte=payload.clear_vitmatte,
        clear_isnet_general=payload.clear_isnet_general,
    )
    return _public()
