"""One entry point for making a pattern, shared by the REST API and the Gradio UI.

Both front ends call these functions, so a future React front end only needs the API.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.schemas.pattern import GridPatternResult, InventoryItem
from app.schemas.settings import CraftSettings
from app.services.crafts.base import CraftGenerator
from app.services.crafts.cross_stitch import CrossStitchGenerator
from app.services.crafts.sizing import FinishedSize, finished_size


@dataclass(frozen=True)
class CraftInfo:
    id: str
    label: str
    generator: CraftGenerator


# Bead art (Week 6) and the embroidery template (Weeks 7 to 8) are registered here when they
# exist, and then show up in the API and in the UI dropdown automatically.
CRAFTS: dict[str, CraftInfo] = {
    "cross_stitch": CraftInfo("cross_stitch", "Cross stitch", CrossStitchGenerator()),
}


def available_crafts() -> list[tuple[str, str]]:
    """(label, id) pairs, in the shape Gradio dropdowns expect."""
    return [(info.label, info.id) for info in CRAFTS.values()]


def get_craft(craft_id: str) -> CraftInfo:
    try:
        return CRAFTS[craft_id]
    except KeyError:
        raise ValueError(f"unknown craft {craft_id!r}; available: {sorted(CRAFTS)}") from None


@dataclass(frozen=True)
class GenerationOutput:
    pattern: GridPatternResult
    inventory: list[InventoryItem]
    size: FinishedSize


def generate(image: np.ndarray, settings: CraftSettings) -> GenerationOutput:
    craft = get_craft(settings.craft)
    pattern = craft.generator.generate(image, settings)
    return GenerationOutput(
        pattern=pattern,
        inventory=craft.generator.build_inventory(pattern),
        size=finished_size(pattern.width, pattern.height, settings.fabric_count),
    )
