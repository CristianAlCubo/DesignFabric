"""Endpoints para previsualizar, exportar y preparar mockups de prendas."""

from __future__ import annotations

import base64
import binascii
import logging
import re
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from designfabric.api.dependencies import get_job_dispatcher, get_settings_dep
from designfabric.api.dispatcher import JobDispatcher
from designfabric.api.schemas import (
    JobCreatedResponse,
    MockupJobRequest,
    MockupCorners,
    MockupParams,
    MockupPreviewRequest,
    MockupPreviewResponse,
    MockupTemplateListResponse,
    MockupTemplatePrepareRequest,
    MockupTemplatePrepareResponse,
    MockupTemplateSummary,
    MockupTemplateUpdateRequest,
)
from designfabric.core.config import Settings
from designfabric.core.imaging.mockup.prepare import prepare_template, save_template
from designfabric.core.imaging.mockup.render import render_mockup
from designfabric.core.imaging.mockup.template import MockupRequest, MockupTemplate, load_template
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mockups", tags=["mockups"])

_TEMPLATE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
_COLOR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_TEMPLATE_CACHE: dict[tuple[str, str, int], MockupTemplate] = {}
_DATA_URL_PREFIX = "data:image/png;base64,"


@router.get("/templates", response_model=MockupTemplateListResponse)
def list_templates(settings: Settings = Depends(get_settings_dep)) -> MockupTemplateListResponse:
    """Lista las plantillas válidas, ordenadas por identificador."""
    templates_dir = Path(settings.mockup_templates_dir)
    summaries: list[MockupTemplateSummary] = []
    if templates_dir.is_dir():
        for template_dir in sorted(templates_dir.iterdir(), key=lambda item: item.name):
            if not template_dir.is_dir() or not _TEMPLATE_ID.fullmatch(template_dir.name):
                continue
            try:
                template = _get_template(settings, template_dir.name)
            except (FileNotFoundError, ValueError) as exc:
                logger.warning("Se omite plantilla de mockup inválida %s: %s", template_dir, exc)
                continue
            summaries.append(_template_summary(template))
    return MockupTemplateListResponse(templates=summaries)


@router.get("/templates/{template_id}/thumbnail")
def get_template_thumbnail(
    template_id: str,
    settings: Settings = Depends(get_settings_dep),
) -> FileResponse:
    """Sirve la fotografía base de la plantilla como miniatura."""
    template = _get_template_or_404(settings, template_id)
    return FileResponse(
        Path(settings.mockup_templates_dir) / template.id / "base.png",
        media_type="image/png",
        filename=f"{template.id}.png",
    )


@router.post("/preview", response_model=MockupPreviewResponse)
def mockup_preview(
    payload: MockupPreviewRequest,
    settings: Settings = Depends(get_settings_dep),
) -> MockupPreviewResponse:
    """Renderiza una previsualización síncrona con el mismo motor del export."""
    template = _get_template_or_404(settings, payload.template_id)
    request = _mockup_request(template, payload)
    design = _open_image(payload.design_path)
    try:
        preview = render_mockup(design, template, request, max_side=payload.max_side)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return MockupPreviewResponse(
        image_data_url=_image_data_url(preview),
        width=preview.width,
        height=preview.height,
        warnings=list(preview.info.get("warnings", ())),
    )


@router.post("", response_model=JobCreatedResponse, status_code=202)
def create_mockup_job(
    payload: MockupJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
    settings: Settings = Depends(get_settings_dep),
) -> JobCreatedResponse:
    """Encola un export full-res en el worker CPU."""
    template = _get_template_or_404(settings, payload.template_id)
    _mockup_request(template, payload)
    job = Job.new(JobType.MOCKUP, payload)
    dispatcher.submit(job)
    logger.info("Job %s encolado (mockup, template=%s)", job.id, payload.template_id)
    return JobCreatedResponse(job_id=job.id, status=job.status)


@router.post("/templates/prepare", response_model=MockupTemplatePrepareResponse)
def prepare_template_endpoint(
    payload: MockupTemplatePrepareRequest,
) -> MockupTemplatePrepareResponse:
    """Propone mapas editables desde una fotografía, sin guardarlos aún."""
    photo = _open_image(payload.photo_path)
    try:
        prepared = prepare_template(photo)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    corners = payload.corners or _suggest_corners(prepared.garment_mask)
    return MockupTemplatePrepareResponse(
        base_size=prepared.base.size,
        mask_data_url=_image_data_url(prepared.garment_mask),
        shading_data_url=_image_data_url(prepared.shading),
        displacement_data_url=_image_data_url(prepared.displacement),
        suggested_corners=corners,
    )


