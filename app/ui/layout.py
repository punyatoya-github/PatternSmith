"""The Gradio interface: left column sets things up, right column shows the result."""

from __future__ import annotations

import gradio as gr

from app.services.generation import available_crafts
from app.services.imaging.framing import ASPECT_PRESETS
from app.ui import handlers

# Graph-paper ink: a deep blue ramp, chosen to look like the lines on cross-stitch chart paper.
INK = gr.themes.Color(
    c50="#eef2fb",
    c100="#dde5f6",
    c200="#bccbec",
    c300="#92a9dc",
    c400="#6a85c8",
    c500="#4a66b0",
    c600="#3a5191",
    c700="#2f4175",
    c800="#263460",
    c900="#1f2a4e",
    c950="#141b33",
)
THEME = gr.themes.Base(
    primary_hue=INK,
    neutral_hue="slate",
    radius_size="sm",
    # Atkinson Hyperlegible was designed for legibility, which matters for small chart text
    font=[
        gr.themes.GoogleFont("Atkinson Hyperlegible"),
        "ui-sans-serif",
        "system-ui",
        "sans-serif",
    ],
)

CSS = """
.hero {
  padding: 1.5rem 1.25rem;
  margin-bottom: .5rem;
  border: 1px solid var(--border-color-primary);
  border-radius: var(--radius-md);
  background-image:
    linear-gradient(var(--border-color-primary) 1px, transparent 1px),
    linear-gradient(90deg, var(--border-color-primary) 1px, transparent 1px);
  background-size: 18px 18px;
  background-position: -1px -1px;
}
.hero h1 { margin: 0 0 .25rem; font-size: 1.9rem; line-height: 1.15; }
.hero p { margin: 0; max-width: 46rem; font-size: 1.05rem; }
.legend-wrap { overflow-x: auto; }  /* never cut off columns on a narrow screen */
table.legend { width: 100%; border-collapse: collapse; font-size: .95rem; border: 0; }
table.legend th, table.legend td {
  padding: .35rem .5rem; text-align: left; border: 0;
  border-bottom: 1px solid var(--border-color-primary);
}
table.legend .num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
table.legend td:nth-child(2) { white-space: nowrap; }
.chip {
  display: inline-block; min-width: 2.6em; padding: .1em .3em; text-align: center;
  font-weight: 700; font-size: 1.05rem; line-height: 1.3;
  border: 1px solid var(--body-text-color-subdued); border-radius: 2px;
}
table.legend .sm { display: none; }  /* short header labels are for phones */
@media (max-width: 640px) {
  table.legend .lg { display: none; }
  table.legend .sm { display: inline; }
  .gradio-container { padding-left: .5rem !important; padding-right: .5rem !important; }
  table.legend { font-size: .8rem; }
  table.legend th { font-size: .75rem; }
  table.legend th, table.legend td { padding: .25rem .2rem; }
  .chip { min-width: 2.2em; font-size: .95rem; }
}
.legend-note { margin-top: .5rem; font-size: .85rem; color: var(--body-text-color-subdued); }
"""

HERO = """
<div class="hero">
  <h1>Turn a photo into a cross stitch pattern</h1>
  <p>Add a photo, choose how detailed you want the chart, and download a PDF with the thread
  list and a chart you can stitch from.</p>
</div>
"""


