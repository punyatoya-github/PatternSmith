"""Cross-stitch generator: photo -> grid of DMC thread indices."""

from __future__ import annotations

import time

import numpy as np
from PIL import Image

from app.schemas.pattern import GridPatternResult, InventoryItem, PaletteEntry
from app.schemas.settings import CraftSettings
from app.services.crafts.render import render_grid_preview
from app.services.crafts.sizing import estimate_skeins
from app.services.crafts.symbols import symbol_for
from app.services.imaging.cleanup import MIN_REGION_AREA, clean_grid
from app.services.imaging.color import ciede2000_matrix, rgb_to_lab
from app.services.imaging.io import crop_image, downsample_to_width
from app.services.imaging.quantize import kmeans_centers
from app.services.palettes.loader import load_palette


class CrossStitchGenerator:
    craft_id = "cross_stitch"

    def generate(self, image: np.ndarray, settings: CraftSettings) -> GridPatternResult:
        timings: dict[str, float] = {}
        t_start = t = time.perf_counter()

        def lap(name: str) -> None:
            nonlocal t
            now = time.perf_counter()
            timings[name] = round((now - t) * 1000, 1)
            t = now

        palette = load_palette(settings.palette)

        # 1. One pixel per stitch
        small = downsample_to_width(crop_image(image, settings.crop), settings.width)
        h, w = small.shape[:2]
        lap("prepare")

        # 2. Cluster the distinct colors in Lab space
        unique_rgb, inverse, counts = np.unique(
            small.reshape(-1, 3), axis=0, return_inverse=True, return_counts=True
        )
        inverse = inverse.reshape(-1)  # NumPy 2.x may return the inverse reshaped
        unique_lab = rgb_to_lab(unique_rgb)
        centers = kmeans_centers(unique_lab, counts, settings.colors, settings.seed)
        lap("quantize")

        # 3. Pick the nearest real thread for each cluster center (perceptual distance).
        #    Centers that land on the same thread merge, so the color count can only shrink.
        center_to_thread = ciede2000_matrix(centers, palette.lab).argmin(axis=1)
        chosen = np.unique(center_to_thread)

        # 4. Re-assign every distinct image color to the nearest *chosen* thread
        nearest = chosen[ciede2000_matrix(unique_lab, palette.lab[chosen]).argmin(axis=1)]
        pixel_thread = nearest[inverse].reshape(h, w)
        lap("map_threads")

        # 5. Basic cleanup on a compact local grid (indices 0..m-1), then re-compact because
        #    cleanup can remove a color entirely
        local_threads, local_grid = np.unique(pixel_thread, return_inverse=True)
        local_grid = local_grid.reshape(h, w)
        local_grid = clean_grid(
            local_grid, palette.lab[local_threads], MIN_REGION_AREA[settings.cleanup]
        )
        pixel_thread = local_threads[local_grid]
        lap("cleanup")

        # 6. Compact to the threads actually used, most-used first (stable, so deterministic)
        used, used_counts = np.unique(pixel_thread, return_counts=True)
        order = np.argsort(-used_counts, kind="stable")
        used, used_counts = used[order], used_counts[order]
        lookup = np.full(len(palette), -1, dtype=np.int32)
        lookup[used] = np.arange(len(used), dtype=np.int32)
        grid = lookup[pixel_thread]

        entries = []
        for rank, (thread_idx, count) in enumerate(zip(used, used_counts, strict=True)):
            color = palette.colors[int(thread_idx)]
            entries.append(
                PaletteEntry(
                    code=color.code,
                    name=color.name,
                    hex=color.hex,
                    rgb=color.rgb,
                    symbol=symbol_for(rank),
                    count=int(count),
                )
            )
        lap("assemble")
        timings["total"] = round((time.perf_counter() - t_start) * 1000, 1)

        return GridPatternResult(
            craft_id=self.craft_id,
            width=w,
            height=h,
            grid=grid.tolist(),
            palette=entries,
            settings=settings,
            timings_ms=timings,
        )

    def render_preview(
        self,
        result: GridPatternResult,
        cell_px: int = 12,
        show_symbols: bool = True,
        show_grid: bool = True,
    ) -> Image.Image:
        return render_grid_preview(result, cell_px, show_symbols, show_grid)

    def build_inventory(self, result: GridPatternResult) -> list[InventoryItem]:
        return [
            InventoryItem(
                code=e.code,
                name=e.name,
                hex=e.hex,
                symbol=e.symbol,
                count=e.count,
                skeins=estimate_skeins(
                    e.count, result.settings.fabric_count, result.settings.strands
                ),
            )
            for e in result.palette
        ]
