"""End to end: start the real app (API + Gradio UI) and drive it like a browser would."""

from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest
import uvicorn
from gradio_client import Client, handle_file

from app.main import create_app
from tests.conftest import encode


@pytest.fixture(scope="module")
def server_url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 30
    while not server.started:
        assert time.time() < deadline, "server did not start"
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


def test_ui_and_api_are_served_together(server_url):
    page = httpx.get(server_url + "/")
    assert page.status_code == 200 and "Cross stitch pattern maker" in page.text
    assert httpx.get(server_url + "/api/health").json()["status"] == "ok"


def test_full_flow_photo_to_pdf(server_url, tmp_path, noise):
    photo = tmp_path / "photo.webp"  # also proves WebP uploads survive the browser upload path
    photo.write_bytes(encode(noise, "WEBP"))
    client = Client(server_url, verbose=False)

    started = time.perf_counter()
    preview, summary, legend = client.predict(
        handle_file(str(photo)), "cross_stitch", 50, 10, 2, 14, 2,
        "Whole photo", 1, 50, 50, api_name="/make_pattern",
    )  # fmt: skip
    pdf_path = client.predict("Garden Gate", "a4", "tint", api_name="/make_pdf")
    elapsed = time.perf_counter() - started

    assert "50 × " in summary and "14-count" in summary
    assert legend.count("<tr>") >= 2
    assert preview and pdf_path
    with open(pdf_path, "rb") as f:
        assert f.read(4) == b"%PDF"
    assert elapsed < 30  # the plan's success metric, with generous room for a slow CI box


def test_unsupported_format_gets_a_friendly_message(server_url, tmp_path, bands):
    from gradio_client.exceptions import AppError

    gif = tmp_path / "photo.gif"  # a real image that Pillow can read, but we do not accept
    gif.write_bytes(encode(bands, "GIF"))
    with pytest.raises(AppError, match="only PNG, JPG and WebP"):
        Client(server_url, verbose=False).predict(
            handle_file(str(gif)), "cross_stitch", 50, 10, 2, 14, 2,
            "Whole photo", 1, 50, 50, api_name="/make_pattern",
        )  # fmt: skip


def test_corrupt_upload_is_rejected_and_the_app_keeps_working(server_url, tmp_path):
    """Known limitation: Gradio's image component rejects files Pillow cannot parse (corrupt
    files, unconverted HEIC) before our handler runs, so the message is Gradio's, not ours."""
    from gradio_client.exceptions import AppError

    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not an image")
    with pytest.raises(AppError):
        Client(server_url, verbose=False).predict(
            handle_file(str(bad)), "cross_stitch", 50, 10, 2, 14, 2,
            "Whole photo", 1, 50, 50, api_name="/make_pattern",
        )  # fmt: skip
    assert httpx.get(server_url + "/api/health").json()["status"] == "ok"


def test_pdf_button_needs_a_pattern_first(server_url):
    from gradio_client.exceptions import AppError

    with pytest.raises(AppError, match="Make a pattern first"):
        Client(server_url, verbose=False).predict("T", "a4", "tint", api_name="/update_pdf")