def build_ui() -> gr.Blocks:
    default_width, default_colors, default_cleanup = handlers.level_to_controls(3)

    with gr.Blocks(title="Cross stitch pattern maker") as demo:
        gr.HTML(HERO)
        pattern_state = gr.State(None)

        with gr.Row(equal_height=False):
            # ---- left: set up -------------------------------------------------------------
            with gr.Column(scale=5, min_width=360):
                photo = gr.Image(
                    label="Your photo",
                    type="filepath",
                    sources=["upload", "clipboard"],
                    height=300,
                )
                with gr.Accordion("Crop the photo", open=False):
                    aspect = gr.Dropdown(
                        list(ASPECT_PRESETS), value="Whole photo", label="Shape of the pattern"
                    )
                    zoom = gr.Slider(1, 4, value=1, step=0.05, label="Zoom in")
                    pan_x = gr.Slider(0, 100, value=50, step=1, label="Move left or right")
                    pan_y = gr.Slider(0, 100, value=50, step=1, label="Move up or down")
                    crop_view = gr.Image(
                        label="Area that will be stitched",
                        interactive=False,
                        height=220,
                        buttons=[],
                    )

                craft = gr.Dropdown(
                    choices=available_crafts(),
                    value="cross_stitch",
                    label="Craft",
                    info="Bead art and an embroidery template are coming next.",
                )
                level = gr.Slider(
                    1,
                    5,
                    value=3,
                    step=1,
                    label="Detail level",
                    info="1 is very simple with few colors. 5 is expert, with many stitches.",
                )
                with gr.Accordion("Fine-tune", open=False):
                    width = gr.Slider(
                        20, 250, value=default_width, step=1, label="Width in stitches"
                    )
                    colors = gr.Slider(
                        2, 40, value=default_colors, step=1, label="Most colors to use"
                    )
                    cleanup = gr.Slider(
                        0,
                        3,
                        value=default_cleanup,
                        step=1,
                        label="Tidy stray stitches",
                        info="0 keeps every stitch. 3 removes small specks and islands.",
                    )
                    fabric = gr.Dropdown(
                        [11, 14, 16, 18], value=14, label="Fabric count (stitches per inch)"
                    )
                    strands = gr.Slider(1, 6, value=2, step=1, label="Strands of thread")

                make_btn = gr.Button("Make pattern", variant="primary", size="lg")

            # ---- right: result ------------------------------------------------------------
            with gr.Column(scale=7, min_width=440):
                summary = gr.Markdown("Your pattern will appear here.")
                preview = gr.Image(
                    label="Pattern preview",
                    interactive=False,
                    buttons=["fullscreen", "download"],
                    height=520,
                )
                pdf_file = gr.File(label="Printable PDF", interactive=False)
                with gr.Accordion("PDF options", open=False):
                    title = gr.Textbox(
                        value="Cross Stitch Pattern", label="Title", max_lines=1, max_length=80
                    )
                    paper = gr.Radio(["a4", "letter"], value="a4", label="Paper size")
                    style = gr.Radio(
                        [("Colored cells", "tint"), ("Black and white", "mono")],
                        value="tint",
                        label="Chart style",
                        info="Black and white prints clearly on any printer.",
                    )
                    pdf_btn = gr.Button("Update PDF")
                legend = gr.HTML()

        # ---- behaviour --------------------------------------------------------------------
        level.change(
            handlers.level_to_controls,
            inputs=level,
            outputs=[width, colors, cleanup],
            show_progress="hidden",
        )

        crop_inputs = [photo, aspect, zoom, pan_x, pan_y]
        for trigger in (photo.change, aspect.change, zoom.release, pan_x.release, pan_y.release):
            trigger(handlers.crop_preview, crop_inputs, crop_view, show_progress="hidden")

        make_btn.click(
            handlers.make_pattern,
            inputs=[
                photo,
                craft,
                width,
                colors,
                cleanup,
                fabric,
                strands,
                aspect,
                zoom,
                pan_x,
                pan_y,
            ],
            outputs=[preview, summary, legend, pattern_state],
            api_name="make_pattern",
        ).success(
            handlers.make_pdf,
            inputs=[pattern_state, title, paper, style],
            outputs=pdf_file,
            api_name="make_pdf",
        )
        pdf_btn.click(
            handlers.make_pdf,
            inputs=[pattern_state, title, paper, style],
            outputs=pdf_file,
            api_name="update_pdf",
        )

        demo.queue(max_size=20, default_concurrency_limit=2)
    return demo
