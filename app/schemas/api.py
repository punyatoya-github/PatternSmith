"""Request and response bodies for the REST API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.pattern import GridPatternResult, InventoryItem

MAX_PREVIEW_SIDE_PX = 3000  # keeps memory use bounded for API callers


class FinishedSizeOut(BaseModel):
    width_cm: float
    height_cm: float
    width_in: float
    height_in: float


class GenerateResponse(BaseModel):
    pattern: GridPatternResult
    inventory: list[InventoryItem]
    finished_size: FinishedSizeOut


class CraftOut(BaseModel):
    id: str
    label: str


class PreviewRequest(BaseModel):
    pattern: GridPatternResult
    cell_px: int = Field(12, ge=2, le=40)
    show_symbols: bool = True
    show_grid: bool = True

    @model_validator(mode="after")
    def _limit_output_size(self) -> PreviewRequest:
        if max(self.pattern.width, self.pattern.height) * self.cell_px > MAX_PREVIEW_SIDE_PX:
            raise ValueError(
                f"preview would be larger than {MAX_PREVIEW_SIDE_PX} px on a side; "
                "use a smaller cell_px"
            )
        return self


class PdfRequest(BaseModel):
    pattern: GridPatternResult
    title: str = Field("Cross Stitch Pattern", min_length=1, max_length=80)
    paper: Literal["a4", "letter"] = "a4"
    style: Literal["tint", "mono"] = "tint"
