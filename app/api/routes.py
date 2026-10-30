"""REST API. Thin wrappers around the service layer, so the UI and API behave identically.

Endpoints are plain ``def`` functions: FastAPI runs them in a worker thread, so the CPU-bound
image work does not block the event loop.
"""

from __future__ import annotations

import io
import json
import re

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError

from app import __version__
from app.core import config
from app.schemas.api import (
    CraftOut,
    FinishedSizeOut,
    GenerateResponse,
    PdfRequest,
    PreviewRequest,
)
from app.schemas.settings import CraftSettings
from app.services.crafts.render import render_grid_preview
from app.services.generation import available_crafts, generate
from app.services.imaging.io import InvalidImageError, load_image
from app.services.pdf.cross_stitch_pdf import build_cross_stitch_pdf

router = APIRouter(prefix="/api", tags=["patterns"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/crafts", response_model=list[CraftOut])
def crafts() -> list[CraftOut]:
    return [CraftOut(id=craft_id, label=label) for label, craft_id in available_crafts()]


@router.post("/generate", response_model=GenerateResponse)
def generate_pattern(
    file: UploadFile = File(..., description="PNG, JPG or WebP photo, up to 10 MB"),
    settings: str = Form("{}", description="CraftSettings as JSON; missing fields use defaults"),
) -> GenerateResponse:
    try:
        parsed = CraftSettings.model_validate_json(settings)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from None

    data = file.file.read(config.MAX_UPLOAD_BYTES + 1)  # never read more than the limit allows
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file is larger than 10 MB")
    try:
        image = load_image(data)
        output = generate(image, parsed)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except ValueError as exc:  # e.g. the pattern would be too tall; the message says how to fix it
        raise HTTPException(status_code=422, detail=str(exc)) from None

    return GenerateResponse(
        pattern=output.pattern,
        inventory=output.inventory,
        finished_size=FinishedSizeOut(**vars(output.size)),
    )


@router.post("/preview", response_class=Response, responses={200: {"content": {"image/png": {}}}})
def preview(request: PreviewRequest) -> Response:
    image = render_grid_preview(
        request.pattern,
        cell_px=request.cell_px,
        show_symbols=request.show_symbols,
        show_grid=request.show_grid,
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@router.post(
    "/export/pdf", response_class=Response, responses={200: {"content": {"application/pdf": {}}}}
)
def export_pdf(request: PdfRequest) -> Response:
    pdf = build_cross_stitch_pdf(
        request.pattern, title=request.title, paper=request.paper, style=request.style
    )
    filename = re.sub(r"[^A-Za-z0-9_-]+", "-", request.title).strip("-") or "pattern"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )
