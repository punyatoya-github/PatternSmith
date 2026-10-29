"""Performance benchmark. Exits non-zero if the engine exceeds its budget (used in CI).

Budgets follow the Phase 1 plan: Week 2 exit criterion is a pattern in under 5 seconds, and the
typical 100 x 100 case should leave most of the 15 second end-to-end budget for the PDF step.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from app.schemas.settings import CraftSettings  # noqa: E402
from app.services.crafts.cross_stitch import CrossStitchGenerator  # noqa: E402
from app.services.imaging.io import load_image  # noqa: E402

IMAGES = REPO / "data" / "test_images" / "synthetic"

# (label, image file, level, budget in seconds for generate + preview)
CASES = [
    ("typical: sunflower, level 3 (100x100, 20 colors)", "sunflower.png", 3, 2.0),
    ("detailed: sunflower, level 5 (200x200, 40 colors)", "sunflower.png", 5, 4.0),
    ("worst case: random noise, level 5", "noisy_texture.png", 5, 5.0),
    ("logo, level 2", "logo_shapes.png", 2, 1.0),
]


def main() -> int:
    if not IMAGES.exists():
        print("synthetic images missing; run: python scripts/make_test_images.py", file=sys.stderr)
        return 2
    gen = CrossStitchGenerator()
    failed = False
    print(f"{'case':<52}{'load':>7}{'generate':>10}{'preview':>9}{'total':>8}  budget")
    for label, filename, level, budget in CASES:
        t0 = time.perf_counter()
        image = load_image(IMAGES / filename)
        t_load = time.perf_counter() - t0

        result = gen.generate(image, CraftSettings.from_level(level))
        t_gen = result.timings_ms["total"] / 1000

        t1 = time.perf_counter()
        gen.render_preview(result, cell_px=8, show_symbols=True)
        t_prev = time.perf_counter() - t1

        total = t_load + t_gen + t_prev
        ok = total <= budget
        failed |= not ok
        print(
            f"{label:<52}{t_load:>6.2f}s{t_gen:>9.2f}s{t_prev:>8.2f}s{total:>7.2f}s"
            f"  {budget:.1f}s {'ok' if ok else 'OVER BUDGET'}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
