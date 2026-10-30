import os
import time

import gradio as gr
import pytest
from PIL import Image

from app.schemas.pattern import GridPatternResult, InventoryItem, PaletteEntry
from app.schemas.settings import CraftSettings
from app.ui import handlers
from tests.conftest import encode

DEFAULTS = dict(
    craft="cross_stitch",
    width=40,
    colors=8,
    cleanup=2,
    fabric_count=14,
    strands=2,
    aspect="Whole photo",
    zoom=1,
    pan_x=50,
    pan_y=50,
)


@pytest.fixture
def photo(tmp_path, noise):
    path = tmp_path / "photo.png"
    path.write_bytes(encode(noise))
    return str(path)


def test_level_controls_match_presets():
    assert handlers.level_to_controls(1) == (40, 8, 3)
    assert handlers.level_to_controls(5) == (200, 40, 1)


def test_preview_cell_size_is_bounded():
    assert handlers.preview_cell_px(20, 20) == handlers.PREVIEW_MAX_CELL
    assert handlers.preview_cell_px(250, 400) == handlers.PREVIEW_MIN_CELL


def test_crop_preview(tmp_path, bands):
    assert handlers.crop_preview(None, "Whole photo", 1, 50, 50) is None
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"nope")
    assert handlers.crop_preview(str(bad), "Whole photo", 1, 50, 50) is None

    path = tmp_path / "bands.png"
    path.write_bytes(encode(bands))  # 90 x 60
    square = handlers.crop_preview(str(path), "Square (1:1)", 1, 50, 50)
    assert isinstance(square, Image.Image) and square.size == (60, 60)


def test_make_pattern_returns_everything_the_ui_needs(photo):
    preview, summary, legend, pattern = handlers.make_pattern(photo, **DEFAULTS)
    assert isinstance(preview, Image.Image) and preview.width == 40 * 16
    assert "40 × " in summary and "stitches" in summary and "14-count" in summary
    assert (
        "<table class='legend'>" in legend
        and "legend-wrap" in legend
        and legend.count("<tr>") == len(pattern.palette) + 1
    )
    assert isinstance(pattern, GridPatternResult) and len(pattern.palette) <= 8


def test_make_pattern_uses_the_crop_controls(tmp_path, bands):
    path = tmp_path / "bands.png"
    path.write_bytes(encode(bands))
    args = {**DEFAULTS, "width": 30, "colors": 3, "aspect": "Square (1:1)", "pan_x": 0}
    pattern = handlers.make_pattern(str(path), **args)[3]
    assert (pattern.width, pattern.height) == (30, 30)  # square frame
    assert len(pattern.palette) <= 2  # a square at the left edge covers the red and white bands


@pytest.mark.parametrize(
    ("photo_arg", "overrides", "expected"),
    [
        (None, {}, "Add a photo first"),
        ("bad", {}, "can't be used"),
        ("good", {"width": 5}, "out of range"),
        ("good", {"colors": 99}, "out of range"),
    ],
)
def test_make_pattern_errors_are_clear(tmp_path, photo, photo_arg, overrides, expected):
    if photo_arg == "bad":
        bad = tmp_path / "bad.png"
        bad.write_bytes(b"nope")
        photo_arg = str(bad)
    elif photo_arg == "good":
        photo_arg = photo
    with pytest.raises(gr.Error, match=expected):
        handlers.make_pattern(photo_arg, **{**DEFAULTS, **overrides})


def test_make_pattern_explains_too_tall_photos(tmp_path):
    import numpy as np

    path = tmp_path / "tall.png"
    path.write_bytes(encode(np.zeros((2000, 100, 3), dtype=np.uint8)))
    with pytest.raises(gr.Error, match="crop"):
        handlers.make_pattern(str(path), **{**DEFAULTS, "width": 100})


def test_legend_escapes_html():
    entry = PaletteEntry(
        code="<b>1</b>",
        name="<script>alert(1)</script>",
        hex="#fff",
        rgb=(255, 255, 255),
        symbol="<",
        count=3,
    )
    pattern = GridPatternResult(
        width=1, height=1, grid=[[0]], palette=[entry], settings=CraftSettings(width=20)
    )
    item = InventoryItem(
        code=entry.code, name=entry.name, hex=entry.hex, symbol="<", count=3, skeins=1
    )
    html = handlers.legend_html(pattern, [item])
    assert "<script>" not in html and "&lt;script&gt;" in html and "&lt;b&gt;" in html


def test_make_pdf(photo):
    pattern = handlers.make_pattern(photo, **DEFAULTS)[3]
    path = handlers.make_pdf(pattern, "  Garden Gate  ", "letter", "mono")
    assert path.endswith("Garden-Gate.pdf")
    with open(path, "rb") as f:
        assert f.read(4) == b"%PDF"


def test_make_pdf_defaults_blank_title(photo):
    pattern = handlers.make_pattern(photo, **DEFAULTS)[3]
    assert handlers.make_pdf(pattern, "   ", "a4", "tint").endswith("Cross-Stitch-Pattern.pdf")


def test_make_pdf_needs_a_pattern():
    with pytest.raises(gr.Error, match="Make a pattern first"):
        handlers.make_pdf(None, "T", "a4", "tint")


def test_old_pdfs_are_deleted(photo):
    pattern = handlers.make_pattern(photo, **DEFAULTS)[3]
    old = os.path.dirname(handlers.make_pdf(pattern, "Old", "a4", "tint"))
    long_ago = time.time() - handlers.PDF_MAX_AGE_SECONDS - 60
    os.utime(old, (long_ago, long_ago))
    fresh = os.path.dirname(handlers.make_pdf(pattern, "Fresh", "a4", "tint"))  # triggers cleanup
    assert not os.path.exists(old) and os.path.exists(fresh)
