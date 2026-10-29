"""Image loading, validation, cropping and downsampling."""

from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core import config
from app.schemas.settings import CropBox


class InvalidImageError(ValueError):
    """The upload is not an acceptable image (type, size, or corrupt data)."""


def load_image(source: bytes | str | Path) -> np.ndarray:
    """Decode an upload into an RGB uint8 array.

    Validates size and format, applies EXIF orientation, flattens transparency onto white and
    downscales very large images. EXIF and other metadata are dropped because only pixels are kept.
    """
    data = source if isinstance(source, bytes) else Path(source).read_bytes()
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise InvalidImageError(f"file is larger than {config.MAX_UPLOAD_BYTES // 1_048_576} MB")

    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in config.ALLOWED_FORMATS:
            raise InvalidImageError("only PNG, JPG and WebP images are supported")
        if img.width * img.height > config.MAX_PIXELS:
            raise InvalidImageError("image has too many pixels")
        img.load()
    except InvalidImageError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise InvalidImageError("could not read the image; the file may be corrupt") from None

    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        img = Image.alpha_composite(background, rgba)
    img = img.convert("RGB")
    if max(img.size) > config.MAX_SIDE:
        img.thumbnail((config.MAX_SIDE, config.MAX_SIDE), Image.Resampling.LANCZOS)
    return np.ascontiguousarray(np.asarray(img, dtype=np.uint8))


def crop_image(image: np.ndarray, box: CropBox | None) -> np.ndarray:
    """Crop using fractional coordinates. Always returns at least a 1x1 region."""
    if box is None:
        return image
    h, w = image.shape[:2]
    left = min(int(round(box.left * w)), w - 1)
    top = min(int(round(box.top * h)), h - 1)
    right = max(int(round(box.right * w)), left + 1)
    bottom = max(int(round(box.bottom * h)), top + 1)
    return image[top:bottom, left:right]


def downsample_to_width(image: np.ndarray, width: int) -> np.ndarray:
    """Resize to one pixel per stitch. Height follows the aspect ratio (stitches are square)."""
    h, w = image.shape[:2]
    new_h = max(1, round(h * width / w))
    if new_h > config.MAX_STITCH_HEIGHT:
        raise ValueError(
            f"the pattern would be {width} x {new_h} stitches; "
            f"crop the image or reduce the width (maximum height is {config.MAX_STITCH_HEIGHT})"
        )
    interpolation = cv2.INTER_AREA if width < w else cv2.INTER_LINEAR
    return cv2.resize(image, (width, new_h), interpolation=interpolation)
