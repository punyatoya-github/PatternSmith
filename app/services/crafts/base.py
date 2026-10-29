"""Shared interface for every craft module (Phase 1 plan, Section 6.1)."""

from __future__ import annotations

from typing import Protocol

import numpy as np
from PIL import Image

from app.schemas.pattern import GridPatternResult, InventoryItem
from app.schemas.settings import CraftSettings


class CraftGenerator(Protocol):
    craft_id: str

    def generate(self, image: np.ndarray, settings: CraftSettings) -> GridPatternResult: ...

    def render_preview(self, result: GridPatternResult) -> Image.Image: ...

    def build_inventory(self, result: GridPatternResult) -> list[InventoryItem]: ...
