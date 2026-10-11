"""Pruebas de preparación offline de plantillas de mockup."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from designfabric.core.imaging.background_removal_strategies import RemovalModelPaths
from designfabric.core.imaging.mockup.prepare import prepare_template, save_template
from designfabric.core.imaging.mockup.template import load_template


def _foto_sintetica() -> Image.Image:
    pixels = np.full((100, 80, 3), 30, dtype=np.uint8)
    pixels[12:88, 20:60] = np.linspace(120, 210, 76, dtype=np.uint8)[:, None, None]
    return Image.fromarray(pixels, mode="RGB")


def test_preparar_propone_componente_mayor_desde_luminancia() -> None:
    preparado = prepare_template(_foto_sintetica(), model_paths=RemovalModelPaths())
    mascara = np.asarray(preparado.garment_mask)

    assert preparado.base.mode == "RGB"
    assert mascara.shape == (100, 80)
    assert set(np.unique(mascara)) <= {0, 255}
    assert mascara[50, 40] == 255
    assert mascara[0, 0] == 0


def test_usa_sam2_configurado_con_punto_central(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from designfabric.core.imaging.sam2_vitmatte import sam2_session

    encoder = tmp_path / "encoder.onnx"
    decoder = tmp_path / "decoder.onnx"
    expected_mask = np.zeros((100, 80), dtype=np.uint8)
    expected_mask[10:90, 15:65] = 1

    class Sam2Falso:
        def __init__(self, encoder_path: Path, decoder_path: Path) -> None:
            assert encoder_path == encoder
            assert decoder_path == decoder

        def predict_masks(
            self,
            image_bgr: np.ndarray,
            point_xy: tuple[float, float] | None = None,
        ) -> np.ndarray:
            assert tuple(image_bgr[50, 40]) == (210, 120, 30)
            assert point_xy == (40.0, 50.0)
            return expected_mask[None, ...]

    monkeypatch.setattr(sam2_session, "Sam2OnnxSession", Sam2Falso)
    photo = Image.new("RGB", (80, 100), (30, 120, 210))
    paths = RemovalModelPaths(sam2_encoder_onnx=encoder, sam2_decoder_onnx=decoder)

    prepared = prepare_template(photo, model_paths=paths)

    proposed = np.asarray(prepared.garment_mask)
    assert proposed[50, 40] == 255
    assert proposed[0, 0] == 0
    assert 0 < np.count_nonzero(proposed) <= np.count_nonzero(expected_mask)


def test_shading_y_displacement_se_normalizan_en_la_prenda() -> None:
    mask = np.zeros((100, 80), dtype=np.uint8)
    mask[10:90, 15:65] = 255
    preparado = prepare_template(_foto_sintetica(), Image.fromarray(mask), model_paths=RemovalModelPaths())
    active = mask > 0
    shading = np.asarray(preparado.shading, dtype=np.uint8)
    displacement = np.asarray(preparado.displacement, dtype=np.uint8)

    assert float(np.median(shading[active])) == pytest.approx(128, abs=1)
    assert float(np.mean(displacement[active])) == pytest.approx(128, abs=1)
    assert np.all(shading[~active] == 128)
    assert np.all(displacement[~active] == 128)


def test_normalizacion_admite_prenda_negra_uniforme() -> None:
    mask = Image.new("L", (40, 30), 255)
    photo = Image.new("RGB", (40, 30), (0, 0, 0))

    preparado = prepare_template(photo, mask, model_paths=RemovalModelPaths())

    assert np.all(np.asarray(preparado.shading) == 128)
    assert np.all(np.asarray(preparado.displacement) == 128)


def test_guardar_y_cargar_plantilla_preparada(tmp_path: Path) -> None:
    template_dir = tmp_path / "tee-front-01"
    template = save_template(
        template_dir,
        _foto_sintetica(),
        template_id="tee-front-01",
        name="Camiseta frontal de prueba",
        corners=((15, 20), (65, 20), (65, 80), (15, 80)),
        px_per_cm=4.0,
        model_paths=RemovalModelPaths(),
    )

    loaded = load_template(template_dir)
    assert template.id == loaded.id == "tee-front-01"
    assert loaded.name == "Camiseta frontal de prueba"
    assert loaded.base_size == (80, 100)
    assert loaded.base.mode == "RGB"
    assert loaded.garment_mask.mode == "L"
    assert loaded.shading.mode == "L"
    assert loaded.displacement.mode == "L"
    assert sorted(path.name for path in template_dir.iterdir()) == [
        "base.png",
        "displacement.png",
        "garment_mask.png",
        "shading.png",
        "template.json",
    ]


def test_rechaza_mascara_de_tamano_incorrecto() -> None:
    wrong_size = Image.new("L", (10, 10), 255)

    with pytest.raises(ValueError, match="debe medir"):
        prepare_template(_foto_sintetica(), wrong_size, model_paths=RemovalModelPaths())
