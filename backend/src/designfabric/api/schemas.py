"""Schemas pydantic del API: requests, responses y eventos de progreso serializables.

Se mantienen deliberadamente separados de `core.progress.ProgressEvent` (que
no depende de pydantic) para que el dominio no filtre detalles de FastAPI.

NOTA (Fase 2): este archivo contenía por ahora solo `ProgressEventSchema`.
En la Fase 4 se agrega el resto de schemas (uno por feature): los heredados
de DesignFabric (batch/single-image de generación IA) y los nuevos de
ClearCut (remove-background/scale/clearcut-batch). `JobType`/`JobStatus` NO
se redefinen acá: son los de `jobs/models.py` (Fase 2), compartidos por
todos los tipos de job del sistema unificado.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from designfabric.core.generation.constants import OLLAMA_MODEL_DEFAULT
from designfabric.jobs.models import JobStatus, JobType


class ProgressEventSchema(BaseModel):
    """Serialización pública (WebSocket) de un `core.progress.ProgressEvent`."""

    job_id: str
    phase: str
    type: Literal["started", "progress", "completed", "failed", "warning"]
    current: int | None = None
    total: int | None = None
    detail: str | None = None
    message: str | None = None
    timestamp: datetime


# ---------------------------------------------------------------------------
# DesignFabric (generación IA): heredados tal cual de DesignFabric, adaptados
# solo para importar JobType/JobStatus de jobs/models.py en vez de redefinirlos.
# ---------------------------------------------------------------------------


class BatchJobRequest(BaseModel):
    """Payload para encolar un job batch: equivalente al flujo actual del CLI (`--n`)."""

    num_images: int = Field(gt=0, le=50, description="Número de stickers a generar")
    ollama_model: str = Field(default=OLLAMA_MODEL_DEFAULT, description="Modelo de Ollama a usar para los conceptos")
    llm_provider: Literal["ollama", "openrouter", "test"] = Field(
        default="ollama", description="Provider primitivo de texto para generar conceptos"
    )
    image_provider: Literal["flux", "openrouter", "test"] = Field(
        default="flux", description="Provider primitivo de imagen para renderizar prompts"
    )
    transparent_background: bool = Field(
        default=True,
        description="Si el modelo OpenRouter lo soporta, pedir fondo transparente",
    )


class SingleImageJobRequest(BaseModel):
    """Payload para generar una única imagen a partir de un prompt escrito por el usuario."""

    prompt: str = Field(min_length=1, max_length=2000, description="Prompt libre en inglés para Flux")
    apply_style_suffix: bool = Field(
        default=True, description="Si se concatena el STYLE_SUFFIX de sticker al prompt del usuario"
    )
    image_provider: Literal["flux", "openrouter", "test"] = Field(
        default="flux", description="Provider primitivo de imagen para renderizar el prompt"
    )
    transparent_background: bool = Field(
        default=True,
        description="Si el modelo OpenRouter lo soporta, pedir fondo transparente",
    )


class ProviderInfoSchema(BaseModel):
    """Entrada del catálogo de providers de generación."""

    id: str
    label: str
    available: bool
    requires_local_ai: bool


class GenerationProvidersResponse(BaseModel):
    """Catálogo de providers LLM e imagen disponibles en este entorno."""

    llm: list[ProviderInfoSchema]
    image: list[ProviderInfoSchema]


class LocalAiStatusSchema(BaseModel):
    available: bool
    missing: list[str] = Field(default_factory=list)


class OllamaStatusSchema(BaseModel):
    host: str
    reachable: bool
    models: list[str] = Field(default_factory=list)
    error: str | None = None


class FluxStatusSchema(BaseModel):
    model_id: str
    weights_present: bool
    cache_hint: str | None = None


class CudaStatusSchema(BaseModel):
    available: bool
    device_name: str | None = None


class ProviderReadinessSchema(BaseModel):
    ollama: bool
    flux: bool
    test_llm: bool = True
    test_image: bool = True
    openrouter_llm: bool = False
    openrouter_image: bool = False


class OpenRouterStatusSchema(BaseModel):
    configured: bool
    text_model_id: str | None = None
    image_model_id: str | None = None


class GenerationReadinessResponse(BaseModel):
    """Fuente de verdad de readiness de generación IA (solo reporte)."""

    local_ai: LocalAiStatusSchema
    ollama: OllamaStatusSchema
    flux: FluxStatusSchema
    cuda: CudaStatusSchema
    providers: ProviderReadinessSchema
    openrouter: OpenRouterStatusSchema | None = None


class OpenRouterSettingsUpdateRequest(BaseModel):
    """Actualiza runtime config OpenRouter (key y/o modelos)."""

    api_key: str | None = None
    clear_api_key: bool = False
    text_model_id: str | None = None
    image_model_id: str | None = None
    image_model_output_modalities: list[str] | None = None
    clear_text_model: bool = False
    clear_image_model: bool = False


class OpenRouterSettingsPublicResponse(BaseModel):
    """Estado público (sin exponer la API key)."""

    configured: bool
    text_model_id: str | None = None
    image_model_id: str | None = None
    image_model_output_modalities: list[str] | None = None


class OpenRouterModelSchema(BaseModel):
    id: str
    name: str
    output_modalities: list[str] = Field(default_factory=list)
    supports_transparent_background: bool = False


class OpenRouterModelsResponse(BaseModel):
    models: list[OpenRouterModelSchema]


class JobCreatedResponse(BaseModel):
    """Respuesta al encolar un job."""

    job_id: str
    status: JobStatus


class StickerResultSchema(BaseModel):
    """Resultado de generar un sticker, con la URL desde la que la UI puede cargar la imagen."""

    prompt: str
    filename: str | None
    image_url: str | None
    success: bool
    error: str | None = None


class BatchJobResultSchema(BaseModel):
    """Resultado completo de un job batch: prompts generados + resultado por imagen."""

    prompts: list[str]
    results: list[StickerResultSchema]
    failure_count: int
    cancelled: bool = False


# ---------------------------------------------------------------------------
# ClearCut (eliminación de fondo / escalado / batch): nuevos en esta fase.
# ---------------------------------------------------------------------------


class RemoveBackgroundJobRequest(BaseModel):
    """Payload para recortar el fondo de una única imagen."""

    input_path: str
    strategy: Literal[
        "white_background",
        "color_background",
        "sam2_vitmatte",
        "isnet_general",
        "rembg_illustration",
        "birefnet_sam2_matte",
    ]


class RemoveBackgroundResultSchema(BaseModel):
    """Resultado de recortar el fondo de una imagen."""

    output_path: str
    image_url: str


class ScaleJobRequest(BaseModel):
    """Payload para escalar una única imagen con Real-ESRGAN."""

    input_path: str
    strategy: Literal["realesrgan"] = "realesrgan"
    width: int | None = None
    height: int | None = None


class ScaleResultSchema(BaseModel):
    """Resultado de escalar una imagen."""

    output_path: str
    image_url: str
    backend: str
    device: str
    scale_factor: float
    source_size: tuple[int, int]
    final_size: tuple[int, int]
    inference_ms: float
    warning: str | None = None


class ClearcutBatchInputSchema(BaseModel):
    """Fuente de entrada del batch de ClearCut: una carpeta o una lista explícita de archivos."""

    kind: Literal["folder", "files"]
    directory: str | None = None
    paths: list[str] | None = None


class ClearcutBatchJobRequest(BaseModel):
    """Payload para procesar un lote completo (recorte + escalado) de ClearCut."""

    input: ClearcutBatchInputSchema
    output_dir: str
    removal_strategy: Literal[
        "white_background",
        "color_background",
        "sam2_vitmatte",
        "isnet_general",
        "rembg_illustration",
        "birefnet_sam2_matte",
    ]
    scale_strategy: Literal["realesrgan"]
    factor: Literal[2, 4]


class ClearcutBatchItemResultSchema(BaseModel):
    """Resultado de un ítem individual del lote (refleja `BatchItemResult.to_dict()`)."""

    input: str | None
    output: str | None
    status: Literal["succeeded", "failed", "skipped"]
    error: str | None = None
    warning: str | None = None


class ClearcutBatchResultSchema(BaseModel):
    """Resultado completo del lote (refleja `BatchReport.to_dict()`)."""

    total: int
    succeeded: int
    failed: int
    skipped: int
    cancelled: bool
    items: list[ClearcutBatchItemResultSchema]


class SizeRowSchema(BaseModel):
    """Una fila de tamaño de un preset de exportación multi-tamaño."""

    label: str = Field(min_length=1)
    mode: Literal["px", "percent"]
    prefix: str = ""
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    percent: float | None = Field(default=None, gt=0)
    template: str | None = None


class MultiExportJobRequest(BaseModel):
    """Payload para exportar N imágenes contra una lista de tamaños, empaquetado en un zip."""

    image_paths: list[str] = Field(min_length=1)
    sizes: list[SizeRowSchema] = Field(min_length=1)
    output_name: str | None = None


class MultiExportItemResultSchema(BaseModel):
    """Resultado de una combinación (imagen, fila de tamaño) individual."""

    input: str | None
    size_label: str
    status: Literal["succeeded", "failed"]
    archive_member: str | None = None
    error: str | None = None


class MultiExportResultSchema(BaseModel):
    """Resultado completo de un job de exportación multi-tamaño."""

    zip_path: str
    zip_url: str
    expected: int
    produced: int
    items: list[MultiExportItemResultSchema]


# `JPG` y `JPEG` son el mismo codec (ver `convert_pipeline`); ambos se ofrecen en la UI.
ConvertTargetFormat = Literal["JPEG", "JPG", "PNG", "WEBP"]


class ConvertJobRequest(BaseModel):
    """Payload para convertir una única imagen a otro formato."""

    input_path: str
    target_format: ConvertTargetFormat
    quality: int = Field(default=90, ge=0, le=100)
    webp_lossless: bool = False


class ConvertResultSchema(BaseModel):
    """Resultado de convertir una imagen individual."""

    output_path: str
    image_url: str


class ConvertBatchJobRequest(BaseModel):
    """Payload para convertir N imágenes al mismo formato destino, empaquetadas en un zip."""

    image_paths: list[str] = Field(min_length=1)
    target_format: ConvertTargetFormat
    quality: int = Field(default=90, ge=0, le=100)
    webp_lossless: bool = False
    output_name: str | None = None


class ConvertBatchItemResultSchema(BaseModel):
    """Resultado de convertir una imagen individual del lote."""

    input: str | None
    status: Literal["succeeded", "failed"]
    archive_member: str | None = None
    error: str | None = None


class ConvertBatchResultSchema(BaseModel):
    """Resultado completo de una conversión en lote."""

    zip_path: str
    zip_url: str
    expected: int
    produced: int
    items: list[ConvertBatchItemResultSchema]


# ---------------------------------------------------------------------------
# Halftone (semitonos): nuevo en esta fase. Replica 1:1 las 10 opciones del
# Space `halftone-converter` (Gradio), con rangos/defaults idénticos. La
# resolución/DPI de salida son fijos (4500×5400 @300) y no se exponen acá.
# ---------------------------------------------------------------------------


HalftoneMethodLiteral = Literal["halftone", "diffusion"]
DotShapeLiteral = Literal["round", "line"]


class HalftoneParams(BaseModel):
    """Los 10 controles del Gradio original, con sus rangos/pasos/defaults exactos."""

    crop_black_background: bool = True
    crop_black_threshold: int = Field(default=25, ge=0, le=255)
    black_point: int = Field(default=16, ge=0, le=255)
    white_point: int = Field(default=100, ge=0, le=255)
    gamma: float = Field(default=1.0, ge=0.1, le=3.0)
    invert_for_dark_shirt: bool = False
    halftone_method: HalftoneMethodLiteral = "halftone"
    screen_frequency: int = Field(default=35, ge=5, le=100)
    screen_angle: float = Field(default=23.5, ge=0.0, le=90.0)
    dot_shape: DotShapeLiteral = "round"


class HalftoneJobRequest(HalftoneParams):
    """Payload para exportar el halftone full-res de una única imagen."""

    input_path: str


class HalftonePreviewRequest(HalftoneParams):
    """Payload para la previsualización rápida (baja resolución)."""

    input_path: str
    preview_max_side: int = Field(default=1080, ge=64, le=2048)


class HalftoneResultSchema(BaseModel):
    """Resultado de exportar un halftone: PNG RGBA transparente."""

    output_path: str
    image_url: str


class HalftonePreviewResponse(BaseModel):
    """Previsualización devuelta como data URL PNG (mismo patrón que `getImagePreview`)."""

    image_data_url: str
    width: int
    height: int


class JobStatusResponse(BaseModel):
    """Estado y, si terminó, resultado de un job."""

    id: str
    type: JobType
    status: JobStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: (
        BatchJobResultSchema
        | StickerResultSchema
        | RemoveBackgroundResultSchema
        | ScaleResultSchema
        | ClearcutBatchResultSchema
        | MultiExportResultSchema
        | ConvertResultSchema
        | ConvertBatchResultSchema
        | HalftoneResultSchema
        | None
    ) = None
    error: str | None = None


class ModelPathsPublicResponse(BaseModel):
    """Rutas locales a modelos ONNX de eliminación de fondo."""

    sam2_encoder_onnx: str | None = None
    sam2_decoder_onnx: str | None = None
    vitmatte_onnx: str | None = None
    isnet_general_onnx: str | None = None


class ModelPathsUpdateRequest(BaseModel):
    """Actualización parcial de rutas a modelos ONNX."""

    sam2_encoder_onnx: str | None = None
    sam2_decoder_onnx: str | None = None
    vitmatte_onnx: str | None = None
    isnet_general_onnx: str | None = None
    clear_sam2_encoder: bool = False
    clear_sam2_decoder: bool = False
    clear_vitmatte: bool = False
    clear_isnet_general: bool = False
