"""Result-side schemas. The pattern is stored as a grid of palette indices, not as an image:
previews, PDFs, counts and saved projects are all derived from it (Part 1, Section 3)."""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field, model_validator

from app.core import config
from app.schemas.settings import CraftSettings


class PaletteEntry(BaseModel):
    code: str
    name: str
    hex: str
    rgb: tuple[int, int, int]
    symbol: str
    count: int = Field(ge=0)


class InventoryItem(BaseModel):
    code: str
    name: str
    hex: str
    symbol: str
    count: int
    skeins: int = Field(ge=1)


class GridPatternResult(BaseModel):
    schema_version: int = 1
    craft_id: str = "cross_stitch"
    width: int = Field(ge=1, le=config.MAX_STITCH_WIDTH)
    height: int = Field(ge=1, le=config.MAX_STITCH_HEIGHT)
    grid: list[list[int]]
    palette: list[PaletteEntry] = Field(min_length=1, max_length=config.MAX_COLORS)
    settings: CraftSettings
    timings_ms: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_grid(self) -> GridPatternResult:
        if len(self.grid) != self.height or any(len(row) != self.width for row in self.grid):
            raise ValueError("grid dimensions do not match width and height")
        arr = np.asarray(self.grid)
        if arr.min() < 0 or arr.max() >= len(self.palette):
            raise ValueError("grid contains an index outside the palette")
        return self

    @property
    def total_stitches(self) -> int:
        return self.width * self.height

    def grid_array(self) -> np.ndarray:
        return np.asarray(self.grid, dtype=np.int32)
