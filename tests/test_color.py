import numpy as np

from app.services.imaging.color import ciede2000_matrix, rgb_to_lab


def test_white_and_black_in_lab():
    lab = rgb_to_lab(np.array([[255, 255, 255], [0, 0, 0]], dtype=np.uint8))
    assert lab[0, 0] > 99.9 and abs(lab[0, 1]) < 0.1 and abs(lab[0, 2]) < 0.1
    assert lab[1, 0] < 0.1


def test_rgb_to_lab_accepts_image_and_vector():
    assert rgb_to_lab(np.zeros((4, 5, 3), dtype=np.uint8)).shape == (4, 5, 3)
    assert rgb_to_lab(np.array([10, 20, 30], dtype=np.uint8)).shape == (3,)


def test_ciede2000_identity_and_ordering():
    lab = rgb_to_lab(np.array([[255, 0, 0], [250, 5, 5], [0, 0, 255]], dtype=np.uint8))
    d = ciede2000_matrix(lab, lab)
    assert np.allclose(np.diag(d), 0)
    assert d[0, 1] < d[0, 2]  # near-red is closer to red than blue is


def test_chunking_gives_same_answer():
    rng = np.random.default_rng(1)
    a = rng.uniform(0, 100, (50, 3))
    b = rng.uniform(-50, 50, (7, 3))
    assert np.allclose(ciede2000_matrix(a, b, chunk=8), ciede2000_matrix(a, b, chunk=1000))
