"""Motor de escalado profesional: vectorización VTracer + rasterización CairoSVG."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cairosvg  # type: ignore[import-untyped]
import vtracer  # type: ignore[import-untyped]

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_SVG_SIZE_RE = re.compile(
    r'width="(?P<width>[\d.]+)(?:px)?"[^>]*height="(?P<height>[\d.]+)(?:px)?"'
    r"|height=\"(?P<height2>[\d.]+)(?:px)?\"[^>]*width=\"(?P<width2>[\d.]+)(?:px)?\"",
    re.IGNORECASE,
)
_REFERENCE_DPI = 96.0


class VectorEngineError(Exception):
    """Error en el pipeline de escalado vectorial."""


@dataclass(frozen=True)
class TraceConfig:
    """Parámetros de trazado VTracer 0.6.15."""

    colormode: str = "color"
    hierarchical: str = "stacked"
    mode: str = "spline"
    filter_speckle: int = 4
    color_precision: int = 6
    layer_difference: int = 16
    corner_threshold: int = 60
    length_threshold: float = 4.0
    max_iterations: int = 10
    splice_threshold: int = 45
    path_precision: int = 8

    def validated(self) -> TraceConfig:
        if self.colormode not in ("color", "binary"):
            raise VectorEngineError(f"colormode inválido: {self.colormode}")
        if self.hierarchical not in ("stacked", "cutout"):
            raise VectorEngineError(f"hierarchical inválido: {self.hierarchical}")
        if self.mode not in ("spline", "polygon", "none"):
            raise VectorEngineError(f"mode inválido: {self.mode}")
        if not (3.5 <= self.length_threshold <= 10.0):
            raise VectorEngineError(
                f"length_threshold fuera de rango [3.5, 10]: {self.length_threshold}"
            )
        if self.filter_speckle < 0:
            raise VectorEngineError("filter_speckle debe ser >= 0")
        if self.color_precision < 1:
            raise VectorEngineError("color_precision debe ser >= 1")
        if self.corner_threshold < 0:
            raise VectorEngineError("corner_threshold debe ser >= 0")
        if self.max_iterations < 1:
            raise VectorEngineError("max_iterations debe ser >= 1")
        return self


@dataclass(frozen=True)
class ExportConfig:
    """Resolución de exportación del PNG final."""

    width_px: int | None = None
    height_px: int | None = None
    dpi: float = 300.0

    def validated(self) -> ExportConfig:
        if self.dpi <= 0:
            raise VectorEngineError(f"dpi debe ser > 0: {self.dpi}")
        if self.width_px is not None and self.width_px <= 0:
            raise VectorEngineError(f"width_px debe ser > 0: {self.width_px}")
        if self.height_px is not None and self.height_px <= 0:
            raise VectorEngineError(f"height_px debe ser > 0: {self.height_px}")
        return self


def get_scale_defaults() -> dict[str, Any]:
    """Defaults de TraceConfig + ExportConfig para hidratar UI/bridge."""
    return {
        "dpi": ExportConfig().dpi,
        "trace": asdict(TraceConfig()),
    }


def _parse_svg_size(svg: str) -> tuple[float, float]:
    match = _SVG_SIZE_RE.search(svg)
    if match is None:
        raise VectorEngineError("No se pudieron leer width/height del SVG generado.")
    width = match.group("width") or match.group("width2")
    height = match.group("height") or match.group("height2")
    if width is None or height is None:
        raise VectorEngineError("SVG sin dimensiones válidas.")
    return float(width), float(height)


def _resolve_output_size(svg: str, export: ExportConfig) -> tuple[int | None, int | None]:
    if export.width_px is not None or export.height_px is not None:
        return export.width_px, export.height_px

    width, height = _parse_svg_size(svg)
    scale = export.dpi / _REFERENCE_DPI
    return max(1, round(width * scale)), max(1, round(height * scale))


class VectorEngine:
    """Vectoriza un PNG en memoria con VTracer y lo rasteriza a alta resolución."""

    def __init__(self, trace: TraceConfig | None = None) -> None:
        self._trace = (trace or TraceConfig()).validated()

    def vectorize(self, png_bytes: bytes) -> str:
        if not png_bytes.startswith(_PNG_SIGNATURE):
            raise VectorEngineError("La entrada debe ser un PNG válido.")

        try:
            svg = vtracer.convert_raw_image_to_svg(
                png_bytes,
                img_format="png",
                colormode=self._trace.colormode,
                hierarchical=self._trace.hierarchical,
                mode=self._trace.mode,
                filter_speckle=self._trace.filter_speckle,
                color_precision=self._trace.color_precision,
                layer_difference=self._trace.layer_difference,
                corner_threshold=self._trace.corner_threshold,
                length_threshold=self._trace.length_threshold,
                max_iterations=self._trace.max_iterations,
                splice_threshold=self._trace.splice_threshold,
                path_precision=self._trace.path_precision,
            )
        except Exception as exc:  # noqa: BLE001 — API nativa de VTracer
            raise VectorEngineError(f"Falló la vectorización VTracer: {exc}") from exc

        if not isinstance(svg, str) or not svg.strip():
            raise VectorEngineError("VTracer devolvió un SVG vacío.")
        return svg

    def rasterize(self, svg: str, export: ExportConfig) -> bytes:
        export = export.validated()
        width_px, height_px = _resolve_output_size(svg, export)

        try:
            png_bytes = cairosvg.svg2png(
                bytestring=svg.encode("utf-8"),
                dpi=export.dpi,
                output_width=width_px,
                output_height=height_px,
            )
        except Exception as exc:  # noqa: BLE001 — API de CairoSVG
            raise VectorEngineError(f"Falló la rasterización CairoSVG: {exc}") from exc

        if not isinstance(png_bytes, (bytes, bytearray)) or not png_bytes:
            raise VectorEngineError("CairoSVG no produjo un PNG válido.")
        return bytes(png_bytes)

    def process(self, png_bytes: bytes, export: ExportConfig) -> bytes:
        svg = self.vectorize(png_bytes)
        try:
            return self.rasterize(svg, export)
        finally:
            del svg


def scale_image(
    input_path: Path,
    output_path: Path,
    *,
    trace: TraceConfig | None = None,
    export: ExportConfig | None = None,
) -> Path:
    """Lee un PNG, escala vía VectorEngine y escribe el PNG de salida una sola vez."""
    path = Path(input_path)
    if not path.is_file():
        raise VectorEngineError(f"No existe el archivo de entrada: {path}")
    if path.suffix.lower() != ".png":
        raise VectorEngineError("El escalado profesional requiere un PNG de entrada.")

    png_bytes = path.read_bytes()
    engine = VectorEngine(trace)
    result = engine.process(png_bytes, export or ExportConfig())

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(result)
    return out
