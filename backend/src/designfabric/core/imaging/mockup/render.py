"""Motor de render determinista de mockups de prendas."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import math
from typing import Iterator

import cv2
import numpy as np
from PIL import Image

from designfabric.core.imaging.mockup.template import MockupRequest, MockupTemplate

_COLOR_HEX_LENGTH = 7
_WHITE = (255, 255, 255)
# Relieve extra para prendas oscuras: intensidad (en niveles de 0–255) y sombreado
# relativo por debajo del cual el relieve oscurece (por encima, aclara).
_DARK_RELIEF = 60.0
_RELIEF_FLOOR = 0.8
# Una tela blanca varía poco de tono; al teñirla se amplifica para que los pliegues
# sigan visibles.
_FOLD_GAIN = 2.2


@contextmanager
def _opencv_single_thread() -> Iterator[None]:
    """Fija temporalmente OpenCV a un hilo y restaura su configuración global."""
    previous_threads = cv2.getNumThreads()
    cv2.setNumThreads(1)
    try:
        yield
    finally:
        cv2.setNumThreads(previous_threads)


def render_mockup(
    design: Image.Image,
    template: MockupTemplate,
    request: MockupRequest,
    *,
    max_side: int | None = None,
) -> Image.Image:
    """Renderiza un PNG RGB determinista de diseño y plantilla.

    Los avisos se devuelven en ``imagen.info["warnings"]`` para mantener la firma
    de imagen compartida por el render completo y el preview.
    """
    if max_side is not None and (type(max_side) is not int or max_side <= 0):
        raise ValueError("max_side debe ser un entero positivo")

    with _opencv_single_thread():
        active_template, active_design = _resize_for_preview(template, design, max_side)
        warnings: list[str] = []

        color, color_key = _resolve_color(active_template, request.garment_color)
        if color_key is None:
            warnings.append(
                f"Color de prenda desconocido: {request.garment_color!r}; se usa blanco."
            )

        design_rgba = active_design.convert("RGBA")
        alpha = np.asarray(design_rgba.getchannel("A"), dtype=np.uint8)
        ys, xs = np.where(alpha > 0)
        if xs.size == 0:
            raise ValueError("El diseño debe contener píxeles visibles")

        # 1. Elimina el espacio transparente para calcular la escala sobre el arte.
        cropped = design_rgba.crop(
            (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        )
        cropped_pixels = np.asarray(cropped, dtype=np.uint8)
        cropped_alpha = cropped_pixels[:, :, 3].astype(np.float32) / np.float32(255.0)
        premultiplied = (
            cropped_pixels[:, :, :3].astype(np.float32) * cropped_alpha[:, :, None]
        )
        premultiplied_rgba = np.dstack((premultiplied, cropped_pixels[:, :, 3])).clip(
            0, 255
        )
        premultiplied_image = Image.fromarray(
            _rounded_u8(premultiplied_rgba), mode="RGBA"
        )

        # 2. Escala física y limita ancho/alto manteniendo la proporción del diseño.
        requested_width_px = request.print_width_cm * active_template.px_per_cm
        max_width_px = active_template.max_print_cm[0] * active_template.px_per_cm
        max_height_px = active_template.max_print_cm[1] * active_template.px_per_cm
        aspect = cropped.height / cropped.width
        width_px = min(requested_width_px, max_width_px, max_height_px / aspect)
        if width_px + 1e-6 < requested_width_px:
            warnings.append(
                "El diseño excede max_print_cm; se redujo para respetar el tamaño máximo."
            )
        target_width = max(1, int(round(width_px)))
        target_height = max(1, int(round(target_width * aspect)))
        resized_design = premultiplied_image.resize(
            (target_width, target_height), Image.Resampling.LANCZOS
        )
        resized_rgba = np.asarray(resized_design, dtype=np.uint8).astype(np.float32)

        # 3. Compone el arte sobre un plano, relativo al anclaje y al offset en cm.
        plane_width, plane_height = _print_plane_size(active_template)
        flat = np.zeros((plane_height, plane_width, 4), dtype=np.float32)
        anchor_x, anchor_y = _anchor_position(
            active_template.default_anchor, plane_width, plane_height
        )
        anchor_x += request.offset_cm[0] * active_template.px_per_cm
        anchor_y += request.offset_cm[1] * active_template.px_per_cm
        left = int(
            round(
                anchor_x
                - _anchor_fraction(active_template.default_anchor)[0] * target_width
            )
        )
        top = int(
            round(
                anchor_y
                - _anchor_fraction(active_template.default_anchor)[1] * target_height
            )
        )
        _place_clipped(flat, resized_rgba, left, top)
        flat = _rounded_u8(flat).astype(np.float32)

        # 4. Proyecta el plano a las cuatro esquinas de impresión.
        source_corners = np.asarray(
            [
                [0, 0],
                [plane_width - 1, 0],
                [plane_width - 1, plane_height - 1],
                [0, plane_height - 1],
            ],
            dtype=np.float32,
        )
        destination_corners = np.asarray(
            active_template.print_area_corners, dtype=np.float32
        )
        homography = cv2.getPerspectiveTransform(source_corners, destination_corners)
        output_width, output_height = active_template.base_size
        projected = cv2.warpPerspective(
            flat,
            homography,
            (output_width, output_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        projected = _rounded_u8(projected).astype(np.float32)

        # 5. Desplaza RGB premultiplicado y alpha con el mismo mapa explícito.
        displacement = np.asarray(active_template.displacement, dtype=np.float32)
        grid_x, grid_y = np.meshgrid(
            np.arange(output_width, dtype=np.float32),
            np.arange(output_height, dtype=np.float32),
        )
        # El nivel congelado 128 representa desplazamiento nulo por contrato.
        delta = ((displacement - np.float32(128.0)) / np.float32(127.0)) * np.float32(
            active_template.displacement_strength_px
        )
        map_x = np.ascontiguousarray(grid_x + delta, dtype=np.float32)
        map_y = np.ascontiguousarray(grid_y + delta, dtype=np.float32)
        displaced = cv2.remap(
            projected,
            map_x,
            map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        displaced = _rounded_u8(displaced).astype(np.float32)

        # 6. Restringe el alpha a la prenda y elimina zonas tapadas.
        garment_mask = np.asarray(
            active_template.garment_mask, dtype=np.float32
        ) / np.float32(255.0)
        if active_template.occlusion is None:
            visible = np.ones_like(garment_mask, dtype=np.float32)
        else:
            occlusion = np.asarray(
                active_template.occlusion, dtype=np.float32
            ) / np.float32(255.0)
            visible = np.float32(1.0) - occlusion
        raw_alpha = displaced[:, :, 3] / np.float32(255.0)
        final_alpha = raw_alpha * garment_mask * visible
        final_alpha_u8 = _rounded_u8(final_alpha * np.float32(255.0))
        if float(final_alpha.sum()) < float(raw_alpha.sum()) * 0.05:
            warnings.append(
                "El diseño está casi totalmente ocluido o fuera de la prenda."
            )

        # 7. Recolorea la prenda con su sombreado relativo (128 = tono medio de la tela);
        #    el exterior conserva la foto. En colores oscuros el multiply casi no deja
        #    ver pliegues, así que se suma un relieve proporcional a lo oscuro del color.
        base = np.asarray(active_template.base, dtype=np.uint8).astype(np.float32)
        relative = np.asarray(active_template.shading, dtype=np.float32) / np.float32(128.0)
        relative = np.clip(
            np.float32(1.0) + (relative - np.float32(1.0)) * np.float32(_FOLD_GAIN), 0.0, 2.0
        ).astype(np.float32)
        color_rgb = np.asarray(color, dtype=np.float32)
        color_luma = float(color_rgb @ np.asarray([0.299, 0.587, 0.114], dtype=np.float32))
        relief = np.float32(_DARK_RELIEF * (1.0 - color_luma / 255.0))
        recolored_garment = (
            relative[:, :, None] * color_rgb[None, None, :]
            + (relative[:, :, None] - np.float32(_RELIEF_FLOOR)) * relief
        )
        recolored = (
            base * (np.float32(1.0) - garment_mask[:, :, None])
            + recolored_garment * garment_mask[:, :, None]
        )
        recolored = _rounded_u8(recolored).astype(np.float32)

        # 8. Conserva el color del diseño, modula sombras y aplica luces en modo screen.
        shade_strength = active_template.shading_strength
        if color_key in active_template.dark_garment_colors:
            shade_strength *= 0.5
        shading = np.asarray(active_template.shading, dtype=np.float32) / np.float32(
            128.0
        )
        shade_factor = np.float32(1.0) - np.float32(shade_strength) * (
            np.float32(1.0) - shading
        )
        original_alpha = displaced[:, :, 3] / np.float32(255.0)
        straight_rgb = np.zeros_like(displaced[:, :, :3], dtype=np.float32)
        visible_pixels = original_alpha > 0
        straight_rgb[visible_pixels] = (
            displaced[:, :, :3][visible_pixels] / original_alpha[visible_pixels, None]
        )
        shaded_rgb = straight_rgb * shade_factor[:, :, None]
        highlight = np.clip(shading - np.float32(1.0), 0, 1)
        highlight = highlight[:, :, None] * np.float32(
            255.0 * active_template.highlight_strength
        )
        shaded_rgb = np.float32(255.0) - (
            np.float32(255.0) - np.clip(shaded_rgb, 0, 255)
        ) * (np.float32(255.0) - highlight) / np.float32(255.0)
        shaded_rgb = _rounded_u8(shaded_rgb).astype(np.float32)

        # 9. Alpha-composite sobre la prenda y adjunta resolución de impresión.
        alpha_float = final_alpha_u8.astype(np.float32)[:, :, None] / np.float32(255.0)
        result_pixels = shaded_rgb * alpha_float + recolored * (
            np.float32(1.0) - alpha_float
        )
        result = Image.fromarray(_rounded_u8(result_pixels), mode="RGB")
        result.info["dpi"] = (300, 300)
        result.info["warnings"] = tuple(warnings)
        return result


def _rounded_u8(values: np.ndarray) -> np.ndarray:
    """Redondea explícitamente una etapa float32 al rango de imagen de 8 bits."""
    return np.rint(values).clip(0, 255).astype(np.uint8)


def _resize_for_preview(
    template: MockupTemplate, design: Image.Image, max_side: int | None
) -> tuple[MockupTemplate, Image.Image]:
    if max_side is None or max(template.base_size) <= max_side:
        return template, design

    scale = max_side / max(template.base_size)
    new_size = (
        max(1, int(round(template.base_size[0] * scale))),
        max(1, int(round(template.base_size[1] * scale))),
    )
    scale_x = new_size[0] / template.base_size[0]
    scale_y = new_size[1] / template.base_size[1]
    corners = template.print_area_corners

    def resize_image(image: Image.Image, mode: str) -> Image.Image:
        return image.convert(mode).resize(new_size, Image.Resampling.LANCZOS)

    resized_template = replace(
        template,
        base_size=new_size,
        print_area_corners=(
            (corners[0][0] * scale_x, corners[0][1] * scale_y),
            (corners[1][0] * scale_x, corners[1][1] * scale_y),
            (corners[2][0] * scale_x, corners[2][1] * scale_y),
            (corners[3][0] * scale_x, corners[3][1] * scale_y),
        ),
        px_per_cm=template.px_per_cm * scale_x,
        displacement_strength_px=template.displacement_strength_px * scale_x,
        base=resize_image(template.base, "RGB"),
        garment_mask=resize_image(template.garment_mask, "L"),
        shading=resize_image(template.shading, "L"),
        displacement=resize_image(template.displacement, "L"),
        occlusion=(
            resize_image(template.occlusion, "L")
            if template.occlusion is not None
            else None
        ),
    )
    design_size = (
        max(1, int(round(design.width * scale_x))),
        max(1, int(round(design.height * scale_y))),
    )
    resized_design = design.convert("RGBA").resize(
        design_size, Image.Resampling.LANCZOS
    )
    return resized_template, resized_design


def _resolve_color(
    template: MockupTemplate, requested: str
) -> tuple[tuple[int, int, int], str | None]:
    if requested in template.garment_colors:
        return _parse_hex(template.garment_colors[requested]), requested
    if len(requested) == _COLOR_HEX_LENGTH and requested.startswith("#"):
        try:
            return _parse_hex(requested), next(
                (
                    key
                    for key, value in template.garment_colors.items()
                    if value.lower() == requested.lower()
                ),
                None,
            )
        except ValueError:
            pass
    return _WHITE, None


def _parse_hex(value: str) -> tuple[int, int, int]:
    if len(value) != _COLOR_HEX_LENGTH or not value.startswith("#"):
        raise ValueError("El color hexadecimal debe tener el formato #RRGGBB")
    try:
        return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError("El color hexadecimal debe tener el formato #RRGGBB") from exc


def _print_plane_size(template: MockupTemplate) -> tuple[int, int]:
    corners = template.print_area_corners
    top_width = math.dist(corners[0], corners[1])
    bottom_width = math.dist(corners[3], corners[2])
    left_height = math.dist(corners[0], corners[3])
    right_height = math.dist(corners[1], corners[2])
    return max(2, int(round((top_width + bottom_width) / 2))), max(
        2, int(round((left_height + right_height) / 2))
    )


def _anchor_fraction(anchor: str) -> tuple[float, float]:
    if anchor == "center":
        return (0.5, 0.5)
    parts = anchor.split("-")
    if len(parts) != 2 or parts[1] not in {"left", "center", "right"}:
        raise ValueError(f"Anclaje no compatible: {anchor!r}")
    vertical, horizontal = parts
    if vertical not in {"top", "center", "bottom"}:
        raise ValueError(f"Anclaje no compatible: {anchor!r}")
    return (
        {"left": 0.0, "center": 0.5, "right": 1.0}[horizontal],
        {"top": 0.0, "center": 0.5, "bottom": 1.0}[vertical],
    )


def _anchor_position(anchor: str, width: int, height: int) -> tuple[float, float]:
    fraction_x, fraction_y = _anchor_fraction(anchor)
    return ((width - 1) * fraction_x, (height - 1) * fraction_y)


def _place_clipped(canvas: np.ndarray, image: np.ndarray, left: int, top: int) -> None:
    canvas_height, canvas_width = canvas.shape[:2]
    image_height, image_width = image.shape[:2]
    x0, y0 = max(0, left), max(0, top)
    x1, y1 = (
        min(canvas_width, left + image_width),
        min(canvas_height, top + image_height),
    )
    if x0 >= x1 or y0 >= y1:
        return
    canvas[y0:y1, x0:x1] = image[y0 - top : y1 - top, x0 - left : x1 - left]
