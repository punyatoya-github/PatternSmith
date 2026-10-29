"""Load thread and bead palettes from data/palettes and precompute their Lab values."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache

import numpy as np

from app.core import config
from app.services.imaging.color import rgb_to_lab

# Public palette name -> file in data/palettes
PALETTE_FILES = {
    "dmc": "dmc-floss.json",
    "dmc-diamond": "dmc-diamond.json",
    "perler": "perler-midi.json",
}


class PaletteError(ValueError):
    pass


@dataclass(frozen=True)
class PaletteColor:
    code: str
    name: str
    hex: str
    rgb: tuple[int, int, int]


@dataclass(frozen=True, eq=False)
class Palette:
    name: str
    brand: str
    colors: tuple[PaletteColor, ...]
    lab: np.ndarray  # shape (n, 3), CIELAB

    def __len__(self) -> int:
        return len(self.colors)


def _parse_color(raw: dict, palette: str) -> PaletteColor:
    try:
        rgb = tuple(int(v) for v in raw["rgb"])
        code, name, hex_ = str(raw["code"]), str(raw["name"]), str(raw["hex"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PaletteError(f"{palette}: malformed color entry {raw!r}") from exc
    if len(rgb) != 3 or any(not 0 <= v <= 255 for v in rgb):
        raise PaletteError(f"{palette}: invalid rgb for code {code}: {rgb}")
    return PaletteColor(code=code, name=name, hex=hex_, rgb=rgb)  # type: ignore[arg-type]


@cache
def load_palette(name: str) -> Palette:
    if name not in PALETTE_FILES:
        raise PaletteError(f"unknown palette {name!r}; available: {sorted(PALETTE_FILES)}")
    path = config.PALETTE_DIR / PALETTE_FILES[name]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PaletteError(f"cannot read palette file {path}") from exc

    colors = tuple(_parse_color(raw, name) for raw in data["colors"])
    codes = [c.code for c in colors]
    if len(set(codes)) != len(codes):
        raise PaletteError(f"{name}: duplicate color codes")
    lab = rgb_to_lab(np.array([c.rgb for c in colors], dtype=np.uint8))
    return Palette(name=name, brand=str(data.get("brand", name)), colors=colors, lab=lab)
