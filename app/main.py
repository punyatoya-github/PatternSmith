"""Application entry point: FastAPI (REST API under /api) with the Gradio UI mounted at /.

Run it with:  python -m app.main     (or: uvicorn app.main:app --reload --port 7860)
"""

from __future__ import annotations

import os

from fastapi import FastAPI

from app import __version__
from app.api.routes import router


def create_app(with_ui: bool = True) -> FastAPI:
    api = FastAPI(
        title="AI Craft Pattern Generator",
        version=__version__,
        description="Turn photos into printable craft patterns.",
    )
    api.include_router(router)
    if not with_ui:
        return api

    import gradio as gr

    from app.ui.layout import CSS, THEME, build_ui

    # ssr_mode=False: no dependency on a Node server for server-side rendering
    return gr.mount_gradio_app(
        api,
        build_ui(),
        path="/",
        theme=THEME,
        css=CSS,
        ssr_mode=False,
        footer_links=["gradio"],  # our own API is documented at /docs, not Gradio's
    )


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "7860")),
    )


if __name__ == "__main__":
    run()
