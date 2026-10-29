import numpy as np
import pytest

from app.services.palettes.loader import PaletteError, load_palette


def test_dmc_palette_loads_all_colors():
    palette = load_palette("dmc")
    assert len(palette) == 489
    assert palette.lab.shape == (489, 3)


@pytest.mark.parametrize(("name", "count"), [("dmc-diamond", 154), ("perler", 103)])
def test_other_palettes_load(name, count):
    assert len(load_palette(name)) == count


def test_codes_are_unique_and_rgb_valid():
    palette = load_palette("dmc")
    codes = [c.code for c in palette.colors]
    assert len(set(codes)) == len(codes)
    rgb = np.array([c.rgb for c in palette.colors])
    assert rgb.min() >= 0 and rgb.max() <= 255


def test_known_colors_present():
    codes = {c.code: c for c in load_palette("dmc").colors}
    assert codes["310"].name.lower().startswith("black")
    assert "Blanc" in codes and "B5200" in codes


def test_unknown_palette_raises():
    with pytest.raises(PaletteError):
        load_palette("not-a-brand")
