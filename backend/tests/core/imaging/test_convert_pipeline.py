"""Tests del pipeline de conversión de formato (Pillow).

Cobertura: matriz de todas las parejas (origen × destino) de los formatos
soportados (JPEG/JPG/PNG/WEBP), manejo de transparencia (aplanado a JPEG,
preservación en PNG/WEBP), calidad/lossless, fidelidad sin pérdida y el modo
lote (formatos mixtos, deduplicación, resiliencia a fallos, vacío y progreso).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from PIL import Image

from designfabric.core.imaging.convert_pipeline import (
    DEFAULT_QUALITY,
    ConvertBatchReport,
    ConvertItemResult,
    convert_batch,
    convert_one,
    resolve_target_format,
)
from designfabric.core.progress import Phase, ProgressEventType

SUPPORTED_FORMATS = ["PNG", "JPEG", "JPG", "WEBP"]

# ---------------------------------------------------------------------------
# Helpers de generación de imágenes
# ---------------------------------------------------------------------------


def _opaque_varied(size: tuple[int, int] = (40, 30)) -> Image.Image:
    """Imagen RGB opaca con píxeles variados (segura como origen JPEG)."""
    img = Image.new("RGB", size)
    px = img.load()
    width, height = size
    for y in range(height):
        for x in range(width):
            px[x, y] = (x * 6 % 256, y * 8 % 256, (x * y) % 256)
    return img


def _transparent_rgba(size: tuple[int, int] = (32, 24)) -> Image.Image:
    """Imagen RGBA totalmente transparente (rojo bajo alpha 0)."""
    return Image.new("RGBA", size, (255, 0, 0, 0))


def _write_source(directory: Path, fmt: str, *, size: tuple[int, int] = (40, 30)) -> Path:
    """Escribe una imagen opaca codificada en el formato `fmt` y devuelve su ruta."""
    directory.mkdir(parents=True, exist_ok=True)
    spec = resolve_target_format(fmt)
    dest = directory / f"src_{fmt}{spec.extension}"
    _opaque_varied(size).save(dest, format=spec.pillow_format)
    return dest


class _RecordingReporter:
    """`ProgressReporter` de prueba que acumula los eventos emitidos."""

    def __init__(self) -> None:
        self.events: list = []

    def emit(self, event) -> None:  # noqa: ANN001 - duck typing del protocolo
        self.events.append(event)


# ---------------------------------------------------------------------------
# resolve_target_format
# ---------------------------------------------------------------------------


def test_resolve_target_format_jpg_and_jpeg_share_codec() -> None:
    jpg = resolve_target_format("JPG")
    jpeg = resolve_target_format("JPEG")
    assert jpg.pillow_format == jpeg.pillow_format == "JPEG"
    assert jpg.extension == jpeg.extension == ".jpg"


@pytest.mark.parametrize("alias", ["png", "Png", "PNG", "wEbP", "jpeg", "jpg"])
def test_resolve_target_format_is_case_insensitive(alias: str) -> None:
    assert resolve_target_format(alias).pillow_format in {"PNG", "WEBP", "JPEG"}


@pytest.mark.parametrize(
    ("fmt", "pillow_format", "extension", "supports_quality", "supports_alpha"),
    [
        ("JPEG", "JPEG", ".jpg", True, False),
        ("JPG", "JPEG", ".jpg", True, False),
        ("PNG", "PNG", ".png", False, True),
        ("WEBP", "WEBP", ".webp", True, True),
    ],
)
def test_resolve_target_format_capabilities(
    fmt: str, pillow_format: str, extension: str, supports_quality: bool, supports_alpha: bool
) -> None:
    spec = resolve_target_format(fmt)
    assert spec.pillow_format == pillow_format
    assert spec.extension == extension
    assert spec.supports_quality is supports_quality
    assert spec.supports_alpha is supports_alpha


@pytest.mark.parametrize("bad", ["GIF", "TIFF", "avif", "", "bmp"])
def test_resolve_target_format_invalid_raises(bad: str) -> None:
    with pytest.raises(ValueError):
        resolve_target_format(bad)


# ---------------------------------------------------------------------------
# convert_one: matriz completa de parejas de formatos
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source_fmt", SUPPORTED_FORMATS)
@pytest.mark.parametrize("target_fmt", SUPPORTED_FORMATS)
def test_convert_one_every_format_pair(tmp_path: Path, source_fmt: str, target_fmt: str) -> None:
    """Cada una de las 16 parejas (origen × destino) produce un archivo válido del destino."""
    src = _write_source(tmp_path, source_fmt)
    spec = resolve_target_format(target_fmt)
    dest = tmp_path / f"out_{source_fmt}_to_{target_fmt}{spec.extension}"

    result = convert_one(src, dest, target_fmt)

    assert result == dest
    assert dest.exists()
    with Image.open(dest) as img:
        assert img.format == spec.pillow_format
        assert img.size == (40, 30)


def test_convert_one_returns_dest_and_creates_parent_dirs(tmp_path: Path) -> None:
    src = _write_source(tmp_path, "PNG")
    dest = tmp_path / "nested" / "deeper" / "out.png"
    result = convert_one(src, dest, "PNG")
    assert result == dest
    assert dest.exists()


# ---------------------------------------------------------------------------
# Transparencia: aplanado a JPEG vs preservación en PNG/WEBP
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target_fmt", ["JPEG", "JPG"])
def test_alpha_flattened_to_white_for_jpeg(tmp_path: Path, target_fmt: str) -> None:
    src = tmp_path / "transparent.png"
    _transparent_rgba().save(src)
    dest = tmp_path / f"out{resolve_target_format(target_fmt).extension}"

    convert_one(src, dest, target_fmt)

    with Image.open(dest) as img:
        assert img.mode == "RGB"  # JPEG no soporta canal alpha
        assert img.getpixel((0, 0)) == (255, 255, 255)  # transparente → blanco


@pytest.mark.parametrize("target_fmt", ["PNG", "WEBP"])
def test_alpha_preserved_for_png_and_webp(tmp_path: Path, target_fmt: str) -> None:
    src = tmp_path / "transparent.png"
    _transparent_rgba().save(src)
    dest = tmp_path / f"out{resolve_target_format(target_fmt).extension}"

    convert_one(src, dest, target_fmt)

    with Image.open(dest) as img:
        assert img.mode == "RGBA"
        assert img.getpixel((0, 0))[3] == 0  # el píxel sigue transparente


@pytest.mark.parametrize("target_fmt", ["PNG", "WEBP"])
def test_opaque_source_stays_rgb_for_png_and_webp(tmp_path: Path, target_fmt: str) -> None:
    src = _write_source(tmp_path, "PNG")  # opaco
    dest = tmp_path / f"out{resolve_target_format(target_fmt).extension}"
    convert_one(src, dest, target_fmt)
    with Image.open(dest) as img:
        assert img.mode == "RGB"


def test_palette_with_transparency_flattened_to_white_for_jpeg(tmp_path: Path) -> None:
    """Una imagen en modo paleta (P) con índice de transparencia también se aplana."""
    src = tmp_path / "palette.png"
    img = Image.new("P", (16, 16), 0)
    img.info["transparency"] = 0  # índice 0 (negro) marcado como transparente
    img.save(src)
    dest = tmp_path / "out.jpg"

    convert_one(src, dest, "JPEG")

    with Image.open(dest) as out:
        assert out.mode == "RGB"
        assert out.getpixel((0, 0)) == (255, 255, 255)


# ---------------------------------------------------------------------------
# Calidad y compresión sin pérdida
# ---------------------------------------------------------------------------


def _noise_source(tmp_path: Path) -> Path:
    src = tmp_path / "noise.png"
    Image.effect_noise((128, 128), 90).convert("RGB").save(src)
    return src


def test_jpeg_quality_affects_output_size(tmp_path: Path) -> None:
    src = _noise_source(tmp_path)
    low = tmp_path / "low.jpg"
    high = tmp_path / "high.jpg"
    convert_one(src, low, "JPEG", quality=20)
    convert_one(src, high, "JPEG", quality=95)
    assert low.stat().st_size < high.stat().st_size


def test_webp_lossy_quality_affects_output_size(tmp_path: Path) -> None:
    src = _noise_source(tmp_path)
    low = tmp_path / "low.webp"
    high = tmp_path / "high.webp"
    convert_one(src, low, "WEBP", quality=10)
    convert_one(src, high, "WEBP", quality=95)
    assert low.stat().st_size < high.stat().st_size


def test_webp_lossless_ignores_quality(tmp_path: Path) -> None:
    src = _noise_source(tmp_path)
    a = tmp_path / "a.webp"
    b = tmp_path / "b.webp"
    convert_one(src, a, "WEBP", quality=1, webp_lossless=True)
    convert_one(src, b, "WEBP", quality=100, webp_lossless=True)
    assert a.read_bytes() == b.read_bytes()


def test_png_quality_is_ignored(tmp_path: Path) -> None:
    src = _write_source(tmp_path, "PNG")
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    convert_one(src, a, "PNG", quality=1)
    convert_one(src, b, "PNG", quality=100)
    assert a.read_bytes() == b.read_bytes()


@pytest.mark.parametrize("quality", [-50, 150, 1000])
def test_out_of_range_quality_is_clamped(tmp_path: Path, quality: int) -> None:
    """El pipeline acota la calidad a [0, 100] sin lanzar (la validación estricta vive en el API)."""
    src = _noise_source(tmp_path)
    clamped = tmp_path / "clamped.jpg"
    reference = tmp_path / "ref.jpg"
    convert_one(src, clamped, "JPEG", quality=quality)
    convert_one(src, reference, "JPEG", quality=100 if quality > 0 else 0)
    assert clamped.stat().st_size == reference.stat().st_size


@pytest.mark.parametrize(
    ("target_fmt", "lossless_kwargs"),
    [("PNG", {}), ("WEBP", {"webp_lossless": True})],
)
def test_lossless_formats_roundtrip_exactly(
    tmp_path: Path, target_fmt: str, lossless_kwargs: dict
) -> None:
    """PNG y WEBP lossless conservan los píxeles exactos de una imagen opaca."""
    original = _opaque_varied((24, 18))
    src = tmp_path / "src.png"
    original.save(src)
    dest = tmp_path / f"out{resolve_target_format(target_fmt).extension}"

    convert_one(src, dest, target_fmt, **lossless_kwargs)

    with Image.open(dest) as img:
        assert img.convert("RGB").tobytes() == original.tobytes()


# ---------------------------------------------------------------------------
# convert_batch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target_fmt", SUPPORTED_FORMATS)
def test_convert_batch_happy_path_each_format(tmp_path: Path, target_fmt: str) -> None:
    paths = [_write_source(tmp_path / f"d{i}", "PNG") for i in range(3)]
    zip_path = tmp_path / "out" / "convert.zip"

    report = convert_batch(paths, target_fmt, zip_path)

    assert isinstance(report, ConvertBatchReport)
    assert report.expected == 3
    assert report.produced == 3
    assert all(item.status == "succeeded" for item in report.items)
    ext = resolve_target_format(target_fmt).extension
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.namelist()
    assert len(members) == 3
    assert all(member.endswith(ext) for member in members)


def test_convert_batch_mixed_source_formats_to_single_target(tmp_path: Path) -> None:
    """Formatos de entrada mixtos → un único formato destino (escenario de spec)."""
    png = _write_source(tmp_path / "a", "PNG")
    jpeg = _write_source(tmp_path / "b", "JPEG")
    webp = _write_source(tmp_path / "c", "WEBP")
    zip_path = tmp_path / "convert.zip"

    report = convert_batch([png, jpeg, webp], "WEBP", zip_path)

    assert report.produced == 3
    with zipfile.ZipFile(zip_path) as archive:
        members = sorted(archive.namelist())
    assert members == ["src_JPEG.webp", "src_PNG.webp", "src_WEBP.webp"]


def test_convert_batch_preserves_original_stems(tmp_path: Path) -> None:
    gato = tmp_path / "gato.png"
    perro = tmp_path / "perro.jpeg"
    _opaque_varied().save(gato)
    _opaque_varied().save(perro, format="JPEG")
    zip_path = tmp_path / "convert.zip"

    convert_batch([gato, perro], "PNG", zip_path)

    with zipfile.ZipFile(zip_path) as archive:
        assert sorted(archive.namelist()) == ["gato.png", "perro.png"]


def test_convert_batch_dedupes_colliding_names(tmp_path: Path) -> None:
    a = _write_source(tmp_path / "a", "PNG")
    b = _write_source(tmp_path / "b", "PNG")
    # Mismos stems desde carpetas distintas.
    a = a.rename(a.with_name("cat.png"))
    b = b.rename(b.with_name("cat.png"))
    zip_path = tmp_path / "convert.zip"

    report = convert_batch([a, b], "PNG", zip_path)

    assert report.produced == 2
    with zipfile.ZipFile(zip_path) as archive:
        assert sorted(archive.namelist()) == ["cat.png", "cat_2.png"]


def test_convert_batch_continues_after_failed_item(tmp_path: Path) -> None:
    good = _write_source(tmp_path / "g", "PNG")
    good = good.rename(good.with_name("good.png"))
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(b"not a real image")
    zip_path = tmp_path / "convert.zip"

    report = convert_batch([good, corrupt], "JPEG", zip_path)

    assert report.expected == 2
    assert report.produced == 1
    statuses = {item.input_path.name: item.status for item in report.items}
    assert statuses == {"good.png": "succeeded", "corrupt.png": "failed"}
    failed = next(item for item in report.items if item.status == "failed")
    assert failed.error is not None
    assert failed.archive_member is None
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == ["good.jpg"]


def test_convert_batch_all_items_fail(tmp_path: Path) -> None:
    bad_a = tmp_path / "a.png"
    bad_b = tmp_path / "b.png"
    bad_a.write_bytes(b"garbage-a")
    bad_b.write_bytes(b"garbage-b")
    zip_path = tmp_path / "convert.zip"

    report = convert_batch([bad_a, bad_b], "PNG", zip_path)

    assert report.expected == 2
    assert report.produced == 0
    assert all(item.status == "failed" for item in report.items)
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == []


def test_convert_batch_empty_input(tmp_path: Path) -> None:
    zip_path = tmp_path / "convert.zip"
    report = convert_batch([], "PNG", zip_path)
    assert report.expected == 0
    assert report.produced == 0
    assert zip_path.exists()


def test_convert_batch_report_to_dict_shape(tmp_path: Path) -> None:
    good = _write_source(tmp_path / "g", "PNG")
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(b"nope")
    zip_path = tmp_path / "out.zip"

    data = convert_batch([good, corrupt], "WEBP", zip_path).to_dict()

    assert data["zip_path"] == str(zip_path)
    assert data["expected"] == 2
    assert data["produced"] == 1
    assert isinstance(data["items"], list) and len(data["items"]) == 2
    keys = set(data["items"][0].keys())
    assert keys == {"input", "status", "archive_member", "error"}


def test_convert_item_result_to_dict() -> None:
    item = ConvertItemResult(
        input_path=Path("/imgs/gato.png"), status="succeeded", archive_member="gato.webp"
    )
    assert item.to_dict() == {
        "input": "/imgs/gato.png",
        "status": "succeeded",
        "archive_member": "gato.webp",
        "error": None,
    }


def test_convert_batch_emits_progress_events(tmp_path: Path) -> None:
    good = _write_source(tmp_path / "g", "PNG")
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(b"broken")
    reporter = _RecordingReporter()

    convert_batch([good, corrupt], "PNG", tmp_path / "out.zip", reporter=reporter)

    types = [e.type for e in reporter.events]
    assert types[0] == ProgressEventType.STARTED
    assert types[-1] == ProgressEventType.COMPLETED
    assert all(e.phase is Phase.CONVERT for e in reporter.events)
    # Un evento PROGRESS por cada imagen (2) y un WARNING por la que falló.
    assert sum(1 for e in reporter.events if e.type == ProgressEventType.PROGRESS) == 2
    assert sum(1 for e in reporter.events if e.type == ProgressEventType.WARNING) == 1
    started = next(e for e in reporter.events if e.type == ProgressEventType.STARTED)
    assert started.total == 2


def test_default_quality_constant() -> None:
    assert DEFAULT_QUALITY == 90
