"""Verificación de dependencias y descarga de modelos de escalado IA."""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from designfabric.core.imaging.upscale_config import UpscaleConfig, load_upscale_config

logger = logging.getLogger(__name__)

_USER_AGENT = "ClearCut/0.1 (model-assets; +https://github.com/)"

# URLs estables (primera = preferida; el resto son mirrors de respaldo).
_MODEL_URLS: dict[str, tuple[str, ...]] = {
    "realesrgan": (
        "https://huggingface.co/Heliosoph/realesrgan-onnx/resolve/main/"
        "realesr-general-x4v3.onnx?download=true",
        "https://hf-mirror.com/Heliosoph/realesrgan-onnx/resolve/main/"
        "realesr-general-x4v3.onnx?download=true",
    ),
    # SPAN desactivado — URLs conservadas por si se reactiva:
    # "span_x2": (...),
    # "span_x4": (...),
}


Downloader = Callable[[str, Path], None]


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class ModelStatus:
    key: str
    filename: str
    path: str
    present: bool
    downloaded: bool = False
    error: str | None = None


@dataclass(frozen=True)
class EnsureModelsReport:
    models_dir: str
    dependencies: list[DependencyStatus] = field(default_factory=list)
    models: list[ModelStatus] = field(default_factory=list)
    ready_realesrgan: bool = False
    ready_span: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "models_dir": self.models_dir,
            "dependencies": [asdict(item) for item in self.dependencies],
            "models": [asdict(item) for item in self.models],
            "ready_realesrgan": self.ready_realesrgan,
            "ready_span": self.ready_span,
            "warnings": list(self.warnings),
        }


class ModelAssetError(Exception):
    """Error al preparar modelos o dependencias de escalado."""


def check_dependencies() -> list[DependencyStatus]:
    """Comprueba imports necesarios para los backends de IA."""
    statuses: list[DependencyStatus] = []

    if importlib.util.find_spec("onnxruntime") is not None:
        statuses.append(
            DependencyStatus("onnxruntime", True, "Disponible para Real-ESRGAN (CPU).")
        )
    else:
        statuses.append(
            DependencyStatus(
                "onnxruntime",
                False,
                "No instalado. Ejecuta `uv sync` (incluido en dependencias base).",
            )
        )

    return statuses


def default_download(url: str, dest: Path) -> None:
    """Descarga un archivo a `dest` de forma atómica."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()
    except urllib.error.URLError as exc:
        raise ModelAssetError(f"No se pudo descargar {url}: {exc}") from exc

    if not data:
        raise ModelAssetError(f"Descarga vacía desde {url}")

    tmp.write_bytes(data)
    tmp.replace(dest)


def _download_with_mirrors(urls: tuple[str, ...], dest: Path, fetch: Downloader) -> None:
    errors: list[str] = []
    for url in urls:
        try:
            fetch(url, dest)
            if dest.is_file() and dest.stat().st_size > 0:
                return
            errors.append(f"{url}: archivo vacío")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {exc}")
    raise ModelAssetError("Todas las URLs fallaron: " + " | ".join(errors))


def ensure_models(
    *,
    config: UpscaleConfig | None = None,
    project_root: Path | None = None,
    download: bool = True,
    keys: set[str] | None = None,
    downloader: Downloader | None = None,
) -> EnsureModelsReport:
    """Verifica deps y asegura que los pesos locales existan (descarga si falta)."""
    cfg = config or load_upscale_config()
    models_dir = cfg.models_path(project_root)
    models_dir.mkdir(parents=True, exist_ok=True)
    fetch = downloader or default_download
    wanted = keys or set(_MODEL_URLS)
    if os.environ.get("CLEARCUT_SKIP_MODEL_DOWNLOAD") == "1":
        download = False

    filename_by_key = {
        "realesrgan": cfg.realesrgan_model,
    }

    dependencies = check_dependencies()
    model_statuses: list[ModelStatus] = []
    warnings: list[str] = []

    for key in ("realesrgan",):
        if key not in wanted:
            continue
        filename = filename_by_key[key]
        path = models_dir / filename
        present = path.is_file() and path.stat().st_size > 0
        downloaded = False
        error: str | None = None

        if not present and download:
            urls = _MODEL_URLS[key]
            logger.info("Descargando modelo %s -> %s", key, path)
            try:
                _download_with_mirrors(urls, path, fetch)
                present = path.is_file() and path.stat().st_size > 0
                downloaded = present
                if not present:
                    error = "La descarga no produjo un archivo válido."
            except Exception as exc:  # noqa: BLE001 — reportar sin abortar el resto
                error = str(exc)
                warnings.append(f"{key}: {error}")
                logger.warning("No se pudo preparar el modelo %s: %s", key, exc)
        elif not present:
            error = "Ausente (descarga desactivada)."
            warnings.append(f"{key}: {error}")

        model_statuses.append(
            ModelStatus(
                key=key,
                filename=filename,
                path=str(path),
                present=present,
                downloaded=downloaded,
                error=error,
            )
        )

    dep_by_name = {item.name: item for item in dependencies}
    onnx_ok = dep_by_name.get("onnxruntime", DependencyStatus("onnxruntime", False, "")).ok
    present_by_key = {m.key: m.present for m in model_statuses}
    realesrgan_model_ok = present_by_key.get("realesrgan", False)
    want_realesrgan = "realesrgan" in wanted

    if want_realesrgan and not onnx_ok:
        warnings.append("Real-ESRGAN no listo: falta onnxruntime (`uv sync`).")
    if want_realesrgan and not realesrgan_model_ok:
        warnings.append("Real-ESRGAN no listo: falta el modelo ONNX.")

    return EnsureModelsReport(
        models_dir=str(models_dir),
        dependencies=dependencies,
        models=model_statuses,
        ready_realesrgan=onnx_ok and realesrgan_model_ok if want_realesrgan else False,
        ready_span=False,
        warnings=warnings,
    )


def ensure_models_for_strategy(
    strategy: str,
    *,
    config: UpscaleConfig | None = None,
    project_root: Path | None = None,
) -> EnsureModelsReport:
    """Prepara solo los modelos relevantes para una estrategia."""
    if strategy == "vector":
        return EnsureModelsReport(
            models_dir=str((config or load_upscale_config()).models_path(project_root)),
            dependencies=check_dependencies(),
            ready_realesrgan=False,
            ready_span=False,
        )
    return ensure_models(
        config=config,
        project_root=project_root,
        keys={"realesrgan"},
    )


def report_to_json(report: EnsureModelsReport) -> str:
    return json.dumps(report.to_dict(), indent=2) + "\n"
