from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image


def encode(arr: np.ndarray, fmt: str = "PNG", **kwargs) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format=fmt, **kwargs)
    return buf.getvalue()


@pytest.fixture
def bands() -> np.ndarray:
    """90 x 60 image: three vertical bands (red, white, blue) of 30 columns each."""
    img = np.zeros((60, 90, 3), dtype=np.uint8)
    img[:, :30] = (200, 30, 40)
    img[:, 30:60] = (255, 255, 255)
    img[:, 60:] = (30, 60, 180)
    return img


@pytest.fixture
def noise() -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, (120, 160, 3), dtype=np.uint8)
