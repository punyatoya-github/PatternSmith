"""Color science helpers: sRGB <-> CIELAB and CIEDE2000 distances."""

from __future__ import annotations

import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Convert uint8 sRGB of shape (..., 3) to float64 CIELAB (D65)."""
    arr = np.asarray(rgb, dtype=np.float64) / 255.0
    if arr.ndim == 1:
        return rgb2lab(arr.reshape(1, 1, 3)).reshape(3)
    if arr.ndim == 2:  # a list of colors
        return rgb2lab(arr.reshape(-1, 1, 3)).reshape(-1, 3)
    return rgb2lab(arr)


def ciede2000_matrix(lab_a: np.ndarray, lab_b: np.ndarray, chunk: int = 20_000) -> np.ndarray:
    """Pairwise CIEDE2000 distances: result[i, j] = dE(lab_a[i], lab_b[j]).

    Computed in row chunks so large inputs do not allocate gigabytes of temporaries.
    """
    lab_a = np.asarray(lab_a, dtype=np.float64).reshape(-1, 3)
    lab_b = np.asarray(lab_b, dtype=np.float64).reshape(-1, 3)
    out = np.empty((len(lab_a), len(lab_b)), dtype=np.float64)
    for start in range(0, len(lab_a), chunk):
        block = lab_a[start : start + chunk]
        out[start : start + chunk] = deltaE_ciede2000(block[:, None, :], lab_b[None, :, :])
    return out
