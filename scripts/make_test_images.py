"""Generate small synthetic test images so tests and the benchmark need no real photos.

Usage: python scripts/make_test_images.py
These stand in for the real photo set from the Week 1 checklist; add your own photos to
data/test_images/ (git-ignored) and run the CLI on them too.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

OUT = Path(__file__).resolve().parents[1] / "data" / "test_images" / "synthetic"
SIZE = 800


def _save(name: str, rgb: np.ndarray) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT / name), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def sunflower() -> np.ndarray:
    """Soft sky gradient, green stem and leaves, yellow petals, brown center (photo-like blur)."""
    rng = np.random.default_rng(1)
    y = np.linspace(0, 1, SIZE)[:, None]
    sky = np.stack([120 + 100 * y, 175 + 60 * y, 235 - 20 * y], axis=-1) * np.ones((1, SIZE, 1))
    img = sky.astype(np.uint8).copy()
    cv2.line(img, (400, 780), (400, 430), (40, 120, 50), 22, cv2.LINE_AA)
    for sign in (-1, 1):
        cv2.ellipse(
            img,
            (400 + sign * 70, 620),
            (80, 28),
            sign * -30,
            0,
            360,
            (50, 140, 60),
            -1,
            cv2.LINE_AA,
        )
    for angle in range(0, 360, 20):
        cv2.ellipse(img, (400, 330), (150, 40), angle, 0, 360, (250, 200, 30), -1, cv2.LINE_AA)
    cv2.circle(img, (400, 330), 85, (90, 55, 25), -1, cv2.LINE_AA)
    cv2.circle(img, (400, 330), 55, (60, 35, 18), -1, cv2.LINE_AA)
    img = cv2.GaussianBlur(img, (0, 0), 2.0)
    noise = rng.normal(0, 4, img.shape)
    return np.clip(img + noise, 0, 255).astype(np.uint8)


def sunset_gradient() -> np.ndarray:
    y = np.linspace(0, 1, SIZE)[:, None]
    x = np.linspace(0, 1, SIZE)[None, :]
    r = 255 * (0.3 + 0.7 * y) * np.ones_like(x)
    g = 255 * (0.1 + 0.5 * y * (1 - 0.3 * x))
    b = 255 * (0.5 * (1 - y) + 0.2 * x)
    return np.clip(np.stack([r, g, b], axis=-1), 0, 255).astype(np.uint8)


def logo_shapes() -> np.ndarray:
    img = np.full((SIZE, SIZE, 3), 245, np.uint8)
    cv2.circle(img, (400, 400), 300, (200, 30, 40), -1, cv2.LINE_AA)
    cv2.circle(img, (400, 400), 200, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.rectangle(img, (300, 300), (500, 500), (20, 60, 160), -1, cv2.LINE_AA)
    pts = np.array([[400, 120], [470, 330], [330, 330]], np.int32)
    cv2.fillPoly(img, [pts], (250, 190, 20), cv2.LINE_AA)
    return img


def noisy_texture() -> np.ndarray:
    """Worst case for color reduction: many distinct colors."""
    rng = np.random.default_rng(7)
    return rng.integers(0, 256, (SIZE, SIZE, 3), dtype=np.uint8)


def low_contrast() -> np.ndarray:
    rng = np.random.default_rng(3)
    base = np.full((SIZE, SIZE, 3), (150, 145, 140), np.float64)
    cv2.circle(base, (400, 400), 250, (165, 158, 150), -1, cv2.LINE_AA)
    return np.clip(base + rng.normal(0, 3, base.shape), 0, 255).astype(np.uint8)


def main() -> None:
    for name, fn in [
        ("sunflower.png", sunflower),
        ("sunset_gradient.png", sunset_gradient),
        ("logo_shapes.png", logo_shapes),
        ("noisy_texture.png", noisy_texture),
        ("low_contrast.png", low_contrast),
    ]:
        _save(name, fn())
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
