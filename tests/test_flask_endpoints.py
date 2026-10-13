import io
import json

import numpy as np
from PIL import Image

import app as app_module
from app import app


def image_upload_bytes(image):
    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_home_endpoint_returns_html():
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    assert b'Robust Image Watermarking' in response.data


def test_results_dashboard_contains_status_and_recovery_charts():
    client = app.test_client()
    with client.session_transaction() as browser_session:
        browser_session["latest_results"] = {
            "attacks": [
                {
                    "attack": "jpeg",
                    "attack_params": {"name": "jpeg", "quality": 80},
                    "status": "measured",
                    "nc": 0.9,
                    "ber": 0.1,
                },
                {
                    "attack": "crop",
                    "attack_params": {"name": "crop", "crop_ratio": 0.5},
                    "status": "extraction_failed",
                    "nc": None,
                    "ber": None,
                },
            ]
        }

    response = client.get("/results")
    assert response.status_code == 200
    assert b'id="statusChart"' in response.data
    assert b'id="recoveryChart"' in response.data
    assert b'"status": "measured"' in response.data


def test_embed_endpoint_requires_files():
    client = app.test_client()
    response = client.post('/api/embed')
    assert response.status_code == 400


def test_extract_endpoint_requires_cover_and_reference():
    client = app.test_client()
    response = client.post('/api/extract')
    assert response.status_code == 400
    assert b'reference watermark' in response.data.lower()


def test_application_does_not_use_debug_mode_or_a_hard_coded_secret():
    assert app.debug is False
    assert app.config["SECRET_KEY"] != "robust-watermark-demo-key"
    assert len(app.config["SECRET_KEY"]) >= 32


def test_embed_robustness_and_csv_endpoints_are_integrated(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "OUTPUT_FOLDER", tmp_path)
    client = app.test_client()
    rng = np.random.default_rng(12)
    cover = rng.integers(0, 256, size=(128, 128), dtype=np.uint8)
    watermark = rng.integers(0, 256, size=(16, 16), dtype=np.uint8)

    embedded_response = client.post(
        "/api/embed",
        data={
            "cover": (image_upload_bytes(cover), "cover.png"),
            "watermark": (image_upload_bytes(watermark), "watermark.png"),
            "wavelet": "haar",
            "level": "1",
            "subband": "LL",
            "alpha": "0.05",
            "key": "integration-key",
        },
        content_type="multipart/form-data",
    )
    assert embedded_response.status_code == 200
    embedded_data = embedded_response.get_json()
    assert embedded_data["cover_preview_url"]
    assert embedded_data["watermarked_preview_url"]

    image_response = client.get(embedded_data["download_url"])
    assert image_response.status_code == 200
    result_response = client.post(
        "/api/robustness",
        data={
            "watermarked": (io.BytesIO(image_response.data), "watermarked.png"),
            "cover": (image_upload_bytes(cover), "cover.png"),
            "watermark": (image_upload_bytes(watermark), "watermark.png"),
            "wavelet": "haar",
            "level": "1",
            "subband": "LL",
            "alpha": "0.05",
            "key": "integration-key",
            "attacks": json.dumps([{"name": "jpeg", "quality": 80}]),
        },
        content_type="multipart/form-data",
    )
    assert result_response.status_code == 200
    row = result_response.get_json()["attacks"][0]
    assert row["status"] == "measured"
    assert row["nc"] < 1
    assert row["attacked_preview_url"]

    csv_response = client.get("/api/results.csv")
    assert csv_response.status_code == 200
    assert b"attack,parameters,status" in csv_response.data
    assert b"jpeg" in csv_response.data
