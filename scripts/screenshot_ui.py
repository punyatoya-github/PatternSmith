"""Drive the real UI in headless Chromium and save screenshots (desktop and phone).

Not part of CI. Needs:  pip install playwright && playwright install chromium
Usage: python scripts/screenshot_ui.py [output_dir]
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[1]
PHOTO = REPO / "data" / "test_images" / "synthetic" / "sunflower.png"
VIEWPORTS = {
    "desktop": {"viewport": {"width": 1280, "height": 900}},
    "phone": {
        "viewport": {"width": 390, "height": 844},
        "device_scale_factor": 2,
        "is_mobile": True,
    },
}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    port = free_port()
    env = {**os.environ, "PORT": str(port)}
    server = subprocess.Popen([sys.executable, "-m", "app.main"], cwd=REPO, env=env)
    try:
        url = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.2)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name, options in VIEWPORTS.items():
                page = browser.new_context(**options).new_page()
                # Gradio keeps a connection open, so "networkidle" never fires: wait for the UI
                page.goto(url, wait_until="load")
                page.get_by_role("button", name="Make pattern").wait_for(timeout=30_000)
                page.wait_for_timeout(500)
                page.screenshot(path=out_dir / f"{name}-1-empty.png", full_page=True)

                page.locator("input[type=file]").first.set_input_files(str(PHOTO))
                page.wait_for_timeout(1500)
                started = time.perf_counter()
                page.get_by_role("button", name="Make pattern").click()
                page.get_by_text("stitches in total").wait_for(timeout=60_000)
                page.locator("a[download], a[href*='craft-pdf']").first.wait_for(timeout=60_000)
                print(f"{name}: pattern and PDF ready in {time.perf_counter() - started:.1f}s")
                page.wait_for_timeout(800)
                page.screenshot(path=out_dir / f"{name}-2-result.png", full_page=True)
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "docs" / "screenshots")
