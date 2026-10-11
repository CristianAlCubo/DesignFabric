"""CLI para preparar plantillas offline de mockup."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from PIL import Image

from designfabric.core.imaging.mockup.prepare import save_template

app = typer.Typer(help="Herramientas offline para preparar plantillas de mockup.")


@app.callback()
def _main() -> None:
    """Agrupa los subcomandos de `designfabric-mockup`."""


@app.command("prepare")
def prepare_command(
    photo: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=True, dir_okay=False, readable=True, help="Foto RGB de la prenda."),
    ],
    template_id: Annotated[str, typer.Option("--id", help="Identificador único de la plantilla.")],
    corners: Annotated[
        str,
        typer.Option(
            "--corners",
            help="Esquinas TL,TR,BR,BL como 'x,y;x,y;x,y;x,y' o JSON [[x,y],...].",
        ),
    ],
    px_per_cm: Annotated[float, typer.Option("--px-per-cm", min=0.000001, help="Escala real de impresión.")],
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Carpeta raíz donde se guardará la plantilla.", file_okay=False),
    ] = Path("data/mockup_templates"),
    mask_path: Annotated[
        Path | None,
        typer.Option("--mask", exists=True, file_okay=True, dir_okay=False, readable=True, help="Máscara manual opcional."),
    ] = None,
    name: Annotated[str | None, typer.Option("--name", help="Nombre legible de la plantilla.")] = None,
    max_print_cm: Annotated[
        str,
        typer.Option("--max-print-cm", help="Ancho,alto máximo imprimible en cm (por defecto 30,40)."),
    ] = "30,40",
) -> None:
    """Prepara una carpeta v1 a partir de una foto y unas esquinas."""
    try:
        parsed_corners = _parse_corners(corners)
        parsed_max_print = _parse_pair(max_print_cm, "--max-print-cm")
        with Image.open(photo) as source:
            source.load()
            photo_rgb = source.convert("RGB")
        manual_mask = None
        if mask_path is not None:
            with Image.open(mask_path) as source_mask:
                source_mask.load()
                manual_mask = source_mask.convert("L")

        template = save_template(
            output_dir / template_id,
            photo_rgb,
            template_id=template_id,
            name=name or template_id,
            corners=parsed_corners,
            px_per_cm=px_per_cm,
            mask=manual_mask,
            max_print_cm=parsed_max_print,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        typer.echo(f"No se pudo preparar la plantilla: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Plantilla lista: {output_dir / template.id}")


def _parse_corners(value: str) -> tuple[tuple[float, float], ...]:
    try:
        raw = json.loads(value)
    except json.JSONDecodeError:
        try:
            raw = [[float(coordinate) for coordinate in point.split(",")] for point in value.split(";")]
        except ValueError as exc:
            raise ValueError("--corners debe tener el formato 'x,y;x,y;x,y;x,y'") from exc
    if (
        not isinstance(raw, list)
        or len(raw) != 4
        or any(not isinstance(point, list) or len(point) != 2 for point in raw)
    ):
        raise ValueError("--corners debe contener exactamente cuatro pares [x,y]")
    try:
        return tuple((float(point[0]), float(point[1])) for point in raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Las coordenadas de --corners deben ser números") from exc


def _parse_pair(value: str, option: str) -> tuple[float, float]:
    try:
        parts = [float(part.strip()) for part in value.split(",")]
    except ValueError as exc:
        raise ValueError(f"{option} debe tener el formato ancho,alto") from exc
    if len(parts) != 2:
        raise ValueError(f"{option} debe contener exactamente dos valores")
    return (parts[0], parts[1])


def mockup_cli() -> None:
    """Punto de entrada `designfabric-mockup`."""
    app()
