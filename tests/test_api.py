"""Endpoint tests with the Claude call mocked — no tokens spent, no key needed."""

import pytest
from fastapi.testclient import TestClient

import app.main as main


@pytest.fixture
def client(monkeypatch, sample_result):
    # Replace the real decoders with stubs so no API call happens.
    monkeypatch.setattr(main, "decode_letter", lambda text: sample_result)
    monkeypatch.setattr(main, "decode_document", lambda data, media_type: sample_result)
    # Reset the rate-limiter between tests.
    main._hits.clear()
    return TestClient(main.app)


def test_decode_success(client):
    resp = client.post("/api/decode", json={"text": "USCIS I-797C Notice of Action..."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_type"] == "USCIS notice"
    assert body["summary_ru"]  # Russian present
    assert body["deadline"]["has_deadline"] is False


def test_empty_text_rejected(client):
    resp = client.post("/api/decode", json={"text": "   "})
    assert resp.status_code == 400


def test_too_long_rejected(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_INPUT_CHARS", 50)
    resp = client.post("/api/decode", json={"text": "x" * 100})
    assert resp.status_code == 413


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 2)
    main._hits.clear()
    payload = {"text": "some letter text"}
    assert client.post("/api/decode", json=payload).status_code == 200
    assert client.post("/api/decode", json=payload).status_code == 200
    assert client.post("/api/decode", json=payload).status_code == 429


def test_decode_file_success(client):
    resp = client.post(
        "/api/decode-file",
        files={"file": ("scan.png", b"\x89PNG\r\n\x1a\nfake-image-bytes", "image/png")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_type"] == "USCIS notice"
    assert body["summary_ru"]  # Russian present


def test_decode_file_pdf_success(client):
    resp = client.post(
        "/api/decode-file",
        files={"file": ("letter.pdf", b"%PDF-1.4 fake-pdf-bytes", "application/pdf")},
    )
    assert resp.status_code == 200


def test_decode_file_bad_type(client):
    resp = client.post(
        "/api/decode-file",
        files={"file": ("notes.txt", b"just some text", "text/plain")},
    )
    assert resp.status_code == 415


def test_decode_file_empty_rejected(client):
    resp = client.post(
        "/api/decode-file",
        files={"file": ("scan.png", b"", "image/png")},
    )
    assert resp.status_code == 400


def test_decode_file_too_large(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_FILE_BYTES", 10)
    resp = client.post(
        "/api/decode-file",
        files={"file": ("scan.png", b"x" * 100, "image/png")},
    )
    assert resp.status_code == 413


def test_decode_file_shares_rate_limit(client, monkeypatch):
    # The file endpoint uses the same per-IP limiter as the text endpoint.
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 2)
    main._hits.clear()
    assert client.post("/api/decode", json={"text": "a letter"}).status_code == 200
    file = {"file": ("scan.png", b"\x89PNGbytes", "image/png")}
    assert client.post("/api/decode-file", files=file).status_code == 200
    assert client.post("/api/decode-file", files=file).status_code == 429


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}
