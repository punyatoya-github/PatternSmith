"""Central limits and paths. Values come from the Phase 1 plan (Sections 3, 5 and 10)."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("CRAFT_DATA_DIR", REPO_ROOT / "data"))
PALETTE_DIR = DATA_DIR / "palettes"

# Upload limits
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 50_000_000  # reject before decoding: decompression-bomb guard
MAX_SIDE = 4000  # larger images are downscaled after decoding
ALLOWED_FORMATS = frozenset({"PNG", "JPEG", "WEBP"})

# Pattern limits
MIN_STITCH_WIDTH = 20
MAX_STITCH_WIDTH = 250
MAX_STITCH_HEIGHT = 400
MIN_COLORS = 2
MAX_COLORS = 40
