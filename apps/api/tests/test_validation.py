"""
Tests for input validation, file constraints, and API key authorization on POST /generate.
"""

import io


def test_missing_api_key_returns_401(client, valid_form_data, sample_png_bytes):
    files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
    response = client.post("/generate", data=valid_form_data, files=files)
    assert response.status_code == 401
    assert "Bad or missing API key" in response.json()["detail"]


def test_invalid_api_key_returns_401(client, valid_form_data, sample_png_bytes):
    files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
    headers = {"X-API-Key": "wrong-secret-key"}
    response = client.post("/generate", data=valid_form_data, files=files, headers=headers)
    assert response.status_code == 401
    assert "Bad or missing API key" in response.json()["detail"]


def test_invalid_image_type_returns_415(client, valid_form_data, valid_headers):
    fake_txt = io.BytesIO(b"Hello text file instead of image")
    files = {"image": ("notes.txt", fake_txt, "text/plain")}
    response = client.post("/generate", data=valid_form_data, files=files, headers=valid_headers)
    assert response.status_code == 415
    assert "Unsupported image type" in response.json()["detail"]


def test_oversized_image_returns_413(client, valid_form_data, valid_headers):
    # Create bytes exceeding 5 MB (5 * 1024 * 1024 + 10 bytes)
    oversized_bytes = io.BytesIO(b"0" * (5 * 1024 * 1024 + 10))
    files = {"image": ("large.png", oversized_bytes, "image/png")}
    response = client.post("/generate", data=valid_form_data, files=files, headers=valid_headers)
    assert response.status_code == 413
    assert "5 MB or smaller" in response.json()["detail"]


def test_empty_market_returns_422(client, valid_form_data, sample_png_bytes, valid_headers):
    data = {**valid_form_data, "market": "   "}
    files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
    response = client.post("/generate", data=data, files=files, headers=valid_headers)
    assert response.status_code == 422
    assert "1 and 60 characters" in response.json()["detail"]


def test_overlong_market_returns_422(client, valid_form_data, sample_png_bytes, valid_headers):
    data = {**valid_form_data, "market": "A" * 61}
    files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
    response = client.post("/generate", data=data, files=files, headers=valid_headers)
    assert response.status_code == 422
    assert "1 and 60 characters" in response.json()["detail"]


def test_invalid_language_returns_422(client, valid_form_data, sample_png_bytes, valid_headers):
    data = {**valid_form_data, "language": "fr"}
    files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
    response = client.post("/generate", data=data, files=files, headers=valid_headers)
    assert response.status_code == 422


def test_missing_required_fields_returns_422(client, sample_png_bytes, valid_headers):
    # Completely empty form data
    files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
    response = client.post("/generate", data={}, files=files, headers=valid_headers)
    assert response.status_code == 422