@router.put("/templates/{template_id}", response_model=MockupTemplateSummary)
def update_template(
    template_id: str,
    payload: MockupTemplateUpdateRequest,
    settings: Settings = Depends(get_settings_dep),
) -> MockupTemplateSummary:
    """Guarda una plantilla con mapas revisados y recalculados desde la foto."""
    if not _TEMPLATE_ID.fullmatch(template_id):
        raise HTTPException(status_code=422, detail="id debe cumplir ^[a-z0-9][a-z0-9-]{1,63}$")
    photo = _open_image(payload.photo_path)
    mask = _decode_mask(payload.mask_data_url) if payload.mask_data_url else None
    target_dir = Path(settings.mockup_templates_dir) / template_id
    try:
        template = save_template(
            target_dir,
            photo,
            template_id=template_id,
            name=payload.name,
            corners=payload.corners,
            px_per_cm=payload.px_per_cm,
            max_print_cm=payload.max_print_cm,
            default_anchor=payload.default_anchor,
            displacement_strength_px=payload.displacement_strength_px,
            shading_strength=payload.shading_strength,
            highlight_strength=payload.highlight_strength,
            garment_colors=payload.garment_colors or None,
            dark_garment_colors=tuple(payload.dark_garment_colors),
            mask=mask,
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _invalidate_template_cache(template_id)
    return _template_summary(template)


def build_handlers(settings: Settings, store: JobStore) -> dict[JobType, Any]:
    """Construye el handler CPU que guarda PNG en `output/mockups`."""
    output_dir = Path(settings.output_dir) / "mockups"

    def handle(payload: MockupJobRequest, reporter: WebSocketProgressReporter) -> dict[str, str]:
        template = _get_template_or_404(settings, payload.template_id)
        request = _mockup_request(template, payload)
        design = _open_image(payload.design_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{uuid.uuid4().hex}.png"
        try:
            result = render_mockup(design, template, request)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        result.save(output_path, format="PNG", dpi=result.info.get("dpi"))
        return {"output_path": str(output_path)}

    return {JobType.MOCKUP: handle}


def _get_template(settings: Settings, template_id: str) -> MockupTemplate:
    if not _TEMPLATE_ID.fullmatch(template_id):
        raise ValueError("Identificador de plantilla inválido")
    template_dir = Path(settings.mockup_templates_dir) / template_id
    metadata_path = template_dir / "template.json"
    try:
        modified_ns = metadata_path.stat().st_mtime_ns
    except OSError as exc:
        raise FileNotFoundError(template_id) from exc
    cache_key = (str(template_dir.resolve()), template_id, modified_ns)
    cached = _TEMPLATE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        template = load_template(template_dir)
    except ValueError:
        raise
    if template.id != template_id:
        raise ValueError("El id de template.json no coincide con el directorio")
    _TEMPLATE_CACHE[cache_key] = template
    return template


def _get_template_or_404(settings: Settings, template_id: str) -> MockupTemplate:
    if not _TEMPLATE_ID.fullmatch(template_id):
        raise HTTPException(status_code=404, detail="Plantilla de mockup inexistente")
    try:
        return _get_template(settings, template_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Plantilla de mockup inexistente") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Plantilla inválida: {exc}") from exc


def _invalidate_template_cache(template_id: str) -> None:
    for key in tuple(_TEMPLATE_CACHE):
        if key[1] == template_id:
            del _TEMPLATE_CACHE[key]


def _template_summary(template: MockupTemplate) -> MockupTemplateSummary:
    return MockupTemplateSummary(
        id=template.id,
        name=template.name,
        thumbnail_url=f"/api/mockups/templates/{template.id}/thumbnail",
        garment_colors=dict(template.garment_colors),
        max_print_cm=template.max_print_cm,
        px_per_cm=template.px_per_cm,
        base_size=template.base_size,
    )


def _mockup_request(template: MockupTemplate, payload: MockupParams) -> MockupRequest:
    color = payload.garment_color
    if color not in template.garment_colors and not _COLOR_HEX.fullmatch(color):
        raise HTTPException(status_code=422, detail="Color de prenda desconocido o hexadecimal inválido")
    if payload.print_width_cm <= 0:
        raise HTTPException(status_code=422, detail="print_width_cm debe ser mayor que cero")
    try:
        return MockupRequest(
            garment_color=color,
            print_width_cm=payload.print_width_cm,
            offset_cm=payload.offset_cm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _open_image(path: str) -> Image.Image:
    try:
        with Image.open(path) as image:
            image.load()
            return image.copy()
    except (OSError, UnidentifiedImageError) as exc:
        raise HTTPException(status_code=422, detail=f"No se pudo leer la imagen: {exc}") from exc


def _image_data_url(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"{_DATA_URL_PREFIX}{encoded}"


def _decode_mask(data_url: str) -> Image.Image:
    if not data_url.startswith(_DATA_URL_PREFIX):
        raise HTTPException(status_code=422, detail="mask_data_url debe ser un PNG en data URL")
    try:
        raw = base64.b64decode(data_url[len(_DATA_URL_PREFIX) :], validate=True)
        with Image.open(BytesIO(raw)) as image:
            if image.format != "PNG" or image.mode != "L":
                raise ValueError("La máscara debe ser un PNG de un canal L")
            image.load()
            return image.copy()
    except (binascii.Error, OSError, UnidentifiedImageError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Máscara inválida: {exc}") from exc


def _suggest_corners(mask: Image.Image) -> MockupCorners:
    bounds = mask.getbbox()
    if bounds is None:
        raise HTTPException(status_code=422, detail="La máscara propuesta está vacía")
    left, top, right, bottom = bounds
    return (
        (float(left), float(top)),
        (float(right - 1), float(top)),
        (float(right - 1), float(bottom - 1)),
        (float(left), float(bottom - 1)),
    )
