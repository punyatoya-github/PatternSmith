"""Crop framing: turn "shape + zoom + position" controls into a CropBox.

This is how phone photo editors work, and it is easier to use than dragging four edges: pick a
shape, zoom in, then move the frame. The result is a fractional CropBox so it does not depend on
the image resolution.
"""

from __future__ import annotations

from app.schemas.settings import CropBox

# Label shown in the UI -> width / height. None keeps the photo's own proportions.
ASPECT_PRESETS: dict[str, float | None] = {
    "Whole photo": None,
    "Square (1:1)": 1.0,
    "Portrait (4:5)": 4 / 5,
    "Tall (2:3)": 2 / 3,
    "Landscape (3:2)": 3 / 2,
    "Wide (16:9)": 16 / 9,
}
MAX_ZOOM = 8.0


def compute_crop_box(
    img_w: int,
    img_h: int,
    aspect: float | None = None,
    zoom: float = 1.0,
    pan_x: float = 0.5,
    pan_y: float = 0.5,
) -> CropBox:
    """Largest frame of the wanted shape, shrunk by `zoom`, placed by `pan_x` / `pan_y` (0 to 1).

    pan 0 puts the frame against the left / top edge, 1 against the right / bottom edge.
    """
    if img_w < 1 or img_h < 1:
        raise ValueError("image must have a positive size")
    image_ratio = img_w / img_h
    ratio = aspect if aspect else image_ratio
    if ratio <= 0:
        raise ValueError("aspect must be positive")

    if ratio >= image_ratio:  # frame is wider than the photo: full width, reduced height
        frac_w, frac_h = 1.0, image_ratio / ratio
    else:  # frame is taller than the photo: full height, reduced width
        frac_w, frac_h = ratio / image_ratio, 1.0

    zoom = min(max(zoom, 1.0), MAX_ZOOM)
    frac_w, frac_h = frac_w / zoom, frac_h / zoom
    pan_x, pan_y = min(max(pan_x, 0.0), 1.0), min(max(pan_y, 0.0), 1.0)
    left, top = (1 - frac_w) * pan_x, (1 - frac_h) * pan_y
    return CropBox(left=left, top=top, right=left + frac_w, bottom=top + frac_h)
