"""Printable cross-stitch PDF (ReportLab): cover, materials and thread list, paginated chart.

Layout rules (Phase 1 plan, Section 8):
- vector symbols, readable in black and white ("mono" style) or on a light tint of the thread color
- bold line every 10 stitches, row and column numbers every 10
- chart pages hold a multiple of 10 columns/rows, so page edges fall on bold lines
- every chart page lists which thread symbols it uses, and where its neighbours are
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

from app.schemas.pattern import GridPatternResult
from app.services.crafts.cross_stitch import CrossStitchGenerator
from app.services.crafts.render import render_grid_preview
from app.services.crafts.sizing import DEFAULT_WASTE_FACTOR, finished_size

Paper = Literal["a4", "letter"]
PdfStyle = Literal["tint", "mono"]

PAPER_SIZES = {"a4": A4, "letter": letter}
NEEDLE_BY_COUNT = {11: "22", 14: "24", 16: "26", 18: "26"}  # tapestry needle sizes (suggested)

MARGIN = 36
HEADER_H = 58
FOOTER_H = 30
LEGEND_H = 58
GUTTER = 18  # space for row / column numbers
CELL_DEFAULT = 10.0
CELL_MAX_SINGLE_PAGE = 16.0
TINT = 0.62  # share of white mixed into a thread color for the "tint" style
ROW_H = 18
FABRIC_MARGIN_CM = 5.0  # extra fabric on every side
ATTRIBUTION = "Color data: craft-color-codes by MakeBead (CC BY 4.0)."


@dataclass(frozen=True)
class ChartLayout:
    cell: float  # cell size in points
    cols: int  # columns per page
    rows: int  # rows per page


def plan_chart_pages(
    width: int, height: int, cols: int, rows: int
) -> list[tuple[int, int, int, int]]:
    """Split the grid into page tiles (col_start, col_end, row_start, row_end), end exclusive,
    in reading order (left to right, then top to bottom)."""
    return [
        (c0, min(c0 + cols, width), r0, min(r0 + rows, height))
        for r0 in range(0, height, rows)
        for c0 in range(0, width, cols)
    ]


def chart_layout(page_w: float, page_h: float, width: int, height: int) -> ChartLayout:
    avail_w = page_w - 2 * MARGIN - GUTTER
    avail_h = page_h - MARGIN - HEADER_H - LEGEND_H - FOOTER_H - GUTTER
    cols = max(10, int(avail_w // CELL_DEFAULT) // 10 * 10)
    rows = max(10, int(avail_h // CELL_DEFAULT) // 10 * 10)
    if width <= cols and height <= rows:  # fits on one page: enlarge the cells
        cell = min(CELL_MAX_SINGLE_PAGE, avail_w / width, avail_h / height)
        return ChartLayout(cell, width, height)
    return ChartLayout(CELL_DEFAULT, cols, rows)


def _tint(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    return tuple((v / 255) * (1 - TINT) + TINT for v in rgb)  # type: ignore[return-value]


class _Builder:
    def __init__(self, result: GridPatternResult, title: str, paper: Paper, style: PdfStyle):
        if paper not in PAPER_SIZES:
            raise ValueError(f"paper must be one of {sorted(PAPER_SIZES)}")
        if style not in ("tint", "mono"):
            raise ValueError("style must be 'tint' or 'mono'")
        self.result, self.title, self.style = result, title, style
        self.page_w, self.page_h = PAPER_SIZES[paper]
        self.grid = result.grid_array()
        self.inventory = CrossStitchGenerator().build_inventory(result)
        self.size = finished_size(result.width, result.height, result.settings.fabric_count)

        self.layout = chart_layout(self.page_w, self.page_h, result.width, result.height)
        self.tiles = plan_chart_pages(
            result.width, result.height, self.layout.cols, self.layout.rows
        )
        self.tile_cols = math.ceil(result.width / self.layout.cols)
        self.tile_rows = math.ceil(result.height / self.layout.rows)

        self.materials = self._materials_lines()
        self.rows_first, self.rows_per_page = self._inventory_capacity()
        inv_rows = len(self.inventory) + 1  # + totals row
        extra = math.ceil(max(0, inv_rows - self.rows_first) / self.rows_per_page)
        self.inventory_pages = 1 + extra
        self.total_pages = 1 + self.inventory_pages + len(self.tiles)

        self.buffer = io.BytesIO()
        self.c = canvas.Canvas(self.buffer, pagesize=(self.page_w, self.page_h))
        self.c.setTitle(title)
        self.c.setAuthor("AI Craft Pattern Generator")
        self.c.setSubject("Cross stitch pattern")
        self.page_no = 0

    # ---------- shared page furniture ----------
    def _new_page(self, subtitle: str = "") -> None:
        if self.page_no:
            self.c.showPage()
        self.page_no += 1
        c = self.c
        c.setFillGray(0)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(MARGIN, self.page_h - MARGIN - 12, self.title)
        c.setFont("Helvetica", 8)
        c.setFillGray(0.35)
        c.drawRightString(
            self.page_w - MARGIN,
            self.page_h - MARGIN - 12,
            f"Page {self.page_no} of {self.total_pages}",
        )
        if subtitle:
            c.drawString(MARGIN, self.page_h - MARGIN - 26, subtitle)
        s = self.result.settings
        c.setFont("Helvetica", 7)
        c.drawCentredString(
            self.page_w / 2,
            MARGIN - 8,
            f"AI Craft Pattern Generator | DMC cross stitch | {self.result.width} x "
            f"{self.result.height} stitches | {len(self.result.palette)} colors | "
            f"{s.fabric_count}-count | seed {s.seed}",
        )
        c.setFillGray(0)

    # ---------- page 1: cover ----------
    def draw_cover(self) -> None:
        self._new_page()
        c, r = self.c, self.result
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(self.page_w / 2, self.page_h - 110, self.title)
        c.setFont("Helvetica", 12)
        c.setFillGray(0.3)
        c.drawCentredString(self.page_w / 2, self.page_h - 132, "Counted cross stitch pattern")
        c.setFillGray(0)

        cell_px = max(2, min(12, 600 // r.width))
        preview = render_grid_preview(r, cell_px=cell_px, show_symbols=False, show_grid=False)
        box_w, box_h = self.page_w - 2 * MARGIN - 40, 420
        scale = min(box_w / preview.width, box_h / preview.height)
        w, h = preview.width * scale, preview.height * scale
        x, y = (self.page_w - w) / 2, self.page_h - 160 - h
        c.drawImage(ImageReader(preview), x, y, width=w, height=h)
        c.setStrokeGray(0.5)
        c.setLineWidth(0.5)
        c.rect(x, y, w, h, stroke=1, fill=0)

        s = self.result.settings
        facts = [
            ("Size", f"{r.width} x {r.height} stitches ({r.total_stitches:,} total)"),
            ("Colors", f"{len(r.palette)} DMC colors"),
            ("Fabric", f"{s.fabric_count}-count Aida or evenweave"),
            (
                "Finished size",
                f"{self.size.width_cm} x {self.size.height_cm} cm "
                f"({self.size.width_in} x {self.size.height_in} in)",
            ),
            ("Chart pages", f"{len(self.tiles)}"),
        ]
        top = y - 34
        for i, (label, value) in enumerate(facts):
            c.setFont("Helvetica-Bold", 10)
            c.drawString(MARGIN + 60, top - i * 16, label)
            c.setFont("Helvetica", 10)
            c.drawString(MARGIN + 170, top - i * 16, value)

    # ---------- materials + thread inventory ----------
    def _materials_lines(self) -> list[tuple[str, str]]:
        s = self.result.settings
        w_cm = self.size.width_cm + 2 * FABRIC_MARGIN_CM
        h_cm = self.size.height_cm + 2 * FABRIC_MARGIN_CM
        w_in, h_in = round(w_cm / 2.54, 1), round(h_cm / 2.54, 1)
        skeins = sum(item.skeins for item in self.inventory)
        return [
            (
                "Fabric",
                f"{s.fabric_count}-count Aida or evenweave, at least {w_cm:.0f} x {h_cm:.0f} cm "
                f"({w_in} x {h_in} in). This includes {FABRIC_MARGIN_CM:.0f} cm of spare "
                "fabric on every side.",
            ),
            (
                "Thread",
                f"DMC six-strand embroidery floss in {len(self.inventory)} colors. Use "
                f"{s.strands} strand{'s' if s.strands != 1 else ''} for cross stitches. About "
                f"{skeins} skeins in total (see list below).",
            ),
            ("Needle", f"Tapestry needle, size {NEEDLE_BY_COUNT[s.fabric_count]} (suggested)."),
            ("Also needed", "Embroidery hoop or frame, sharp small scissors."),
            (
                "Note",
                "* Skein counts are approximate: they assume full cross stitches and an "
                f"allowance of {DEFAULT_WASTE_FACTOR}x for the back of the work and thread "
                "tails, and each color is rounded up. Thread colors differ slightly on "
                f"screen and on paper; buy by the DMC code. {ATTRIBUTION}",
            ),
        ]

    def _wrapped_materials(self) -> list[tuple[str, list[str]]]:
        max_w = self.page_w - 2 * MARGIN - 90
        return [(label, simpleSplit(text, "Helvetica", 9, max_w)) for label, text in self.materials]

    def _materials_height(self) -> float:
        return sum(len(lines) * 12 + 6 for _, lines in self._wrapped_materials()) + 30

    def _inventory_capacity(self) -> tuple[int, int]:
        table_top_first = self.page_h - MARGIN - HEADER_H - self._materials_height() - 24
        bottom = MARGIN + 14
        first = int((table_top_first - bottom) // ROW_H)
        per_page = int((self.page_h - MARGIN - HEADER_H - 24 - bottom) // ROW_H)
        return max(1, first), max(1, per_page)

    def _draw_table_header(self, y: float) -> None:
        c = self.c
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN + 6, y, "Sym")
        c.drawString(MARGIN + 90, y, "DMC")
        c.drawString(MARGIN + 150, y, "Name")
        c.drawRightString(self.page_w - MARGIN - 80, y, "Stitches")
        c.drawRightString(self.page_w - MARGIN - 8, y, "Skeins*")
        c.setStrokeGray(0.3)
        c.setLineWidth(0.8)
        c.line(MARGIN, y - 5, self.page_w - MARGIN, y - 5)

    def _draw_inventory_row(self, y: float, index: int) -> None:
        c = self.c
        if index == len(self.inventory):  # totals row
            c.setStrokeGray(0.3)
            c.setLineWidth(0.8)
            c.line(MARGIN, y + 12, self.page_w - MARGIN, y + 12)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(MARGIN + 150, y, "Total")
            c.drawRightString(
                self.page_w - MARGIN - 80, y, f"{sum(i.count for i in self.inventory):,}"
            )
            c.drawRightString(
                self.page_w - MARGIN - 8, y, f"{sum(i.skeins for i in self.inventory)}"
            )
            return
        item = self.inventory[index]
        c.setFont("Helvetica-Bold", 11)
        c.drawString(MARGIN + 8, y, item.symbol)
        rgb = self.result.palette[index].rgb
        c.setFillColorRGB(*(v / 255 for v in rgb))
        c.setStrokeGray(0.4)
        c.setLineWidth(0.4)
        c.rect(MARGIN + 38, y - 3, 32, 12, stroke=1, fill=1)
        c.setFillGray(0)
        c.setFont("Helvetica", 9)
        c.drawString(MARGIN + 90, y, item.code)
        c.drawString(MARGIN + 150, y, item.name)
        c.drawRightString(self.page_w - MARGIN - 80, y, f"{item.count:,}")
        c.drawRightString(self.page_w - MARGIN - 8, y, str(item.skeins))

    def draw_materials_and_inventory(self) -> None:
        total_rows = len(self.inventory) + 1
        index = 0
        for page in range(self.inventory_pages):
            first = page == 0
            self._new_page("Materials and thread list" if first else "Thread list (continued)")
            y = self.page_h - MARGIN - HEADER_H
            if first:
                for label, lines in self._wrapped_materials():
                    self.c.setFont("Helvetica-Bold", 9)
                    self.c.drawString(MARGIN, y, label)
                    self.c.setFont("Helvetica", 9)
                    for line in lines:
                        self.c.drawString(MARGIN + 90, y, line)
                        y -= 12
                    y -= 6
                y -= 24
            else:
                y -= 6
            self._draw_table_header(y)
            y -= ROW_H
            capacity = self.rows_first if first else self.rows_per_page
            for _ in range(min(capacity, total_rows - index)):
                self._draw_inventory_row(y, index)
                index += 1
                y -= ROW_H

    # ---------- chart pages ----------
    def _draw_minimap(self, tile_index: int) -> None:
        c, size = self.c, 6
        tc, tr = tile_index % self.tile_cols, tile_index // self.tile_cols
        x0 = self.page_w - MARGIN - self.tile_cols * size
        y0 = self.page_h - MARGIN - 28 - self.tile_rows * size
        for row in range(self.tile_rows):
            for col in range(self.tile_cols):
                active = (col, row) == (tc, tr)
                c.setFillGray(0.15 if active else 1)
                c.setStrokeGray(0.4)
                c.setLineWidth(0.4)
                c.rect(x0 + col * size, y0 + (self.tile_rows - 1 - row) * size, size, size, 1, 1)
        c.setFillGray(0)

    def _draw_page_legend(self, used: np.ndarray) -> None:
        c = self.c
        item_w = 58
        per_line = max(1, int((self.page_w - 2 * MARGIN) // item_w))
        x0 = MARGIN
        y0 = MARGIN + FOOTER_H + LEGEND_H - 16
        for n, idx in enumerate(used):
            col, line = n % per_line, n // per_line
            x, y = x0 + col * item_w, y0 - line * 11
            entry = self.result.palette[int(idx)]
            c.setFillColorRGB(*(v / 255 for v in entry.rgb))
            c.setStrokeGray(0.4)
            c.setLineWidth(0.4)
            c.rect(x, y - 1, 9, 9, stroke=1, fill=1)
            c.setFillGray(0)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(x + 12, y, f"{entry.symbol} {entry.code}")

    def draw_chart_page(self, tile_index: int) -> None:
        c0, c1, r0, r1 = self.tiles[tile_index]
        sub = self.grid[r0:r1, c0:c1]
        n_rows, n_cols = sub.shape
        cell = self.layout.cell
        tc, tr = tile_index % self.tile_cols, tile_index // self.tile_cols

        notes = [f"Columns {c0 + 1}-{c1}, rows {r0 + 1}-{r1}"]
        if tc + 1 < self.tile_cols:
            notes.append(f"continues right: page {self.page_no + 2}")
        if tr + 1 < self.tile_rows:
            below = 1 + self.inventory_pages + (tile_index + self.tile_cols) + 1
            notes.append(f"continues down: page {below}")
        self._new_page(" | ".join(notes))
        self._draw_minimap(tile_index)

        c = self.c
        gx = MARGIN + GUTTER
        top = self.page_h - MARGIN - HEADER_H - GUTTER
        right, bottom = gx + n_cols * cell, top - n_rows * cell

        # cell fills (skipped in mono style)
        if self.style == "tint":
            for idx in np.unique(sub):
                c.setFillColorRGB(*_tint(self.result.palette[int(idx)].rgb))
                for y, x in zip(*np.nonzero(sub == idx), strict=True):
                    c.rect(gx + x * cell, top - (y + 1) * cell, cell, cell, stroke=0, fill=1)

        # thin grid, then bold lines every 10 stitches (absolute positions)
        c.setStrokeGray(0.62)
        c.setLineWidth(0.25)
        for i in range(n_cols + 1):
            c.line(gx + i * cell, top, gx + i * cell, bottom)
        for j in range(n_rows + 1):
            c.line(gx, top - j * cell, right, top - j * cell)
        c.setStrokeGray(0)
        c.setLineWidth(0.9)
        for i in range(n_cols + 1):
            if (c0 + i) % 10 == 0:
                c.line(gx + i * cell, top, gx + i * cell, bottom)
        for j in range(n_rows + 1):
            if (r0 + j) % 10 == 0:
                c.line(gx, top - j * cell, right, top - j * cell)
        c.rect(gx, bottom, right - gx, top - bottom, stroke=1, fill=0)

        # symbols
        symbols = [e.symbol for e in self.result.palette]
        c.setFillGray(0)
        c.setFont("Helvetica-Bold", cell * 0.68)
        baseline = cell * 0.5 - cell * 0.68 * 0.36
        for y in range(n_rows):
            for x in range(n_cols):
                c.drawCentredString(
                    gx + (x + 0.5) * cell, top - (y + 1) * cell + baseline, symbols[sub[y, x]]
                )

        # numbers every 10
        c.setFont("Helvetica", 7)
        for i in range(n_cols):
            if (c0 + i + 1) % 10 == 0:
                c.drawCentredString(gx + (i + 0.5) * cell, top + 5, str(c0 + i + 1))
        for j in range(n_rows):
            if (r0 + j + 1) % 10 == 0:
                c.drawRightString(gx - 3, top - (j + 0.5) * cell - 2.5, str(r0 + j + 1))

        self._draw_page_legend(np.unique(sub))

    def build(self) -> bytes:
        self.draw_cover()
        self.draw_materials_and_inventory()
        for i in range(len(self.tiles)):
            self.draw_chart_page(i)
        self.c.save()
        return self.buffer.getvalue()


def build_cross_stitch_pdf(
    result: GridPatternResult,
    *,
    title: str = "Cross Stitch Pattern",
    paper: Paper = "a4",
    style: PdfStyle = "tint",
) -> bytes:
    """Build the full pattern PDF and return its bytes."""
    return _Builder(result, title, paper, style).build()
