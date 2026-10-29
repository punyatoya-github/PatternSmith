# Product brief: AI Craft Pattern Generator, Phase 1

**Problem.** Crafters who want a custom pattern from their own photo must either pay for
a pattern service or wrestle with desktop software. Free converters often produce noisy,
unstitchable results with no usable thread list.

**Users (Phase 1).** Hobbyist cross stitchers, bead-art makers (Perler, fuse, diamond art) and
embroiderers who have a photo and want a pattern they can print and start today.

**Goal.** Validate that people find value in turning an image into a craft pattern.

**Core journey.** Upload, crop, choose craft, set complexity, generate, preview, download PDF.

**Hypotheses to test**
1. People complete the flow and download the PDF.
2. Patterns are good enough that a real crafter would use one.
3. We learn which craft gets used most.
4. We learn which Phase 2 feature people ask for first.

**Success criteria**
- Photo to downloadable PDF in under 30 seconds (typical case under 15).
- 7 of 10 test crafters rate their own-photo pattern 4/5 or better for "would use".
- 50 patterns generated and 20 PDFs downloaded by outside users within 3 weeks of launch.
- Under 2% of generations end in an error.

**In scope.** Cross stitch, bead art, embroidery template (lite); K-means color reduction to real
DMC / Perler palettes; basic cleanup; zoomable preview; PDF with material list, thread inventory
and size; anonymous session projects; feedback form.

**Out of scope.** Accounts, other crafts, AI generation, reverse recognition, marketplace,
payments, community, agents, bulk jobs, React front end, mobile app.

**Go / no-go for Phase 2.** Go if usage and quality criteria are met and one craft clearly leads.
Adjust (improve the engine) if quality is the main complaint. Pivot if people generate but never
download.
