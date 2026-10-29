"""Color reduction with k-means in CIELAB."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans


def kmeans_centers(lab: np.ndarray, weights: np.ndarray, k: int, seed: int = 42) -> np.ndarray:
    """Cluster unique colors (weighted by pixel count) and return up to k centers in Lab.

    Running on unique colors keeps this fast even for noisy photos. If the image already has k or
    fewer distinct colors, each color is its own center.
    """
    if len(lab) <= k:
        return np.asarray(lab, dtype=np.float64)
    model = KMeans(n_clusters=k, n_init=4, random_state=seed)
    model.fit(lab, sample_weight=weights)
    return model.cluster_centers_
