"""Pattern cleanup: remove tiny isolated color regions (single stitches, small islands).

Works on a grid of *local* color indices (0..m-1) plus the Lab value of each index, so the
replacement color for a speck is the visually closest color among its neighbours.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from app.services.imaging.color import ciede2000_matrix

# Cleanup strength -> smallest region (in stitches) that is kept. 0 turns cleanup off.
# Strength 1 removes lone stitches, 2 removes regions of up to 3 stitches, 3 up to 7.
MIN_REGION_AREA = {0: 0, 1: 2, 2: 4, 3: 8}

_FOUR_CONNECTED = ndimage.generate_binary_structure(2, 1)
_NEIGHBOUR_SHIFTS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def region_sizes(grid: np.ndarray) -> np.ndarray:
    """For every cell, the size of the 4-connected same-color region it belongs to."""
    sizes = np.zeros(grid.shape, dtype=np.int64)
    for color in np.unique(grid):
        labels, n = ndimage.label(grid == color, structure=_FOUR_CONNECTED)
        if n:
            counts = np.bincount(labels.ravel())
            mask = labels > 0
            sizes[mask] = counts[labels[mask]]
    return sizes


def count_small_regions(grid: np.ndarray, min_area: int) -> int:
    """Number of regions smaller than min_area (used to measure cleanup in tests/benchmarks)."""
    if min_area <= 1:
        return 0
    small = region_sizes(grid) < min_area
    count = 0
    for color in np.unique(grid):
        labels, n = ndimage.label((grid == color) & small, structure=_FOUR_CONNECTED)
        count += n
    return count


def clean_grid(
    grid: np.ndarray, lab: np.ndarray, min_area: int, max_iterations: int = 10
) -> np.ndarray:
    """Replace regions smaller than min_area by the closest-looking neighbouring color.

    Each pass moves every cell of a small region that touches a large region to the visually
    closest neighbouring color. Cells deeper inside a small region follow on the next pass, so even
    an island of several stitches dissolves from the outside in. Large regions are never changed.
    """
    if min_area <= 1:
        return grid.copy()
    grid = grid.copy()
    h, w = grid.shape
    distance = ciede2000_matrix(lab, lab)  # (m, m) perceptual distances between used colors

    for _ in range(max_iterations):
        small = region_sizes(grid) < min_area
        if not small.any():
            break

        best_cost = np.full(grid.shape, np.inf)
        best_color = grid.copy()
        padded_grid = np.pad(grid, 1, constant_values=-1)
        padded_small = np.pad(small, 1, constant_values=True)  # outside the image is not a donor
        for dy, dx in _NEIGHBOUR_SHIFTS:
            neighbour = padded_grid[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
            # A donor must be in a large region AND a different color. A same-color diagonal
            # neighbour is at distance 0 and would otherwise win without changing anything.
            donor_ok = ~padded_small[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w] & (neighbour != grid)
            cost = np.where(donor_ok, distance[grid, np.maximum(neighbour, 0)], np.inf)
            better = small & (cost < best_cost)
            best_cost = np.where(better, cost, best_cost)
            best_color = np.where(better, neighbour, best_color)

        changed = small & np.isfinite(best_cost)
        if not changed.any():
            break  # nothing to merge into (e.g. the whole image is one tiny region)
        grid = np.where(changed, best_color, grid)
    return grid
