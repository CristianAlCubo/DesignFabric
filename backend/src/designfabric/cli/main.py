"""CLIs standalone conservados de la fusión: `clearcut` (eliminación de fondo
y escalado) y `designfabric` (generación de stickers vía Ollama + FLUX.2).

Ambos siguen funcionando de forma independiente a la app de escritorio
Electron y al backend FastAPI — son wrappers delgados sobre las mismas
funciones de `core/imaging` y `core/generation` que usan los routers HTTP,
útiles para debugging/uso por script. Registrados en `[project.scripts]`
de `pyproject.toml` como `clearcut = "designfabric.cli.main:clearcut_cli"`
y `designfabric = "designfabric.cli.main:designfabric_cli"`.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from pathlib import Path

from designfabric.core.config import get_settings
from designfabric.core.imaging.background_remover import RemovalConfig, process_image
from designfabric.core.imaging.batch import (
    BatchConfig,
    create_input_source,
    create_output_target,
    emit_item_line,
    emit_progress_line,
    run_batch as run_clearcut_batch,
)
from designfabric.core.imaging.model_assets import ensure_models, report_to_json
from designfabric.core.imaging.silhouette_strategies import StrategyName, create_silhouette_strategy
from designfabric.core.imaging.upscale_pipeline import WARNING_PREFIX, get_scale_defaults, scale_image
from designfabric.core.imaging.upscale_strategies import UpscaleError, UpscaleStrategyName
from designfabric.core.imaging.vector_engine import ExportConfig, TraceConfig, VectorEngineError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# `clearcut` — eliminación de fondo, escalado y batch (ex ClearCut CLI)
# ---------------------------------------------------------------------------


def _add_remove_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "remove",
        help="Elimina el fondo de una ilustración y guarda un PNG RGBA.",
    )
    parser.add_argument("--input", type=Path, required=True, help="Ruta de la imagen de entrada.")
    parser.add_argument("--output", type=Path, required=True, help="Ruta del PNG de salida.")
    parser.add_argument(
        "--strategy",
        choices=("white_background", "color_background"),
        default="white_background",
        help="Estrategia de detección de silueta (default: white_background).",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Máximo de erosiones iterativas sobre la máscara (default: 5).",
    )
    parser.set_defaults(handler=_handle_remove)


def _add_scale_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "scale",
        help="Escala un PNG/SVG con la estrategia seleccionada (vectorial o IA).",
    )
    parser.add_argument("--input", type=Path, required=True, help="Ruta del PNG o SVG de entrada.")
    parser.add_argument("--output", type=Path, required=True, help="Ruta del PNG de salida.")
    parser.add_argument(
        "--strategy",
        choices=("vector", "realesrgan"),
        default="realesrgan",
        help="Estrategia de escalado (default: realesrgan).",
    )
    parser.add_argument("--width", type=int, default=None, help="Ancho de salida en píxeles.")
    parser.add_argument("--height", type=int, default=None, help="Alto de salida en píxeles.")
    parser.add_argument("--dpi", type=float, default=ExportConfig().dpi, help="DPI de exportación.")
    defaults = TraceConfig()
    parser.add_argument("--colormode", choices=("color", "binary"), default=defaults.colormode)
    parser.add_argument("--hierarchical", choices=("stacked", "cutout"), default=defaults.hierarchical)
    parser.add_argument("--mode", choices=("spline", "polygon", "none"), default=defaults.mode)
    parser.add_argument("--filter-speckle", type=int, default=defaults.filter_speckle)
    parser.add_argument("--color-precision", type=int, default=defaults.color_precision)
    parser.add_argument("--layer-difference", type=int, default=defaults.layer_difference)
    parser.add_argument("--corner-threshold", type=int, default=defaults.corner_threshold)
    parser.add_argument("--length-threshold", type=float, default=defaults.length_threshold)
    parser.add_argument("--trace-max-iterations", type=int, default=defaults.max_iterations)
    parser.add_argument("--splice-threshold", type=int, default=defaults.splice_threshold)
    parser.add_argument("--path-precision", type=int, default=defaults.path_precision)
    parser.set_defaults(handler=_handle_scale)


def _add_scale_defaults_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "scale-defaults",
        help="Imprime en JSON los defaults de escalado (estrategias, TraceConfig, DPI).",
    )
    parser.set_defaults(handler=_handle_scale_defaults)


def _add_ensure_models_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "ensure-models",
        help="Verifica dependencias de IA y descarga modelos faltantes a models_dir.",
    )
    parser.add_argument("--no-download", action="store_true", help="Solo verifica; no descarga archivos.")
    parser.set_defaults(handler=_handle_ensure_models)


def _add_batch_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "batch",
        help="Procesa un lote: recorte + escalado con configuración uniforme.",
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input-dir", type=Path, help="Carpeta con imágenes a procesar (sin recursión).")
    input_group.add_argument("--inputs", type=Path, nargs="+", help="Lista explícita de archivos a procesar.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Carpeta donde se escribirán los PNG generados.")
    parser.add_argument(
        "--removal-strategy",
        choices=("white_background", "color_background"),
        default="white_background",
        help="Estrategia de recorte (default: white_background).",
    )
    parser.add_argument(
        "--scale-strategy",
        choices=("vector", "realesrgan"),
        default="realesrgan",
        help="Estrategia de escalado (default: realesrgan).",
    )
    parser.add_argument("--factor", type=int, choices=(2, 4), default=2, help="Factor de escalado 2x o 4x (default: 2).")
    parser.add_argument(
        "--max-iterations", type=int, default=5, help="Máximo de erosiones iterativas sobre la máscara (default: 5)."
    )
    parser.set_defaults(handler=_handle_batch)


def _build_clearcut_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ClearCut: eliminación de fondo y escalado profesional para DTF.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_remove_parser(subparsers)
    _add_scale_parser(subparsers)
    _add_scale_defaults_parser(subparsers)
    _add_ensure_models_parser(subparsers)
    _add_batch_parser(subparsers)
    return parser


def _handle_remove(args: argparse.Namespace) -> None:
    strategy_name: StrategyName = args.strategy
    strategy = create_silhouette_strategy(strategy_name)
    config = RemovalConfig(max_iterations=args.max_iterations)

    logger.info("Procesando %s -> %s (strategy=%s)", args.input, args.output, strategy_name)
    process_image(args.input, args.output, strategy, config)
    logger.info("Listo: %s", args.output)


def _handle_scale(args: argparse.Namespace) -> None:
    strategy_name: UpscaleStrategyName = args.strategy
    trace = TraceConfig(
        colormode=args.colormode,
        hierarchical=args.hierarchical,
        mode=args.mode,
        filter_speckle=args.filter_speckle,
        color_precision=args.color_precision,
        layer_difference=args.layer_difference,
        corner_threshold=args.corner_threshold,
        length_threshold=args.length_threshold,
        max_iterations=args.trace_max_iterations,
        splice_threshold=args.splice_threshold,
        path_precision=args.path_precision,
    )
    export = ExportConfig(width_px=args.width, height_px=args.height, dpi=args.dpi)

    logger.info(
        "Escalando %s -> %s (strategy=%s width=%s height=%s dpi=%s)",
        args.input,
        args.output,
        strategy_name,
        args.width,
        args.height,
        args.dpi,
    )
    try:
        outcome = scale_image(args.input, args.output, strategy=strategy_name, trace=trace, export=export)
    except (UpscaleError, VectorEngineError) as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc

    if outcome.result.warning:
        sys.stderr.write(f"{WARNING_PREFIX}{outcome.result.warning}\n")
    logger.info("Listo: %s", args.output)


def _handle_scale_defaults(_args: argparse.Namespace) -> None:
    json.dump(get_scale_defaults(), sys.stdout, indent=2)
    sys.stdout.write("\n")


def _handle_ensure_models(args: argparse.Namespace) -> None:
    report = ensure_models(download=not args.no_download)
    sys.stdout.write(report_to_json(report))
    if not report.ready_realesrgan:
        for warning in report.warnings:
            logger.warning("%s", warning)


def _handle_batch(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error("No se pudo usar la carpeta de salida %s: %s", output_dir, exc)
        raise SystemExit(1) from exc

    if not output_dir.is_dir():
        logger.error("La ruta de salida no es una carpeta: %s", output_dir)
        raise SystemExit(1)

    try:
        if args.input_dir is not None:
            source = create_input_source("folder", directory=Path(args.input_dir))
        else:
            source = create_input_source("files", paths=list(args.inputs))
        target = create_output_target("directory", directory=output_dir)
    except (FileNotFoundError, ValueError, OSError) as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc

    config = BatchConfig(
        removal_strategy=args.removal_strategy,
        scale_strategy=args.scale_strategy,
        scale_factor=args.factor,
        removal=RemovalConfig(max_iterations=args.max_iterations),
    )

    logger.info(
        "Batch: removal=%s scale=%s factor=%sx -> %s",
        config.removal_strategy,
        config.scale_strategy,
        config.scale_factor,
        output_dir,
    )

    cancel_requested = False

    def _request_cancel(_signum: int, _frame: object) -> None:
        nonlocal cancel_requested
        cancel_requested = True
        logger.info("Cancelación solicitada; se detendrá entre archivos.")

    previous_sigint = signal.getsignal(signal.SIGINT)
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, _request_cancel)
    signal.signal(signal.SIGTERM, _request_cancel)

    try:
        report = run_clearcut_batch(
            config,
            source,
            target,
            on_progress=emit_progress_line,
            on_item=emit_item_line,
            should_cancel=lambda: cancel_requested,
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)

    json.dump(report.to_dict(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    logger.info(
        "Batch listo: total=%s succeeded=%s failed=%s skipped=%s cancelled=%s",
        report.total,
        report.succeeded,
        report.failed,
        report.skipped,
        report.cancelled,
    )


def clearcut_cli() -> None:
    """Punto de entrada del comando `clearcut`."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = _build_clearcut_arg_parser()
    args = parser.parse_args()
    args.handler(args)


