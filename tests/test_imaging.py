import io

import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from app.core import config
from app.schemas.settings import CropBox
from app.services.imaging.io import (
    InvalidImageError,
    crop_image,
    downsample_to_width,
    load_image,
)
from tests.conftest import encode


def test_loads_png_jpeg_webp(bands):
    for fmt in ("PNG", "JPEG", "WEBP"):
        out = load_image(encode(bands, fmt))
        assert out.shape == bands.shape and out.dtype == np.uint8


def test_rejects_unsupported_format(bands):
    with pytest.raises(InvalidImageError, match="PNG, JPG and WebP"):
        load_image(encode(bands, "GIF"))


def test_rejects_garbage_and_empty():
    for data in (b"definitely not an image", b""):
        with pytest.raises(InvalidImageError):
            load_image(data)


def test_rejects_truncated_image(noise):
    data = encode(noise, "PNG")
    assert len(data) > 1000  # make sure slicing really removes image data
    with pytest.raises(InvalidImageError):
        load_image(data[: len(data) // 2])


def test_rejects_oversized_file(monkeypatch, bands):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 100)
    with pytest.raises(InvalidImageError, match="larger than"):
        load_image(encode(bands, "PNG"))


def test_rejects_too_many_pixels(monkeypatch, bands):
    monkeypatch.setattr(config, "MAX_PIXELS", 100)
    with pytest.raises(InvalidImageError, match="too many pixels"):
        load_image(encode(bands, "PNG"))


def test_large_images_are_downscaled(monkeypatch, bands):
    monkeypatch.setattr(config, "MAX_SIDE", 45)
    out = load_image(encode(bands, "PNG"))
    assert max(out.shape[:2]) == 45


def test_exif_orientation_is_applied(bands):
    img = Image.fromarray(bands)
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees clockwise to display
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    out = load_image(buf.getvalue())
    assert out.shape[:2] == (90, 60)  # width and height swapped


def test_transparency_is_flattened_onto_white():
    rgba = np.zeros((10, 10, 4), dtype=np.uint8)  # fully transparent black
    out = load_image(encode(rgba, "PNG"))
    assert (out == 255).all()


def test_crop_box_validation():
    with pytest.raises(ValidationError):
        CropBox(left=0.6, right=0.4)
    with pytest.raises(ValidationError):
        CropBox(left=-0.1)


def test_crop_image(bands):
    cropped = crop_image(bands, CropBox(left=0.0, top=0.0, right=1 / 3, bottom=0.5))
    assert cropped.shape[:2] == (30, 30)
    assert (cropped == (200, 30, 40)).all()
    assert crop_image(bands, None) is bands


def test_crop_extreme_box_never_empty(bands):
    out = crop_image(bands, CropBox(left=0.999, top=0.999, right=1.0, bottom=1.0))
    assert out.size > 0


def test_downsample_keeps_aspect_ratio(bands):
    small = downsample_to_width(bands, 30)
    assert small.shape[:2] == (20, 30)


def test_downsample_rejects_excessive_height():
    tall = np.zeros((5000, 100, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="crop the image"):
        downsample_to_width(tall, 100)
