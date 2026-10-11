"""Genera las plantillas de mockup con modelo (`tee-model-man`, `tee-model-woman`).

Las fotos base se generaron con IA (OpenRouter, `openai/gpt-image-2.5-sunburst`) y
quedan guardadas como `base.png` de cada plantilla. Este script rehace máscara,
escala y zona de impresión a partir de ellas; con `--generate` pide fotos nuevas
(necesita `OPENROUTER_API_KEY` en el entorno; nunca se escribe en disco).

Uso (desde `backend/`):

    uv run python scripts/make_model_mockups.py              # reusa las fotos actuales
    uv run python scripts/make_model_mockups.py --generate   # fotos nuevas (cuesta créditos)
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from designfabric.core.imaging.mockup.prepare import save_template

GARMENT_COLORS = {
    "blanco": "#FFFFFF",
    "negro": "#1A1A1A",
    "gris": "#9A9A9A",
    "azul marino": "#1F2A44",
    "rojo": "#B3202A",
    "verde": "#2F5D3A",
    "arena": "#D8C8A8",
}
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "mockup_templates"
IMAGE_MODEL = "openai/gpt-image-2.5-sunburst"
PROMPT = (
    "Professional e-commerce product photo of a plain white crew-neck cotton t-shirt {who}, "
    "front view, straight-on camera at chest height, chest fully visible and unobstructed, "
    "arms relaxed at sides, no logos, no prints, no text, soft even studio lighting, "
    "subtle natural fabric folds, neutral light gray seamless background, "
    "high resolution, sharp fabric texture, photorealistic"
)


@dataclass(frozen=True)
class ModelSpec:
    template_id: str
    name: str
    who: str
    length_cm: float  # largo cuello→bajo de una talla M
    max_print_cm: tuple[float, float]
    torso_row: int  # fila (px) bajo las axilas para hallar el centro del torso
    # Correcciones de máscara específicas de la foto actual.
    sleeve_hull_rows: tuple[int, int] | None = None
    recover_shaded_sides: bool = False


SPECS = (
    ModelSpec(
        "tee-model-man", "Camiseta – modelo hombre",
        "worn by an adult man, cropped from chin to hips",
        68.0, (28.0, 36.0), 620, sleeve_hull_rows=(60, 520), recover_shaded_sides=True,
    ),
    ModelSpec(
        "tee-model-woman", "Camiseta – modelo mujer",
        "worn by an adult woman, cropped from chin to hips",
        62.0, (24.0, 32.0), 640,
    ),
)


def generate_photo(spec: ModelSpec) -> Image.Image:
    from designfabric.core.generation.openrouter.client import OpenRouterClient

    client = OpenRouterClient(os.environ["OPENROUTER_API_KEY"], timeout=300)
    data = client.generate_image(
        PROMPT.format(who=spec.who),
        model=IMAGE_MODEL,
        modalities=["image"],
        image_options={"output_format": "png"},
    )
    return Image.open(BytesIO(data)).convert("RGB")


def shirt_mask(rgb: np.ndarray, spec: ModelSpec) -> np.ndarray:
    """Camiseta blanca sobre fondo gris: GrabCut sembrado por color + correcciones.

    Solo corre al preparar la plantilla (offline); el render nunca la recalcula.
    """
    h, w = rgb.shape[:2]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat, val = hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    not_shirt = (sat > 45) | (val < 110)  # piel, pelo, vaqueros

    gc = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    gc[(sat < 25) & (val > 205)] = cv2.GC_PR_FGD
    core = cv2.erode(((sat < 18) & (val > 225)).astype(np.uint8), np.ones((15, 15), np.uint8))
    gc[core > 0] = cv2.GC_FGD
    gc[not_shirt] = cv2.GC_BGD
    b = max(4, w // 100)
    gc[:b, :] = gc[:, :b] = gc[:, -b:] = cv2.GC_BGD
    cv2.setRNGSeed(0)
    cv2.grabCut(
        rgb[..., ::-1].copy(), gc, None,
        np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64),
        6, cv2.GC_INIT_WITH_MASK,
    )
    m = np.isin(gc, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8)
    _, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    m = (lab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81)))
    m[not_shirt] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    flood = m.copy()
    cv2.floodFill(flood, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 255)
    m |= cv2.bitwise_not(flood)

    if spec.sleeve_hull_rows:
        # Muescas en el borde de las mangas: envolvente convexa de cada manga.
        y0, y1 = spec.sleeve_hull_rows
        for x0, x1 in ((0, w // 3), (w - w // 3, w)):
            region = np.zeros_like(m)
            region[y0:y1, x0:x1] = m[y0:y1, x0:x1]
            pts = cv2.findNonZero(region)
            if pts is None:
                continue
            hull = np.zeros_like(m)
            cv2.fillConvexPoly(hull, cv2.convexHull(pts), 255)
            hull[not_shirt] = 0
            m = np.maximum(m, hull)

    if spec.recover_shaded_sides:
        # La tela en sombra tiene el gris del fondo pero un leve tinte cálido
        # (saturación 5–40); el fondo es neutro (≤ 3).
        cand = ((sat >= 5) & (sat <= 40) & (val > 140)).astype(np.uint8)
        near = cv2.dilate((m > 127).astype(np.uint8), np.ones((61, 61), np.uint8))
        add = cv2.morphologyEx(cand & near, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        _, lab = cv2.connectedComponents(((m > 127) | (add > 0)).astype(np.uint8), connectivity=8)
        cy, cx = h // 2, w // 2
        keep = lab == lab[cy, cx]
        m = np.where(keep, np.maximum(m, add * 255), m).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        m[sat > 45] = 0

    # Cubre el margen blanco de 1–2 px que deja la segmentación; si quedara fuera,
    # se vería como un hilo claro al teñir.
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    return cv2.GaussianBlur(m, (0, 0), 1.6)


def build(spec: ModelSpec, photo: Image.Image) -> None:
    rgb = np.asarray(photo.convert("RGB"))
    mask = shirt_mask(rgb, spec)
    m = mask > 127
    xs = np.nonzero(m[spec.torso_row])[0]
    cx = (xs.min() + xs.max()) / 2
    ys = np.nonzero(m[:, int(cx)])[0]
    ppc = (ys.max() - ys.min()) / spec.length_cm
    pw, ph = spec.max_print_cm
    w, h = pw * ppc, ph * ppc
    if w > 0.85 * (xs.max() - xs.min()):
        raise ValueError(f"{spec.template_id}: la zona de impresión no cabe en el torso")
    top = ys.min() + 7 * ppc  # ~7 cm bajo el cuello
    corners = [[cx - w / 2, top], [cx + w / 2, top], [cx + w / 2, top + h], [cx - w / 2, top + h]]
    save_template(
        OUT_DIR / spec.template_id, photo, template_id=spec.template_id, name=spec.name,
        corners=corners, px_per_cm=ppc, mask=mask, max_print_cm=spec.max_print_cm,
        displacement_strength_px=5.0, shading_strength=0.55, highlight_strength=0.3,
        garment_colors=GARMENT_COLORS, dark_garment_colors=("negro", "azul marino", "verde"),
    )
    print(f"ok {spec.template_id}: {ppc:.2f} px/cm")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--generate", action="store_true", help="pedir fotos nuevas a OpenRouter")
    args = parser.parse_args()
    for spec in SPECS:
        if args.generate:
            photo = generate_photo(spec)
        else:
            # Copia en memoria: save_template sobrescribe base.png.
            photo = Image.open(OUT_DIR / spec.template_id / "base.png").convert("RGB").copy()
        build(spec, photo)


if __name__ == "__main__":
    main()
