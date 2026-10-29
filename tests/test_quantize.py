import numpy as np

from app.services.imaging.color import rgb_to_lab
from app.services.imaging.quantize import kmeans_centers


def _unique_lab(img):
    uniq, counts = np.unique(img.reshape(-1, 3), axis=0, return_counts=True)
    return rgb_to_lab(uniq), counts


def test_never_more_centers_than_requested(noise):
    lab, counts = _unique_lab(noise)
    assert len(kmeans_centers(lab, counts, k=8)) == 8


def test_few_distinct_colors_are_kept_as_is(bands):
    lab, counts = _unique_lab(bands)
    assert len(kmeans_centers(lab, counts, k=10)) == 3


def test_deterministic_for_same_seed(noise):
    lab, counts = _unique_lab(noise)
    a = kmeans_centers(lab, counts, k=6, seed=5)
    b = kmeans_centers(lab, counts, k=6, seed=5)
    assert np.array_equal(a, b)
