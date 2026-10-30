# Design decisions

Short records of choices that are easy to forget the reason for.

## The pattern is data, not an image
`GridPatternResult` holds a grid of palette indices plus a palette. Previews, counts, finished size,
PDFs and saved projects are all derived from it. This keeps one source of truth and makes later
features (chat editing, recoloring, exports) edits to data rather than to pixels.

## Lab color space and CIEDE2000
k-means and thread matching run in CIELAB, where distances roughly match how colors look. Thread
matching uses CIEDE2000, which handles hue and lightness better than Euclidean Lab distance.
It is only computed against small sets (cluster centers vs. 489 threads; image colors vs. at most 40
chosen threads), so cost stays low.

## scikit-image dependency
The original plan listed OpenCV, Pillow, NumPy and scikit-learn. scikit-image is added only for
`rgb2lab` and `deltaE_ciede2000`, because a tested reference implementation is safer than
hand-written color math. If install size matters later, these two functions can be replaced.

## Cluster unique colors, weighted by count
k-means runs on the distinct colors of the downsampled image with pixel counts as weights. It gives
the same result as clustering every pixel, is much faster on photos, and is cheap even for noise.

## Re-assign pixels to the chosen threads
After mapping cluster centers to threads (and merging duplicates), each distinct image color is
re-assigned to the nearest chosen thread. Without this step, pixels keep their original cluster
even when a neighbouring chosen thread is a closer match.

## Result color count can be lower than requested
The `colors` setting is a maximum. Clusters that map to the same DMC thread merge, and threads that
end up with no pixels are dropped.

## Symbols are letters, digits and a few punctuation marks
They render in any PDF or image font and avoid look-alikes (I/l/1, O/0). At least 58 are defined for
a 40-color maximum. Vector shapes can be added later if legibility on paper demands it.

## No accounts in Phase 1
Matches the roadmap. Projects will be stored against an anonymous session token (Week 9), with
project file download and upload as a backup.

## Palette data and licensing
Palettes are copied unmodified from craft-color-codes (CC BY 4.0, Perler values MIT) with
attribution in `data/palettes/ATTRIBUTION.md`. The data is marked `cross-checked` for DMC and
`community` for Perler upstream, so Perler colors should be shown as approximate.

## Skein estimate is a heuristic
One full stitch = two front diagonals plus about two stitch lengths of travel on the back, times a
1.5 waste factor, for six-strand, 8 m skeins. It is labelled approximate and should be calibrated
against a published calculator before launch.

## Cleanup works per cell, from the outside in
Cleanup finds 4-connected same-color regions. Every cell in a region below the size threshold moves
to the visually closest (CIEDE2000) *different* color among its eight neighbours that belongs to a
large region; cells deeper inside a small island follow on the next pass. It is fully vectorised
with NumPy shifts, so it costs roughly 3 to 190 ms. Lesson learned: same-color neighbours must be
excluded as donors, otherwise a lone stitch touching a big region of its own color diagonally
"merges" into itself and never changes (regression test in `tests/test_cleanup.py`).

## Cleanup strength follows the complexity level
Simpler patterns clean harder (levels 1 and 2: remove regions up to 7 stitches; level 3 and 4: up
to 3; level 5: lone stitches only), because one stray stitch matters more on a small chart.

## PDF design
- Chart pages hold a multiple of 10 columns and rows, so page edges fall on bold lines.
- Two styles: `tint` (symbol on a 62% tint of the thread color) and `mono` (symbol on white). The
  tint is always light, so the black symbol stays readable even on dark threads.
- Small patterns that fit on one page get larger cells (up to 16 pt).
- No row/column overlap between pages; absolute row and column numbers, "continues right/down"
  page pointers and a minimap navigate instead. Revisit if testers get lost.
- Only ASCII text is drawn with built-in fonts, which avoids missing-glyph boxes.