# ---------------------------------------------------------------------------
# `designfabric` — generación de stickers vía Ollama + FLUX.2 (ex DesignFabric CLI)
# ---------------------------------------------------------------------------


def _run_designfabric(
    num_images: int,
    ollama_model: str,
    llm_provider: str,
    image_provider: str,
    run_generation_batch: object,
) -> None:
    """Orquesta el flujo completo: generar conceptos y renderizarlos como stickers."""
    from designfabric.cli.rich_reporter import RichProgressReporter, console

    console.print(f"[bold]🏷  DesignFabric Sticker Generator[/bold] — generando {num_images} sticker(s)\n")

    settings = get_settings()
    run_generation_batch(  # type: ignore[operator]
        num_images,
        ollama_model=ollama_model,
        output_dir=settings.output_dir,
        reporter=RichProgressReporter(),
        ollama_host=settings.ollama_host,
        llm_provider=llm_provider,
        image_provider=image_provider,
    )


def designfabric_cli() -> None:
    """Punto de entrada del comando `designfabric`."""
    from designfabric.core.generation.constants import OLLAMA_MODEL_DEFAULT
    from designfabric.core.generation.pipeline import run_batch as run_generation_batch

    parser = argparse.ArgumentParser(description="Generador de stickers CLI de DesignFabric.")
    parser.add_argument("--n", type=int, default=1, help="Número de imágenes a generar")
    parser.add_argument(
        "--ollama-model",
        type=str,
        default=OLLAMA_MODEL_DEFAULT,
        help=f"Modelo de Ollama a usar para generar conceptos (por defecto: {OLLAMA_MODEL_DEFAULT})",
    )
    parser.add_argument(
        "--llm-provider",
        choices=("ollama", "test"),
        default="ollama",
        help="Provider primitivo de texto (por defecto: ollama)",
    )
    parser.add_argument(
        "--image-provider",
        choices=("flux", "test"),
        default="flux",
        help="Provider primitivo de imagen (por defecto: flux)",
    )

    args = parser.parse_args()
    _run_designfabric(
        args.n,
        args.ollama_model,
        args.llm_provider,
        args.image_provider,
        run_generation_batch,
    )


if __name__ == "__main__":
    clearcut_cli()
