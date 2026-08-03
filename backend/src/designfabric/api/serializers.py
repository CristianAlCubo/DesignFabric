"""Conversión de modelos internos (dataclasses de dominio/jobs) a schemas pydantic públicos."""

from __future__ import annotations

import os

from designfabric.api.schemas import (
    BatchJobResultSchema,
    ClearcutBatchItemResultSchema,
    ClearcutBatchResultSchema,
    ConvertBatchItemResultSchema,
    ConvertBatchResultSchema,
    ConvertResultSchema,
    JobStatusResponse,
    MultiExportItemResultSchema,
    MultiExportResultSchema,
    RemoveBackgroundResultSchema,
    ScaleResultSchema,
    StickerResultSchema,
)
from designfabric.core.config import Settings
from designfabric.jobs.models import Job, JobType

try:
    # `pipeline.py`/`sticker_generator.py` importan torch/diffusers/langchain a
    # nivel de módulo: sin el extra `local-ai` instalado, se usan sentinels que
    # no matchean nunca ningún `isinstance` de abajo (nunca podría haber un
    # `job.result` de estos tipos si esas features no llegaron a registrarse).
    from designfabric.core.generation.pipeline import BatchResult
    from designfabric.core.generation.sticker_generator import StickerResult
except ImportError:

    class BatchResult:  # type: ignore[no-redef]
        pass

    class StickerResult:  # type: ignore[no-redef]
        pass


def _image_url(filename: str | None, settings: Settings) -> str | None:
    """Convierte una ruta de archivo en disco a la URL servida por el mount `/output`."""
    if filename is None:
        return None
    relative = os.path.relpath(filename, settings.output_dir)
    return f"/output/{relative}"


def sticker_result_to_schema(result: StickerResult, settings: Settings) -> StickerResultSchema:
    return StickerResultSchema(
        prompt=result.prompt,
        filename=result.filename,
        image_url=_image_url(result.filename, settings),
        success=result.success,
        error=result.error,
    )


def job_to_schema(job: Job, settings: Settings) -> JobStatusResponse:
    """Serializa un `Job` (incluyendo su resultado, si terminó) a la respuesta pública del API.

    Cada handler de feature (ver `api/routers/*.py`) devuelve un `dict`
    schema-friendly con los campos mínimos necesarios para construir la
    sub-schema de resultado correspondiente — el `match`/`if` de acá solo
    necesita saber el `job.type` para elegir qué schema construir, sin
    importar tipos concretos de cada feature (salvo los de generación IA,
    que siguen devolviendo sus dataclasses de dominio tal cual, heredado de
    DesignFabric).
    """
    result_schema: (
        BatchJobResultSchema
        | StickerResultSchema
        | RemoveBackgroundResultSchema
        | ScaleResultSchema
        | ClearcutBatchResultSchema
        | MultiExportResultSchema
        | ConvertResultSchema
        | ConvertBatchResultSchema
        | None
    ) = None

    if isinstance(job.result, BatchResult):
        result_schema = BatchJobResultSchema(
            prompts=job.result.prompts,
            results=[sticker_result_to_schema(r, settings) for r in job.result.results],
            failure_count=job.result.failure_count,
            cancelled=job.result.cancelled,
        )
    elif isinstance(job.result, StickerResult):
        result_schema = sticker_result_to_schema(job.result, settings)
    elif job.result is not None and job.type is JobType.REMOVE_BACKGROUND:
        result_schema = RemoveBackgroundResultSchema(
            output_path=job.result["output_path"],
            image_url=_image_url(job.result["output_path"], settings),
        )
    elif job.result is not None and job.type is JobType.SCALE:
        result_schema = ScaleResultSchema(
            output_path=job.result["output_path"],
            image_url=_image_url(job.result["output_path"], settings),
            backend=job.result["backend"],
            device=job.result["device"],
            scale_factor=job.result["scale_factor"],
            source_size=job.result["source_size"],
            final_size=job.result["final_size"],
            inference_ms=job.result["inference_ms"],
            warning=job.result.get("warning"),
        )
    elif job.result is not None and job.type is JobType.CLEARCUT_BATCH:
        result_schema = ClearcutBatchResultSchema(
            total=job.result["total"],
            succeeded=job.result["succeeded"],
            failed=job.result["failed"],
            skipped=job.result["skipped"],
            cancelled=job.result["cancelled"],
            items=[ClearcutBatchItemResultSchema(**item) for item in job.result["items"]],
        )
    elif job.result is not None and job.type is JobType.MULTI_EXPORT:
        zip_path = job.result["zip_path"]
        result_schema = MultiExportResultSchema(
            zip_path=zip_path,
            zip_url=_image_url(zip_path, settings) or "",
            expected=job.result["expected"],
            produced=job.result["produced"],
            items=[MultiExportItemResultSchema(**item) for item in job.result["items"]],
        )
    elif job.result is not None and job.type is JobType.CONVERT:
        # Un mismo JobType.CONVERT cubre individual (dict con `output_path`) y lote
        # (dict con `zip_path`): la forma del dict de resultado distingue ambos modos.
        if "zip_path" in job.result:
            convert_zip = job.result["zip_path"]
            result_schema = ConvertBatchResultSchema(
                zip_path=convert_zip,
                zip_url=_image_url(convert_zip, settings) or "",
                expected=job.result["expected"],
                produced=job.result["produced"],
                items=[ConvertBatchItemResultSchema(**item) for item in job.result["items"]],
            )
        else:
            result_schema = ConvertResultSchema(
                output_path=job.result["output_path"],
                image_url=_image_url(job.result["output_path"], settings) or "",
            )

    return JobStatusResponse(
        id=job.id,
        type=job.type,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        result=result_schema,
        error=job.error,
    )
