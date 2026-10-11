"""Contratos y carga validada de plantillas de mockup."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, TypeAlias, TypeGuard

from PIL import Image

Point: TypeAlias = tuple[float, float]
Corners: TypeAlias = tuple[Point, Point, Point, Point]
Size: TypeAlias = tuple[int, int]
_COLOR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True, slots=True)
class MockupTemplate:
    """Plantilla inmutable con imágenes y parámetros ya validados."""

    id: str
    name: str
    base_size: Size
    print_area_corners: Corners
    px_per_cm: float
    max_print_cm: tuple[float, float]
    default_anchor: str
    displacement_strength_px: float
    shading_strength: float
    highlight_strength: float
    garment_colors: Mapping[str, str]
    dark_garment_colors: tuple[str, ...]
    base: Image.Image
    garment_mask: Image.Image
    shading: Image.Image
    displacement: Image.Image
    occlusion: Image.Image | None = None


@dataclass(frozen=True, slots=True)
class MockupRequest:
    """Parámetros variables para generar un mockup de una plantilla."""

    garment_color: str
    print_width_cm: float
    offset_cm: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self) -> None:
        if not isinstance(self.garment_color, str) or not self.garment_color:
            raise ValueError("garment_color debe ser una clave o un color hexadecimal")
        if self.garment_color.startswith("#") and not _COLOR_HEX.fullmatch(self.garment_color):
            raise ValueError("garment_color debe tener el formato #RRGGBB")
        if not _is_finite_number(self.print_width_cm) or self.print_width_cm <= 0:
            raise ValueError("print_width_cm debe ser un número finito mayor que cero")
        if (
            not isinstance(self.offset_cm, tuple)
            or len(self.offset_cm) != 2
            or not all(_is_finite_number(value) for value in self.offset_cm)
        ):
            raise ValueError("offset_cm debe contener dos números finitos")


def load_template(path: Path) -> MockupTemplate:
    """Carga una carpeta de plantilla y valida JSON, geometría e imágenes."""
    template_dir = Path(path)
    json_path = template_dir / "template.json"
    try:
        with json_path.open(encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer {json_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("template.json debe contener un objeto JSON")

    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version debe ser 1")
    template_id = _required_string(data, "id")
    name = _required_string(data, "name")
    base_size = _parse_size(data.get("base_size"))
    corners = _parse_corners(data.get("print_area"))
    px_per_cm = _positive_number(data.get("px_per_cm"), "px_per_cm")
    max_print_cm = _parse_positive_pair(data.get("max_print_cm"), "max_print_cm")
    default_anchor = _required_string(data, "default_anchor")
    displacement_strength_px = _nonnegative_number(
        data.get("displacement_strength_px"), "displacement_strength_px"
    )
    shading_strength = _unit_interval(data.get("shading_strength"), "shading_strength")
    highlight_strength = _unit_interval(data.get("highlight_strength"), "highlight_strength")
    garment_colors = _parse_colors(data.get("garment_colors"))
    dark_garment_colors = _parse_dark_colors(data.get("dark_garment_colors"), garment_colors)

    base = _load_png(template_dir / "base.png", "RGB", base_size)
    garment_mask = _load_png(template_dir / "garment_mask.png", "L", base_size)
    shading = _load_png(template_dir / "shading.png", "L", base_size)
    displacement = _load_png(template_dir / "displacement.png", "L", base_size)
    occlusion_path = template_dir / "occlusion.png"
    occlusion = _load_png(occlusion_path, "L", base_size) if occlusion_path.exists() else None

    return MockupTemplate(
        id=template_id,
        name=name,
        base_size=base_size,
        print_area_corners=corners,
        px_per_cm=px_per_cm,
        max_print_cm=max_print_cm,
        default_anchor=default_anchor,
        displacement_strength_px=displacement_strength_px,
        shading_strength=shading_strength,
        highlight_strength=highlight_strength,
        garment_colors=MappingProxyType(garment_colors),
        dark_garment_colors=dark_garment_colors,
        base=base,
        garment_mask=garment_mask,
        shading=shading,
        displacement=displacement,
        occlusion=occlusion,
    )


def _required_string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} debe ser una cadena no vacía")
    return value


def _parse_size(value: object) -> Size:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(part) is not int or part <= 0 for part in value)
    ):
        raise ValueError("base_size debe contener dos enteros positivos [W, H]")
    return (value[0], value[1])


def _parse_corners(value: object) -> Corners:
    if not isinstance(value, dict):
        raise ValueError("print_area debe ser un objeto con corners")
    points = value.get("corners")
    if not isinstance(points, list) or len(points) != 4:
        raise ValueError("print_area.corners debe contener exactamente cuatro puntos")
    parsed: list[Point] = []
    for point in points:
        if (
            not isinstance(point, list)
            or len(point) != 2
            or not all(_is_finite_number(coordinate) for coordinate in point)
        ):
            raise ValueError("Cada esquina debe contener dos coordenadas finitas")
        parsed.append((float(point[0]), float(point[1])))

    crosses = []
    for index in range(4):
        current = parsed[index]
        following = parsed[(index + 1) % 4]
        after_following = parsed[(index + 2) % 4]
        crosses.append(
            (following[0] - current[0]) * (after_following[1] - following[1])
            - (following[1] - current[1]) * (after_following[0] - following[0])
        )
    if any(abs(cross) <= 1e-9 for cross in crosses) or not (
        all(cross > 0 for cross in crosses) or all(cross < 0 for cross in crosses)
    ):
        raise ValueError("print_area.corners debe formar un cuadrilátero convexo")
    return (parsed[0], parsed[1], parsed[2], parsed[3])


def _parse_positive_pair(value: object, field_name: str) -> tuple[float, float]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(_is_finite_number(part) and part > 0 for part in value)
    ):
        raise ValueError(f"{field_name} debe contener dos números positivos")
    return (float(value[0]), float(value[1]))


def _parse_colors(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ValueError("garment_colors debe ser un objeto no vacío")
    colors: dict[str, str] = {}
    for name, color in value.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Las claves de garment_colors deben ser cadenas no vacías")
        if not isinstance(color, str) or not _COLOR_HEX.fullmatch(color):
            raise ValueError(f"El color de prenda {name!r} debe tener el formato #RRGGBB")
        colors[name] = color
    return colors


def _parse_dark_colors(value: object, colors: Mapping[str, str]) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError("dark_garment_colors debe ser una lista de claves")
    if any(item not in colors for item in value):
        raise ValueError("dark_garment_colors solo puede incluir claves de garment_colors")
    return tuple(value)


def _load_png(path: Path, mode: str, size: Size) -> Image.Image:
    try:
        with Image.open(path) as image:
            if image.format != "PNG":
                raise ValueError(f"{path.name} debe ser un PNG")
            if image.mode != mode:
                raise ValueError(f"{path.name} debe tener modo {mode}, no {image.mode}")
            if image.size != size:
                raise ValueError(f"{path.name} debe medir {size[0]}×{size[1]}, no {image.size}")
            image.load()
            return image.copy()
    except OSError as exc:
        raise ValueError(f"No se pudo leer {path}: {exc}") from exc


def _is_finite_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _positive_number(value: object, field_name: str) -> float:
    if not _is_finite_number(value) or value <= 0:
        raise ValueError(f"{field_name} debe ser un número finito mayor que cero")
    return float(value)


def _nonnegative_number(value: object, field_name: str) -> float:
    if not _is_finite_number(value) or value < 0:
        raise ValueError(f"{field_name} debe ser un número finito no negativo")
    return float(value)


def _unit_interval(value: object, field_name: str) -> float:
    if not _is_finite_number(value) or not 0 <= value <= 1:
        raise ValueError(f"{field_name} debe estar entre 0 y 1")
    return float(value)
