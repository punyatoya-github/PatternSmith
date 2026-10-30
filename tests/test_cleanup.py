import numpy as np

from app.schemas.settings import CraftSettings
from app.services.crafts.cross_stitch import CrossStitchGenerator
from app.services.imaging.cleanup import (
    MIN_REGION_AREA,
    clean_grid,
    count_small_regions,
    region_sizes,
)

LAB = np.array([[20.0, 0, 0], [50.0, 0, 0], [80.0, 0, 0]])  # three greys: dark, mid, light


def test_region_sizes():
    grid = np.array([[0, 0, 1], [0, 1, 1], [2, 2, 2]])
    sizes = region_sizes(grid)
    assert sizes[0, 0] == 3 and sizes[0, 2] == 3 and sizes[2, 0] == 3


def test_lone_stitch_is_absorbed():
    grid = np.zeros((8, 8), dtype=int)
    grid[4, 4] = 1
    out = clean_grid(grid, LAB, min_area=2)
    assert (out == 0).all()


def test_diagonal_touch_of_same_color_still_counts_as_isolated():
    """Regression: a lone stitch touching a big same-colored region only diagonally must be
    removed. It used to pick that region as its own 'donor' (distance 0) and never change."""
    grid = np.zeros((10, 10), dtype=int)
    grid[0:3, 0:3] = 1  # big region of color 1
    grid[3, 3] = 1  # lone stitch, diagonal neighbour of the big region
    out = clean_grid(grid, LAB, min_area=4)
    assert out[3, 3] == 0
    assert (out[0:3, 0:3] == 1).all()


def test_large_regions_are_never_changed():
    grid = np.zeros((10, 10), dtype=int)
    grid[:, 5:] = 2
    grid[2, 2] = 1
    out = clean_grid(grid, LAB, min_area=3)
    assert (out[:, 5:] == 2).all()
    assert out[2, 2] == 0


def test_speck_takes_the_visually_closest_neighbouring_color():
    grid = np.zeros((6, 6), dtype=int)
    grid[:, 3:] = 2  # dark left (0), light right (2)
    grid[2, 2] = 1  # speck on the boundary between the dark and light regions
    lab = np.array([[20.0, 0, 0], [70.0, 0, 0], [85.0, 0, 0]])  # speck is lighter, so closer to 2
    out = clean_grid(grid, lab, min_area=2)
    assert out[2, 2] == 2


def test_disabled_and_uniform_inputs():
    grid = np.array([[0, 1], [1, 0]])
    assert np.array_equal(clean_grid(grid, LAB, min_area=0), grid)
    assert np.array_equal(clean_grid(grid, LAB, min_area=1), grid)
    uniform = np.zeros((5, 5), dtype=int)
    assert np.array_equal(clean_grid(uniform, LAB, min_area=8), uniform)  # one region, no donor


def test_input_is_not_modified_and_indices_stay_valid():
    rng = np.random.default_rng(0)
    grid = rng.integers(0, 3, (20, 20))
    before = grid.copy()
    out = clean_grid(grid, LAB, min_area=4)
    assert np.array_equal(grid, before)
    assert set(np.unique(out)) <= {0, 1, 2}


def test_cleanup_leaves_no_small_regions_on_noise():
    rng = np.random.default_rng(1)
    grid = rng.integers(0, 3, (40, 40))
    assert count_small_regions(grid, 4) > 50
    assert count_small_regions(clean_grid(grid, LAB, min_area=4), 4) == 0


def test_generator_cleanup_reduces_isolated_stitches(noise):
    gen = CrossStitchGenerator()
    off = gen.generate(noise, CraftSettings(width=60, colors=12, cleanup=0))
    on = gen.generate(noise, CraftSettings(width=60, colors=12, cleanup=2))
    min_area = MIN_REGION_AREA[2]
    assert count_small_regions(on.grid_array(), min_area) == 0
    assert count_small_regions(off.grid_array(), min_area) > 0
    assert len(on.palette) <= len(off.palette)  # cleanup can only drop colors, never add
    assert sum(e.count for e in on.palette) == on.total_stitches


def test_cleanup_keeps_clean_images_intact(bands):
    gen = CrossStitchGenerator()
    a = gen.generate(bands, CraftSettings(width=30, colors=3, cleanup=0))
    b = gen.generate(bands, CraftSettings(width=30, colors=3, cleanup=3))
    assert a.grid == b.grid
