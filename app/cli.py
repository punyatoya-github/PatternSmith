"""Command-line entry point: ``python -m app.cli photo.jpg --craft cross_stitch --level 3``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from app.schemas.settings import CraftSettings, CropBox
from app.services.crafts.cross_stitch import CrossStitchGenerator
from app.services.crafts.sizing import finished_size
from app.services.imaging.io import InvalidImageError, load_image
from app.services.palettes.loader import PaletteError


def _parse_crop(text: str) -> CropBox:
    try:
        left, top, right, bottom = (float(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(
            "crop must be 'left,top,right,bottom' as fractions"
        ) from None
    return CropBox(left=left, top=top, right=right, bottom=bottom)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="craft", description="Turn a photo into a craft pattern.")
    p.add_argument("image", type=Path, help="PNG, JPG or WebP file")
    p.add_argument("--craft", choices=["cross_stitch"], default="cross_stitch")
    p.add_argument("--level", type=int, choices=range(1, 6), help="complexity 1 (simple) to 5")
    p.add_argument("--width", type=int, help="pattern width in stitches (overrides --level)")
    p.add_argument("--colors", type=int, help="maximum number of colors (overrides --level)")
    p.add_argument("--fabric-count", type=int, choices=[11, 14, 16, 18], default=14)
    p.add_argument(
        "--cleanup", type=int, choices=range(4), help="cleanup strength 0 (off) to 3 (strongest)"
    )
    p.add_argument("--strands", type=int, default=2)
    p.add_argument("--crop", type=_parse_crop, help="left,top,right,bottom as fractions 0 to 1")
    p.add_argument("--out", type=Path, default=Path("pattern.png"), help="preview image path")
    p.add_argument("--json", type=Path, dest="json_out", help="also save the pattern as JSON")
    p.add_argument("--pdf", type=Path, help="also write a printable PDF (needs reportlab)")
    p.add_argument("--title", default="Cross Stitch Pattern", help="title used in the PDF")
    p.add_argument("--paper", choices=["a4", "letter"], default="a4")
    p.add_argument(
        "--pdf-style",
        choices=["tint", "mono"],
        default="tint",
        help="tint: symbols on a light color tint; mono: symbols on white (best for B&W printers)",
    )
    p.add_argument("--cell", type=int, default=12, help="preview cell size in pixels")
    p.add_argument("--no-symbols", action="store_true", help="omit symbols in the preview")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    overrides = {"fabric_count": args.fabric_count, "strands": args.strands, "crop": args.crop}
    if args.width is not None:
        overrides["width"] = args.width
    if args.colors is not None:
        overrides["colors"] = args.colors
    if args.cleanup is not None:
        overrides["cleanup"] = args.cleanup
    try:
        if args.level is not None:
            settings = CraftSettings.from_level(args.level, **overrides)
        else:
            settings = CraftSettings(**overrides)
        image = load_image(args.image)
        generator = CrossStitchGenerator()
        result = generator.generate(image, settings)
    except (ValidationError, InvalidImageError, PaletteError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    generator.render_preview(result, cell_px=args.cell, show_symbols=not args.no_symbols).save(
        args.out
    )
    if args.json_out:
        args.json_out.write_text(result.model_dump_json(), encoding="utf-8")

    if args.pdf:
        try:
            from app.services.pdf.cross_stitch_pdf import build_cross_stitch_pdf
        except ImportError:
            print("error: PDF export needs reportlab: pip install reportlab", file=sys.stderr)
            return 1
        args.pdf.write_bytes(
            build_cross_stitch_pdf(result, title=args.title, paper=args.paper, style=args.pdf_style)
        )
        print(f"PDF -> {args.pdf}")

    size = finished_size(result.width, result.height, settings.fabric_count)
    print(f"Pattern: {result.width} x {result.height} stitches, {len(result.palette)} colors")
    print(
        f"Finished size on {settings.fabric_count}-count: "
        f"{size.width_cm} x {size.height_cm} cm ({size.width_in} x {size.height_in} in)"
    )
    print(f"Generated in {result.timings_ms['total'] / 1000:.2f}s -> {args.out}")
    print(f"\n{'Sym':<4}{'DMC':<8}{'Stitches':>9}  Skeins  Name")
    for item in generator.build_inventory(result):
        print(f"{item.symbol:<4}{item.code:<8}{item.count:>9}  {item.skeins:>6}  {item.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
