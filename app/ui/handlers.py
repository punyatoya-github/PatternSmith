"""Gradio event handlers. Plain functions, so they can be unit tested without a browser."""

from __future__ import annotations

import html
import re
import shutil
import tempfile
import time
from pathlib import Path

import gradio as gr
from PIL import Image
from pydantic import ValidationError

from app.schemas.pattern import GridPatternResult, InventoryItem
from app.schemas.settings import CROSS_STITCH_LEVELS, CraftSettings
from app.services.crafts.render import render_grid_preview
from app.services.crafts.sizing import FinishedSize
from app.services.generation import generate
from app.services.imaging.framing import ASPECT_PRESETS, compute_crop_box
from app.services.imaging.io import InvalidImageError, crop_image, load_image
from app.services.pdf.cross_stitch_pdf import build_cross_stitch_pdf

PREVIEW_TARGET_PX = 1400  # aim for roughly this size on the longest side
PREVIEW_MIN_CELL, PREVIEW_MAX_CELL = 8, 16  # at least 8 px so symbols stay readable
PDF_DIR_PREFIX = "craft-pdf-"
PDF_MAX_AGE_SECONDS = 60 * 60  # generated PDFs are deleted after an hour


def level_to_controls(level: int) -> tuple[int, int, int]:
    """Complexity slider -> (width, colors, cleanup) values for the fine-tune sliders."""
    return CROSS_STITCH_LEVELS[int(level)]


def _crop_from_controls(image_shape, aspect, zoom, pan_x, pan_y):
    h, w = image_shape[:2]
    return compute_crop_box(
        w, h, ASPECT_PRESETS.get(aspect), float(zoom), float(pan_x) / 100, float(pan_y) / 100
    )


def crop_preview(photo_path, aspect, zoom, pan_x, pan_y) -> Image.Image | None:
    """Show the part of the photo that will be stitched. Returns None until a photo is added."""
    if not photo_path:
        return None
    try:
        image = load_image(photo_path)
    except InvalidImageError:
        return None  # the clear error is shown when the person presses "Make pattern"
    box = _crop_from_controls(image.shape, aspect, zoom, pan_x, pan_y)
    cropped = Image.fromarray(crop_image(image, box))
    cropped.thumbnail((600, 600))
    return cropped


def preview_cell_px(width: int, height: int) -> int:
    return min(PREVIEW_MAX_CELL, max(PREVIEW_MIN_CELL, PREVIEW_TARGET_PX // max(width, height)))


def summary_markdown(pattern: GridPatternResult, size: FinishedSize, seconds: float) -> str:
    s = pattern.settings
    return (
        f"**{pattern.width} × {pattern.height} stitches** in {len(pattern.palette)} colors "
        f"({pattern.total_stitches:,} stitches in total).  \n"
        f"On {s.fabric_count}-count fabric it measures **{size.width_cm} × {size.height_cm} cm** "
        f"({size.width_in} × {size.height_in} in).  \n"
        f"Made in {seconds:.1f} seconds."
    )


def _ink_for(rgb: tuple[int, int, int]) -> str:
    """Black text on light colors, white on dark ones (same rule as the chart preview)."""
    luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return "#000" if luminance > 140 else "#fff"


def legend_html(pattern: GridPatternResult, inventory: list[InventoryItem]) -> str:
    rows = []
    for entry, item in zip(pattern.palette, inventory, strict=True):
        chip = (
            f"<span class='chip' style='background:{html.escape(entry.hex)};"
            f"color:{_ink_for(entry.rgb)}'>{html.escape(item.symbol)}</span>"
        )
        rows.append(
            "<tr>"
            f"<td>{chip}</td>"
            f"<td>{html.escape(item.code)}</td>"
            f"<td>{html.escape(item.name)}</td>"
            f"<td class='num'>{item.count:,}</td>"
            f"<td class='num'>{item.skeins}</td>"
            "</tr>"
        )
    return (
        "<div class='legend-wrap'><table class='legend'><thead><tr>"
        "<th><span class='lg'>Symbol</span><span class='sm'>Sym</span></th>"
        "<th>DMC</th><th>Name</th>"
        "<th class='num'><span class='lg'>Stitches</span><span class='sm'>Count</span></th>"
        "<th class='num'>Skeins*</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        "<p class='legend-note'>*Approximate. Thread colors look different on screen and on "
        "paper, so buy by the DMC code.</p>"
    )


def _first_error(exc: ValidationError) -> str:
    err = exc.errors()[0]
    field = ".".join(str(part) for part in err["loc"])
    return f"{field}: {err['msg']}"


def make_pattern(
    photo_path,
    craft,
    width,
    colors,
    cleanup,
    fabric_count,
    strands,
    aspect,
    zoom,
    pan_x,
    pan_y,
    progress=gr.Progress(),
):
    """Photo + settings -> (preview image, summary text, legend html, pattern for the PDF step)."""
    if not photo_path:
        raise gr.Error("Add a photo first. Upload one, or paste it from your clipboard.")
    started = time.perf_counter()
    try:
        progress(0.05, desc="Reading your photo")
        image = load_image(photo_path)
        settings = CraftSettings(
            craft=craft,
            width=int(width),
            colors=int(colors),
            cleanup=int(cleanup),
            fabric_count=int(fabric_count),
            strands=int(strands),
            crop=_crop_from_controls(image.shape, aspect, zoom, pan_x, pan_y),
        )
        progress(0.2, desc="Building your pattern")
        output = generate(image, settings)
        progress(0.75, desc="Drawing the preview")
        cell = preview_cell_px(output.pattern.width, output.pattern.height)
        preview = render_grid_preview(output.pattern, cell_px=cell, show_symbols=True)
    except InvalidImageError as exc:
        raise gr.Error(
            f"That photo can't be used: {exc}. Try a PNG, JPG or WebP under 10 MB."
        ) from None
    except ValidationError as exc:
        raise gr.Error(f"A setting is out of range ({_first_error(exc)}).") from None
    except ValueError as exc:
        message = str(exc)
        raise gr.Error(message[:1].upper() + message[1:] + ".") from None

    seconds = time.perf_counter() - started
    return (
        preview,
        summary_markdown(output.pattern, output.size, seconds),
        legend_html(output.pattern, output.inventory),
        output.pattern,
    )


def _delete_old_pdfs(now: float | None = None) -> None:
    """Remove generated PDFs older than an hour (a first step towards the Week 9 retention rule)."""
    now = time.time() if now is None else now
    for folder in Path(tempfile.gettempdir()).glob(f"{PDF_DIR_PREFIX}*"):
        try:
            if now - folder.stat().st_mtime > PDF_MAX_AGE_SECONDS:
                shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            continue


def make_pdf(pattern, title, paper, style, progress=gr.Progress()):
    """Build the printable PDF for the current pattern and return its file path."""
    if pattern is None:
        raise gr.Error("Make a pattern first, then create the PDF.")
    progress(0.1, desc="Laying out the PDF")
    title = (title or "").strip() or "Cross Stitch Pattern"
    pdf = build_cross_stitch_pdf(pattern, title=title, paper=paper, style=style)
    _delete_old_pdfs()
    folder = Path(tempfile.mkdtemp(prefix=PDF_DIR_PREFIX))
    name = re.sub(r"[^A-Za-z0-9_-]+", "-", title).strip("-") or "pattern"
    path = folder / f"{name}.pdf"
    path.write_bytes(pdf)
    return str(path)
