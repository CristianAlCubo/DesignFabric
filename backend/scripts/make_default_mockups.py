"""Genera las plantillas de mockup por defecto (camiseta *flat lay* frontal y trasera).

Las fotos se dibujan por código, sin IA: silueta de camiseta, pliegues suaves por
sinusoides y textura de tela con semilla fija. El resultado es determinista y se
guarda en `backend/data/mockup_templates/`, que viaja con el instalador.

Uso (desde `backend/`):

    uv run python scripts/make_default_mockups.py
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from designfabric.core.imaging.mockup.prepare import save_template

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "mockup_templates"
W, H = 1600, 1800
SS = 2  # supersampling para bordes suaves
BACKGROUND = (236, 234, 230)
# Ancho de pecho de una talla M ≈ 52 cm; en el dibujo el cuerpo mide 1000 px.
CHEST_PX = 1000
PX_PER_CM = CHEST_PX / 52.0
GARMENT_COLORS = {
    "blanco": "#FFFFFF",
    "negro": "#1A1A1A",
    "gris": "#9A9A9A",
    "azul marino": "#1F2A44",
    "rojo": "#B3202A",
    "verde": "#2F5D3A",
    "arena": "#D8C8A8",
}


def _silhouette(neck_depth: float) -> np.ndarray:
    """Máscara (H, W) de la camiseta, con el cuello recortado."""
    cx = W / 2
    half = CHEST_PX / 2
    pts = [
        (cx - 120, 180),          # cuello izq.
        (cx - half - 40, 260),    # hombro izq.
        (cx - half - 330, 560),   # punta manga izq. arriba
        (cx - half - 200, 740),   # punta manga izq. abajo
        (cx - half, 600),         # sisa izq.
        (cx - half + 10, 1680),   # bajo izq.
        (cx + half - 10, 1680),
        (cx + half, 600),
        (cx + half + 200, 740),
        (cx + half + 330, 560),
        (cx + half + 40, 260),
        (cx + 120, 180),
    ]
    big = np.zeros((H * SS, W * SS), np.uint8)
    cv2.fillPoly(big, [(np.array(pts) * SS).astype(np.int32)], 255, cv2.LINE_AA)
    cv2.ellipse(
        big, (int(cx * SS), int(170 * SS)), (int(130 * SS), int(neck_depth * SS)),
        0, 0, 360, 0, -1, cv2.LINE_AA,
    )
    return cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)


def _fabric(mask: np.ndarray, seed: int, neck_depth: float) -> Image.Image:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # Pliegues: pocas sinusoides oblicuas de baja frecuencia.
    folds = np.zeros((H, W), np.float32)
    for _ in range(6):
        angle = rng.uniform(-0.6, 0.6) + np.pi / 2
        freq = rng.uniform(1.5, 3.5) / W
        phase = rng.uniform(0, 2 * np.pi)
        proj = xx * np.cos(angle) + yy * np.sin(angle)
        folds += np.sin(2 * np.pi * freq * proj + phase) * rng.uniform(2.0, 5.0)
    folds = cv2.GaussianBlur(folds, (0, 0), 25)
    # Bordes más oscuros (volumen) y ligera luz arriba.
    dist = cv2.distanceTransform((mask > 127).astype(np.uint8), cv2.DIST_L2, 5)
    edge = np.clip(dist / 60.0, 0, 1) ** 0.5
    light = 1.0 - (yy / H) * 0.04
    tone = 244 * light * (0.88 + 0.12 * edge) + folds
    # Ribete del cuello.
    neck = np.zeros((H, W), np.uint8)
    cv2.ellipse(neck, (W // 2, 170), (150, int(neck_depth + 20)), 0, 0, 360, 255, 22, cv2.LINE_AA)
    tone -= (neck.astype(np.float32) / 255) * 10
    # Textura de punto.
    grain = cv2.GaussianBlur(rng.normal(0, 3.0, (H, W)).astype(np.float32), (0, 0), 0.8)
    tone = np.clip(tone + grain, 0, 255)

    alpha = mask.astype(np.float32)[..., None] / 255
    shirt = np.repeat(tone[..., None], 3, axis=2)
    bg = np.array(BACKGROUND, np.float32)[None, None, :]
    # Sombra de contacto suave bajo la prenda.
    shadow = cv2.GaussianBlur(mask.astype(np.float32) / 255, (0, 0), 18)
    shadow = np.roll(shadow, (14, 8), axis=(0, 1))[..., None] * 0.12
    bg_img = bg * (1 - shadow)
    out = shirt * alpha + bg_img * (1 - alpha)
    return Image.fromarray(np.rint(out).clip(0, 255).astype(np.uint8), "RGB")


def _print_corners(top: float) -> list[list[float]]:
    width_cm, height_cm = 30.0, 40.0
    w, h = width_cm * PX_PER_CM, height_cm * PX_PER_CM
    left = W / 2 - w / 2
    return [[left, top], [left + w, top], [left + w, top + h], [left, top + h]]


def main() -> None:
    specs = [
        ("tee-flat-front", "Camiseta lisa – frente", 95.0, 1, 380.0),
        ("tee-flat-back", "Camiseta lisa – espalda", 35.0, 2, 300.0),
    ]
    for template_id, name, neck_depth, seed, print_top in specs:
        mask = _silhouette(neck_depth)
        photo = _fabric(mask, seed, neck_depth)
        save_template(
            OUT_DIR / template_id,
            photo,
            template_id=template_id,
            name=name,
            corners=_print_corners(print_top),
            px_per_cm=PX_PER_CM,
            mask=mask,
            max_print_cm=(30.0, 40.0),
            displacement_strength_px=4.0,
            shading_strength=0.5,
            highlight_strength=0.25,
            garment_colors=GARMENT_COLORS,
            dark_garment_colors=("negro", "azul marino", "verde"),
        )
        print(f"ok {template_id}")


if __name__ == "__main__":
    main()
