import io

import pytest
from pypdf import PdfReader

from app.schemas.settings import CraftSettings
from app.services.crafts.cross_stitch import CrossStitchGenerator
from app.services.pdf.cross_stitch_pdf import (
    _Builder,
    build_cross_stitch_pdf,
    chart_layout,
    plan_chart_pages,
)

gen = CrossStitchGenerator()


def _read(pdf: bytes) -> PdfReader:
    return PdfReader(io.BytesIO(pdf))


def _text(reader: PdfReader) -> str:
    return "\n".join(page.extract_text() for page in reader.pages)


@pytest.mark.parametrize(
    ("width", "height", "cols", "rows"),
    [(100, 100, 50, 60), (20, 20, 50, 60), (50, 60, 50, 60), (51, 61, 50, 60), (250, 400, 50, 60)],
)
def test_page_tiles_cover_every_cell_exactly_once(width, height, cols, rows):
    covered = set()
    for c0, c1, r0, r1 in plan_chart_pages(width, height, cols, rows):
        assert 0 <= c0 < c1 <= width and 0 <= r0 < r1 <= height
        for r in range(r0, r1):
            for c in range(c0, c1):
                assert (r, c) not in covered
                covered.add((r, c))
    assert len(covered) == width * height


def test_chart_pages_align_with_bold_lines():
    layout = chart_layout(595, 842, 200, 200)
    assert layout.cols % 10 == 0 and layout.rows % 10 == 0


def test_small_pattern_gets_bigger_cells_on_one_page():
    layout = chart_layout(595, 842, 40, 40)
    assert (layout.cols, layout.rows) == (40, 40) and layout.cell > 10


def test_pdf_is_valid_and_has_expected_page_count(noise):
    result = gen.generate(noise, CraftSettings(width=130, colors=10))
    builder = _Builder(result, "Test", "a4", "tint")
    pdf = build_cross_stitch_pdf(result, title="Test")
    reader = _read(pdf)
    assert pdf.startswith(b"%PDF")
    assert len(reader.pages) == builder.total_pages
    assert len(builder.tiles) > 1  # this size must span several chart pages


def test_pdf_contains_title_legend_codes_and_counts(noise):
    result = gen.generate(noise, CraftSettings(width=60, colors=12))
    reader = _read(build_cross_stitch_pdf(result, title="Garden Gate"))
    text = _text(reader)
    assert "Garden Gate" in text
    for entry in result.palette:
        assert entry.code in text
    assert f"{result.width} x {result.height} stitches" in text
    assert f"Page 1 of {len(reader.pages)}" in text
    assert reader.metadata.title == "Garden Gate"


def test_multi_page_chart_has_navigation_hints(noise):
    result = gen.generate(noise, CraftSettings(width=130, colors=8))
    text = _text(_read(build_cross_stitch_pdf(result)))
    assert "continues right" in text and "continues down" in text
    assert "Columns 1-50" in text


def test_single_page_chart_has_no_navigation_hints(bands):
    result = gen.generate(bands, CraftSettings(width=30, colors=3))
    reader = _read(build_cross_stitch_pdf(result))
    assert len(reader.pages) == 3  # cover, materials, one chart page
    assert "continues" not in _text(reader)


def test_paper_sizes(bands):
    result = gen.generate(bands, CraftSettings(width=30, colors=3))
    a4 = _read(build_cross_stitch_pdf(result, paper="a4")).pages[0].mediabox
    us = _read(build_cross_stitch_pdf(result, paper="letter")).pages[0].mediabox
    assert round(float(a4.width)) == 595 and round(float(us.width)) == 612


def test_mono_style_builds(noise):
    result = gen.generate(noise, CraftSettings(width=40, colors=8))
    assert build_cross_stitch_pdf(result, style="mono").startswith(b"%PDF")


def test_invalid_options_rejected(bands):
    result = gen.generate(bands, CraftSettings(width=30, colors=3))
    with pytest.raises(ValueError):
        build_cross_stitch_pdf(result, paper="a3")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        build_cross_stitch_pdf(result, style="neon")  # type: ignore[arg-type]


def test_many_colors_paginate_the_thread_list(noise):
    result = gen.generate(noise, CraftSettings(width=80, colors=40, cleanup=0))
    builder = _Builder(result, "T", "a4", "tint")
    reader = _read(builder.build())
    assert len(reader.pages) == builder.total_pages
    text = _text(reader)
    assert all(e.code in text for e in result.palette)
