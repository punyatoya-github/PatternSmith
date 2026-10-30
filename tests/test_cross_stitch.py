import numpy as np
import pytest
from pydantic import ValidationError

from app.schemas.pattern import GridPatternResult
from app.schemas.settings import CraftSettings, CropBox
from app.services.crafts.cross_stitch import CrossStitchGenerator
from app.services.crafts.sizing import estimate_skeins, finished_size
from app.services.crafts.symbols import SYMBOLS, symbol_for

gen = CrossStitchGenerator()


def test_grid_shape_and_color_limit(noise):
    result = gen.generate(noise, CraftSettings(width=50, colors=8))
    assert (result.width, result.height) == (50, 38)  # 160x120 image -> 50 x round(37.5)
    assert len(result.palette) <= 8
    assert result.grid_array().shape == (result.height, result.width)


def test_every_cell_points_to_a_palette_entry(noise):
    result = gen.generate(noise, CraftSettings(width=40, colors=12))
    grid = result.grid_array()
    assert grid.min() >= 0 and grid.max() < len(result.palette)


def test_counts_add_up_and_match_grid(noise):
    result = gen.generate(noise, CraftSettings(width=40, colors=12))
    assert sum(e.count for e in result.palette) == result.total_stitches
    for idx, entry in enumerate(result.palette):
        assert entry.count == int((result.grid_array() == idx).sum())
    counts = [e.count for e in result.palette]
    assert counts == sorted(counts, reverse=True)  # most-used thread first


def test_symbols_and_codes_unique(noise):
    result = gen.generate(noise, CraftSettings(width=60, colors=40))
    symbols = [e.symbol for e in result.palette]
    codes = [e.code for e in result.palette]
    assert len(set(symbols)) == len(symbols)
    assert len(set(codes)) == len(codes)


def test_three_color_image_gives_three_regions(bands):
    result = gen.generate(bands, CraftSettings(width=30, colors=3))
    grid = result.grid_array()
    assert len(result.palette) == 3
    # each band maps to exactly one thread, and the three threads differ
    band_ids = [np.unique(grid[:, i * 10 : (i + 1) * 10]) for i in range(3)]
    assert all(len(ids) == 1 for ids in band_ids)
    assert len({int(ids[0]) for ids in band_ids}) == 3


def test_threads_are_perceptually_close_to_source(bands):
    result = gen.generate(bands, CraftSettings(width=30, colors=3))
    rgb = {e.rgb for e in result.palette}
    # white band should land on a near-white thread
    assert any(min(c) > 240 for c in rgb)


def test_deterministic(noise):
    s = CraftSettings(width=40, colors=10, seed=3)
    assert gen.generate(noise, s).grid == gen.generate(noise, s).grid


def test_crop_changes_the_pattern(bands):
    full = gen.generate(bands, CraftSettings(width=30, colors=3))
    cropped = gen.generate(
        bands, CraftSettings(width=30, colors=3, crop=CropBox(left=0, right=1 / 3))
    )
    assert len(full.palette) == 3 and len(cropped.palette) == 1


def test_json_roundtrip(noise):
    result = gen.generate(noise, CraftSettings(width=30, colors=6))
    again = GridPatternResult.model_validate_json(result.model_dump_json())
    assert again.grid == result.grid and again.palette == result.palette


def test_result_validation_catches_bad_index(noise):
    result = gen.generate(noise, CraftSettings(width=20, colors=4))
    data = result.model_dump()
    data["grid"][0][0] = 99
    with pytest.raises(ValidationError):
        GridPatternResult.model_validate(data)


def test_timings_recorded(noise):
    result = gen.generate(noise, CraftSettings(width=30, colors=6))
    assert {"prepare", "quantize", "map_threads", "cleanup", "total"} <= set(result.timings_ms)


def test_preview_dimensions_and_symbols(noise):
    result = gen.generate(noise, CraftSettings(width=30, colors=6))
    img = gen.render_preview(result, cell_px=10)
    assert img.size == (result.width * 10, result.height * 10)
    plain = gen.render_preview(result, cell_px=10, show_symbols=False, show_grid=False)
    assert np.asarray(img).tolist() != np.asarray(plain).tolist()


def test_inventory_matches_palette(noise):
    result = gen.generate(noise, CraftSettings(width=30, colors=6))
    inventory = gen.build_inventory(result)
    assert [i.code for i in inventory] == [e.code for e in result.palette]
    assert all(i.skeins >= 1 for i in inventory)


def test_settings_levels():
    assert (CraftSettings.from_level(1).width, CraftSettings.from_level(1).colors) == (40, 8)
    assert (
        CraftSettings.from_level(1).cleanup > CraftSettings.from_level(5).cleanup
    )  # simpler = stronger
    assert CraftSettings.from_level(3, cleanup=0).cleanup == 0
    assert CraftSettings.from_level(5, fabric_count=18).fabric_count == 18
    with pytest.raises(ValueError):
        CraftSettings.from_level(9)


def test_settings_bounds():
    for bad in (
        {"width": 5},
        {"width": 999},
        {"colors": 1},
        {"colors": 41},
        {"fabric_count": 13},
        {"cleanup": 4},
    ):
        with pytest.raises(ValidationError):
            CraftSettings(**bad)


def test_finished_size_math():
    size = finished_size(140, 70, 14)
    assert (size.width_in, size.height_in) == (10.0, 5.0)
    assert size.width_cm == 25.4


def test_skeins_scale_with_stitches_and_strands():
    assert estimate_skeins(0, 14, 2) == 1
    assert estimate_skeins(100, 14, 2) == 1
    assert estimate_skeins(20_000, 14, 2) > estimate_skeins(2_000, 14, 2)
    assert estimate_skeins(5_000, 14, 3) >= estimate_skeins(5_000, 14, 2)
    # coarser fabric means bigger stitches, so more thread for the same stitch count
    assert estimate_skeins(50_000, 11, 2) > estimate_skeins(50_000, 18, 2)


def test_enough_symbols_for_max_colors():
    assert len(SYMBOLS) >= 40 and len(set(SYMBOLS)) == len(SYMBOLS)
    with pytest.raises(IndexError):
        symbol_for(len(SYMBOLS))
