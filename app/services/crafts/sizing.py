"""Finished-size and thread estimates."""

from __future__ import annotations

import math
from dataclasses import dataclass

MM_PER_INCH = 25.4
SKEIN_LENGTH_MM = 8_000  # a DMC skein is about 8 m
SKEIN_STRANDS = 6  # ... of six-strand floss
# Extra thread for the back of the work, thread tails and parking between colors.
DEFAULT_WASTE_FACTOR = 1.5


@dataclass(frozen=True)
class FinishedSize:
    width_cm: float
    height_cm: float
    width_in: float
    height_in: float


def finished_size(width: int, height: int, fabric_count: int) -> FinishedSize:
    """Fabric count is stitches per inch, so size is simply stitches divided by count."""
    width_in = width / fabric_count
    height_in = height / fabric_count
    return FinishedSize(
        width_cm=round(width_in * 2.54, 1),
        height_cm=round(height_in * 2.54, 1),
        width_in=round(width_in, 1),
        height_in=round(height_in, 1),
    )


def estimate_skeins(
    stitches: int,
    fabric_count: int,
    strands: int,
    waste_factor: float = DEFAULT_WASTE_FACTOR,
) -> int:
    """Approximate whole skeins needed for one color of full cross stitches.

    Heuristic: one full stitch uses two diagonals on the front (2 * sqrt(2) * s) plus roughly two
    stitch-lengths of travel on the back, where s is the stitch size. This is an estimate to
    calibrate against a published thread calculator before relying on it; the PDF labels it
    "approximate".
    """
    if stitches <= 0:
        return 1
    stitch_mm = MM_PER_INCH / fabric_count
    strand_mm_per_stitch = stitch_mm * (2 * math.sqrt(2) + 2) * waste_factor
    total_strand_mm = stitches * strands * strand_mm_per_stitch
    return max(1, math.ceil(total_strand_mm / (SKEIN_LENGTH_MM * SKEIN_STRANDS)))
