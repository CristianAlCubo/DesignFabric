"""Tests del pipeline SAM2 + ViTMatte (con runners mockeados)."""

from __future__ import annotations

import numpy as np

from designfabric.core.imaging.background_removal_strategies import RemovalModelPaths
from designfabric.core.imaging.sam2_vitmatte.guided_filter import guided_filter
from designfabric.core.imaging.sam2_vitmatte.mask_selection import clean_mask, select_primary_mask
from designfabric.core.imaging.sam2_vitmatte.pipeline import Sam2VitMattePipeline
from designfabric.core.imaging.sam2_vitmatte.sam2_session import Sam2OnnxSession
from designfabric.core.imaging.sam2_vitmatte.strategy import Sam2VitMatteStrategy
from designfabric.core.imaging.sam2_vitmatte.trimap import build_trimap
from designfabric.core.imaging.sam2_vitmatte.vitmatte_session import VitMatteOnnxSession


class _FakeSam2:
    def predict_masks(self, image_bgr: np.ndarray) -> np.ndarray:
        h, w = image_bgr.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        mask[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4] = 255
        return mask[None, ...]


class _FakeVitMatte:
    def predict_alpha(self, image_bgr: np.ndarray, trimap: np.ndarray) -> np.ndarray:
        h, w = image_bgr.shape[:2]
        alpha = np.zeros((h, w), dtype=np.float32)
        alpha[trimap == 255] = 1.0
        alpha[trimap == 128] = 0.5
        return alpha


def test_select_primary_mask_picks_largest() -> None:
    small = np.zeros((40, 40), dtype=np.uint8)
    small[5:10, 5:10] = 255
    large = np.zeros((40, 40), dtype=np.uint8)
    large[10:35, 10:35] = 255
    chosen = select_primary_mask(np.stack([small, large], axis=0))
    assert chosen[20, 20] == 255
    assert chosen[7, 7] == 0


def test_clean_mask_keeps_largest_component() -> None:
    mask = np.zeros((50, 50), dtype=np.uint8)
    mask[5:10, 5:10] = 255
    mask[15:40, 15:40] = 255
    cleaned = clean_mask(mask, close_kernel=0, open_kernel=0)
    assert cleaned[25, 25] == 255
    assert cleaned[7, 7] == 0


def test_build_trimap_has_three_levels() -> None:
    mask = np.zeros((60, 60), dtype=np.uint8)
    mask[15:45, 15:45] = 255
    trimap = build_trimap(mask, erode_iter=2, dilate_iter=4)
    values = set(np.unique(trimap).tolist())
    assert values == {0, 128, 255}


def test_guided_filter_preserves_shape() -> None:
    guide = np.random.rand(32, 32).astype(np.float32)
    src = np.clip(guide + 0.1, 0, 1).astype(np.float32)
    out = guided_filter(guide, src, radius=2, eps=1e-3)
    assert out.shape == guide.shape
    assert out.dtype == np.float32


def test_pipeline_returns_bgra_with_soft_alpha() -> None:
    image = np.full((80, 80, 3), 40, dtype=np.uint8)
    image[20:60, 20:60] = (30, 30, 220)
    pipeline = Sam2VitMattePipeline(_FakeSam2(), _FakeVitMatte())
    result = pipeline.run(image)
    assert result.shape == (80, 80, 4)
    assert result.dtype == np.uint8
    assert result[40, 40, 3] > 0
    assert result[5, 5, 3] == 0


def test_vitmatte_single_input_uses_four_channels_when_shape_dynamic() -> None:
    class _Meta:
        def __init__(self) -> None:
            self.name = "pixel_values"
            self.shape = ["batch", "channels", "height", "width"]

    class _Session:
        def get_inputs(self) -> list[_Meta]:
            return [_Meta()]

    session = VitMatteOnnxSession.__new__(VitMatteOnnxSession)
    image = np.zeros((1, 3, 64, 64), dtype=np.float32)
    trimap = np.ones((1, 1, 64, 64), dtype=np.float32) * 0.5
    feeds = session._build_feeds(_Session(), image, trimap)
    assert feeds["pixel_values"].shape == (1, 4, 64, 64)


def test_decoder_feed_mapping_does_not_confuse_mask_input_names() -> None:
    session = Sam2OnnxSession.__new__(Sam2OnnxSession)
    session._encoder_hw = (1024, 1024)
    session._decoder_input_names = [
        "image_embed",
        "high_res_feats_0",
        "high_res_feats_1",
        "point_coords",
        "point_labels",
        "mask_input",
        "has_mask_input",
    ]
    image_embed = np.zeros((1, 256, 64, 64), dtype=np.float32)
    feats0 = np.zeros((1, 32, 256, 256), dtype=np.float32)
    feats1 = np.zeros((1, 64, 128, 128), dtype=np.float32)
    feeds = session._prepare_decoder_feeds(
        image_embed,
        feats0,
        feats1,
        np.array([[512.0, 512.0]], dtype=np.float32),
        np.array([1], dtype=np.float32),
        orig_hw=(1024, 1024),
    )
    assert feeds["has_mask_input"].ndim == 1
    assert feeds["has_mask_input"].shape == (1,)
    assert feeds["mask_input"].ndim == 4


