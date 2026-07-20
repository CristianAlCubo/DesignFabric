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
    llm_provider: Literal["ollama", "test"] = Field(
        default="ollama", description="Provider primitivo de texto para generar conceptos"
    )
    image_provider: Literal["flux", "test"] = Field(
        default="flux", description="Provider primitivo de imagen para renderizar prompts"
    )


class SingleImageJobRequest(BaseModel):
    """Payload para generar una única imagen a partir de un prompt escrito por el usuario."""

    prompt: str = Field(min_length=1, max_length=2000, description="Prompt libre en inglés para Flux")
    apply_style_suffix: bool = Field(
        default=True, description="Si se concatena el STYLE_SUFFIX de sticker al prompt del usuario"
    )
    image_provider: Literal["flux", "test"] = Field(
        default="flux", description="Provider primitivo de imagen para renderizar el prompt"
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


class GenerationReadinessResponse(BaseModel):
    """Fuente de verdad de readiness de generación IA (solo reporte)."""

    local_ai: LocalAiStatusSchema
    ollama: OllamaStatusSchema
    flux: FluxStatusSchema
    cuda: CudaStatusSchema
    providers: ProviderReadinessSchema


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


# ---------------------------------------------------------------------------
# ClearCut (eliminación de fondo / escalado / batch): nuevos en esta fase.
# ---------------------------------------------------------------------------


class RemoveBackgroundJobRequest(BaseModel):
    """Payload para recortar el fondo de una única imagen."""

    input_path: str
    strategy: Literal["white_background", "color_background"]


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
    removal_strategy: Literal["white_background", "color_background"]
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
        | None
    ) = None
    error: str | None = None
