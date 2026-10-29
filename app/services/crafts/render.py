"""Render a grid pattern as an image: colored cells, optional symbols and chart gridlines."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.schemas.pattern import GridPatternResult

LIGHT_LINE = (205, 205, 205)
BOLD_LINE = (70, 70, 70)


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.load_default(size=size)
    except (TypeError, OSError):  # very old Pillow or no FreeType: fixed-size bitmap font
        return ImageFont.load_default()


def _glyph_tile(symbol: str, cell: int) -> np.ndarray:
    """A cell-sized alpha mask (0 to 1) with the symbol centered."""
    tile = Image.new("L", (cell, cell), 0)
    ImageDraw.Draw(tile).text(
        (cell / 2, cell / 2), symbol, fill=255, font=_font(max(6, int(cell * 0.72))), anchor="mm"
    )
    return np.asarray(tile, dtype=np.float32) / 255.0


def render_grid_preview(
    result: GridPatternResult,
    cell_px: int = 12,
    show_symbols: bool = True,
    show_grid: bool = True,
) -> Image.Image:
    """Return an RGB image of size (width * cell_px, height * cell_px).

    Everything is vectorised with NumPy, so a 250 x 250 pattern renders quickly.
    """
    if cell_px < 1:
        raise ValueError("cell_px must be at least 1")
    grid = result.grid_array()
    h, w = grid.shape
    colors = np.array([e.rgb for e in result.palette], dtype=np.uint8)
    img = np.kron(colors[grid], np.ones((cell_px, cell_px, 1), dtype=np.uint8)).astype(np.float32)

    if show_symbols and cell_px >= 8:
        for idx, entry in enumerate(result.palette):
            cell_mask = np.kron(grid == idx, np.ones((cell_px, cell_px), dtype=bool))
            alpha = np.tile(_glyph_tile(entry.symbol, cell_px), (h, w)) * cell_mask
            luminance = 0.299 * entry.rgb[0] + 0.587 * entry.rgb[1] + 0.114 * entry.rgb[2]
            ink = np.array([0, 0, 0] if luminance > 140 else [255, 255, 255], dtype=np.float32)
            img = img * (1 - alpha[..., None]) + ink * alpha[..., None]

    out = np.clip(img, 0, 255).astype(np.uint8)
    if show_grid and cell_px >= 4:
        out[::cell_px, :, :] = LIGHT_LINE
        out[:, ::cell_px, :] = LIGHT_LINE
        bold = 10 * cell_px
        out[::bold, :, :] = BOLD_LINE
        out[:, ::bold, :] = BOLD_LINE
    return Image.fromarray(out, mode="RGB")
