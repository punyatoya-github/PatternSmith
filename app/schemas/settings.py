"""Request-side schemas: what the user asks the generator to do."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core import config

FabricCount = Literal[11, 14, 16, 18]

# Complexity slider presets (Phase 1 plan, Section 6.2):
# level -> (stitch width, colors, cleanup strength). Simpler patterns clean up harder, because a
# lone stitch matters more on a small chart; detailed patterns keep more fine detail.
CROSS_STITCH_LEVELS: dict[int, tuple[int, int, int]] = {
    1: (40, 8, 3),
    2: (60, 12, 3),
    3: (100, 20, 2),
    4: (150, 30, 2),
    5: (200, 40, 1),
}


class CropBox(BaseModel):
    """Crop rectangle as fractions of the image (0 to 1), so it is resolution independent."""

    left: float = Field(0.0, ge=0, le=1)
    top: float = Field(0.0, ge=0, le=1)
    right: float = Field(1.0, ge=0, le=1)
    bottom: float = Field(1.0, ge=0, le=1)

    @model_validator(mode="after")
    def _check_order(self) -> CropBox:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("crop box must have right > left and bottom > top")
        return self


class CraftSettings(BaseModel):
    """Settings for a cross-stitch pattern. Bead and embroidery settings arrive in Weeks 6 to 8."""

    craft: Literal["cross_stitch"] = "cross_stitch"
    width: int = Field(100, ge=config.MIN_STITCH_WIDTH, le=config.MAX_STITCH_WIDTH)
    colors: int = Field(20, ge=config.MIN_COLORS, le=config.MAX_COLORS)
    fabric_count: FabricCount = 14
    strands: int = Field(2, ge=1, le=6)
    palette: Literal["dmc"] = "dmc"
    cleanup: int = Field(2, ge=0, le=3)  # 0 off, 1 lone stitches, 2 up to 3, 3 up to 7 stitches
    crop: CropBox | None = None
    seed: int = 42

    @classmethod
    def from_level(cls, level: int, **overrides) -> CraftSettings:
        """Build settings from the 1 to 5 complexity slider; any field can be overridden."""
        if level not in CROSS_STITCH_LEVELS:
            raise ValueError(f"level must be one of {sorted(CROSS_STITCH_LEVELS)}")
        width, colors, cleanup = CROSS_STITCH_LEVELS[level]
        values = {"width": width, "colors": colors, "cleanup": cleanup, **overrides}
        return cls(**values)
