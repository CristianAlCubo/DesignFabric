"""Configuración del pipeline de escalado (backends, modelos, límites)."""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class UpscaleConfig:
    """Parámetros configurables del escalado multi-estrategia."""

    gpu_backend: str = "realesrgan"  # SPAN desactivado; se ignora en auto
    cpu_backend: str = "realesrgan"
    models_dir: str = ".local/models"
    max_image_side: int = 4096
    max_scale_factor: int = 4
    realesrgan_model: str = "realesr-general-x4v3.onnx"
    # Conservados por compatibilidad con clearcut.toml antiguos (no se usan):
    span_x2_model: str = "spanx2_ch48.pth"
    span_x4_model: str = "spanx4_ch48.pth"

    def models_path(self, project_root: Path | None = None) -> Path:
        env_dir = os.environ.get("CLEARCUT_MODELS_DIR")
        if env_dir:
            return Path(env_dir).expanduser().resolve()
        base = Path(self.models_dir)
        if base.is_absolute():
            return base
        root = project_root or Path.cwd()
        return (root / base).resolve()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_DEFAULT = UpscaleConfig()


def _config_path() -> Path | None:
    env = os.environ.get("CLEARCUT_CONFIG")
    if env:
        path = Path(env)
        return path if path.is_file() else None

    cwd_candidate = Path.cwd() / "clearcut.toml"
    if cwd_candidate.is_file():
        return cwd_candidate

    return None


def load_upscale_config(path: Path | None = None) -> UpscaleConfig:
    """Carga UpscaleConfig desde TOML o devuelve defaults."""
    config_file = path or _config_path()
    if config_file is None:
        return _DEFAULT

    with config_file.open("rb") as fh:
        data = tomllib.load(fh)

    section = data.get("upscale", data)
    known = {f.name for f in UpscaleConfig.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    kwargs = {key: value for key, value in section.items() if key in known}
    return UpscaleConfig(**{**asdict(_DEFAULT), **kwargs})
