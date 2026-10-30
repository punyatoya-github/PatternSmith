import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.main import create_app
from tests.conftest import encode


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app(with_ui=False))


def _generate(client, image_bytes, settings=None, filename="photo.png", content_type="image/png"):
    data = {"settings": json.dumps(settings)} if settings is not None else {}
    return client.post(
        "/api/generate", files={"file": (filename, image_bytes, content_type)}, data=data
    )


@pytest.fixture
def pattern(client, noise):
    response = _generate(client, encode(noise), {"width": 40, "colors": 8})
    assert response.status_code == 200
    return response.json()["pattern"]


def test_health_and_crafts(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert {"id": "cross_stitch", "label": "Cross stitch"} in client.get("/api/crafts").json()


def test_generate_returns_pattern_inventory_and_size(client, noise):
    response = _generate(client, encode(noise), {"width": 40, "colors": 8})
    assert response.status_code == 200
    body = response.json()
    assert body["pattern"]["width"] == 40
    assert len(body["pattern"]["palette"]) <= 8
    assert [i["code"] for i in body["inventory"]] == [e["code"] for e in body["pattern"]["palette"]]
    assert body["finished_size"]["width_in"] == round(40 / 14, 1)


def test_generate_uses_defaults_when_settings_omitted(client, bands):
    response = _generate(client, encode(bands))
    assert response.status_code == 200
    assert response.json()["pattern"]["width"] == 100


def test_generate_accepts_webp_and_jpeg(client, bands):
    for fmt, mime in (("WEBP", "image/webp"), ("JPEG", "image/jpeg")):
        assert (
            _generate(client, encode(bands, fmt), {"width": 30}, content_type=mime).status_code
            == 200
        )


def test_generate_applies_crop(client, bands):
    settings = {"width": 30, "colors": 3, "crop": {"left": 0, "right": 1 / 3}}
    response = _generate(client, encode(bands), settings)
    assert len(response.json()["pattern"]["palette"]) == 1  # only the red band is left


@pytest.mark.parametrize(
    "settings",
    [{"width": 5}, {"colors": 99}, {"fabric_count": 13}, {"crop": {"left": 0.9, "right": 0.1}}],
)
def test_generate_rejects_bad_settings(client, bands, settings):
    response = _generate(client, encode(bands), settings)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_generate_rejects_non_json_settings(client, bands):
    response = client.post(
        "/api/generate",
        files={"file": ("a.png", encode(bands), "image/png")},
        data={"settings": "not json"},
    )
    assert response.status_code == 422


def test_generate_rejects_bad_uploads(client, bands):
    assert _generate(client, b"not an image").status_code == 400
    assert _generate(client, encode(bands, "GIF"), content_type="image/gif").status_code == 400


def test_generate_rejects_oversized_upload(client, bands, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 100)
    assert _generate(client, encode(bands)).status_code == 413


def test_generate_explains_too_tall_images(client):
    tall = np.zeros((2000, 100, 3), dtype=np.uint8)
    response = _generate(client, encode(tall), {"width": 100})
    assert response.status_code == 422 and "crop" in response.json()["detail"]


def test_missing_file_is_a_validation_error(client):
    assert client.post("/api/generate", data={"settings": "{}"}).status_code == 422


def test_preview_returns_png_of_expected_size(client, pattern):
    response = client.post("/api/preview", json={"pattern": pattern, "cell_px": 6})
    assert response.status_code == 200 and response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_preview_rejects_huge_output(client, pattern):
    assert client.post("/api/preview", json={"pattern": pattern, "cell_px": 40}).status_code == 200
    big = {**pattern, "width": 250, "grid": [[0] * 250 for _ in range(pattern["height"])]}
    assert client.post("/api/preview", json={"pattern": big, "cell_px": 40}).status_code == 422


def test_export_pdf(client, pattern):
    response = client.post(
        "/api/export/pdf",
        json={"pattern": pattern, "title": "My Garden!", "paper": "letter", "style": "mono"},
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert response.headers["content-disposition"] == 'attachment; filename="My-Garden.pdf"'


def test_export_pdf_accepts_any_script_in_title(client, pattern):
    response = client.post("/api/export/pdf", json={"pattern": pattern, "title": "花 🌻 Rose"})
    assert response.status_code == 200 and response.content.startswith(b"%PDF")


@pytest.mark.parametrize("override", [{"paper": "a3"}, {"style": "neon"}, {"title": ""}])
def test_export_pdf_validates_options(client, pattern, override):
    assert client.post("/api/export/pdf", json={"pattern": pattern, **override}).status_code == 422


def test_export_pdf_rejects_tampered_patterns(client, pattern):
    bad_index = json.loads(json.dumps(pattern))
    bad_index["grid"][0][0] = 99
    assert client.post("/api/export/pdf", json={"pattern": bad_index}).status_code == 422

    too_wide = {**pattern, "width": 5000, "grid": [[0] * 5000]}
    assert client.post("/api/export/pdf", json={"pattern": too_wide}).status_code == 422
