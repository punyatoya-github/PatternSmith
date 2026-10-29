"""Chart symbols. Letters and digits only, so they render in any PDF or image font.

Look-alikes (I, l, 1, O, 0, o, and lower-case twins of capitals such as c/C and s/S) are left out
so neighbouring symbols stay easy to tell apart on a printed chart.
"""

from __future__ import annotations

SYMBOLS = "ABCDEFGHJKLMNPQRSTUVWXYZ" + "abdefghmnqrty" + "23456789" + "#@%&*+=?!$~^<>/"


def symbol_for(index: int) -> str:
    if not 0 <= index < len(SYMBOLS):
        raise IndexError(f"no symbol for index {index}; only {len(SYMBOLS)} are defined")
    return SYMBOLS[index]