def test_predict_masks_uses_explicit_point_xy_override() -> None:
    class _FakeEncoder:
        def run(self, output_names, feeds):
            del output_names, feeds
            return [
                np.zeros((1, 32, 256, 256), dtype=np.float32),
                np.zeros((1, 64, 128, 128), dtype=np.float32),
                np.zeros((1, 256, 64, 64), dtype=np.float32),
            ]

    class _FakeDecoder:
        def __init__(self) -> None:
            self.received_point_coords: np.ndarray | None = None

        def run(self, output_names, feeds):
            del output_names
            self.received_point_coords = feeds["point_coords"]
            return [np.zeros((1, 1, 64, 64), dtype=np.float32), np.array([[1.0]], dtype=np.float32)]

    session = Sam2OnnxSession.__new__(Sam2OnnxSession)
    session._encoder_hw = (1024, 1024)
    session._encoder_input_name = "image"
    session._encoder_output_names = ["high_res_feats_0", "high_res_feats_1", "image_embed"]
    session._decoder_input_names = [
        "image_embed",
        "high_res_feats_0",
        "high_res_feats_1",
        "point_coords",
        "point_labels",
        "mask_input",
        "has_mask_input",
    ]
    session._decoder_output_names = ["masks", "scores"]
    fake_encoder = _FakeEncoder()
    fake_decoder = _FakeDecoder()
    session._encoder = fake_encoder
    session._decoder = fake_decoder

    image = np.zeros((64, 64, 3), dtype=np.uint8)
    session.predict_masks(image, point_xy=(10.0, 20.0))

    assert fake_decoder.received_point_coords is not None
    # coords se escalan de espacio original (64x64) a espacio del encoder (1024x1024).
    expected = np.array([[[10.0 / 64 * 1024, 20.0 / 64 * 1024]]], dtype=np.float32)
    np.testing.assert_allclose(fake_decoder.received_point_coords, expected)


def test_predict_masks_defaults_to_image_center_without_point_xy() -> None:
    class _FakeEncoder:
        def run(self, output_names, feeds):
            del output_names, feeds
            return [
                np.zeros((1, 32, 256, 256), dtype=np.float32),
                np.zeros((1, 64, 128, 128), dtype=np.float32),
                np.zeros((1, 256, 64, 64), dtype=np.float32),
            ]

    class _FakeDecoder:
        def __init__(self) -> None:
            self.received_point_coords: np.ndarray | None = None

        def run(self, output_names, feeds):
            del output_names
            self.received_point_coords = feeds["point_coords"]
            return [np.zeros((1, 1, 64, 64), dtype=np.float32), np.array([[1.0]], dtype=np.float32)]

    session = Sam2OnnxSession.__new__(Sam2OnnxSession)
    session._encoder_hw = (1024, 1024)
    session._encoder_input_name = "image"
    session._encoder_output_names = ["high_res_feats_0", "high_res_feats_1", "image_embed"]
    session._decoder_input_names = [
        "image_embed",
        "high_res_feats_0",
        "high_res_feats_1",
        "point_coords",
        "point_labels",
        "mask_input",
        "has_mask_input",
    ]
    session._decoder_output_names = ["masks", "scores"]
    fake_decoder = _FakeDecoder()
    session._encoder = _FakeEncoder()
    session._decoder = fake_decoder

    image = np.zeros((64, 64, 3), dtype=np.uint8)
    session.predict_masks(image)

    expected = np.array([[[512.0, 512.0]]], dtype=np.float32)
    np.testing.assert_allclose(fake_decoder.received_point_coords, expected)


def test_strategy_uses_injected_runners(tmp_path) -> None:
    paths = RemovalModelPaths(
        tmp_path / "encoder.onnx",
        tmp_path / "decoder.onnx",
        tmp_path / "vitmatte.onnx",
    )
    strategy = Sam2VitMatteStrategy(paths, sam2=_FakeSam2(), vitmatte=_FakeVitMatte())
    image = np.full((64, 64, 3), 200, dtype=np.uint8)
    image[16:48, 16:48] = (10, 10, 10)
    result = strategy.remove_background(image)
    assert result.shape == (64, 64, 4)
