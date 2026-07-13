"""FastAPI app: serves the single-page UI and the /api/decode endpoint.

Deliberate choices (judgment/safety signal for the project):
  * No pasted letter text is ever stored or logged. It lives only in memory for the
    duration of the request. These are sensitive government/medical letters.
  * Input length is capped and a simple per-IP rate limit protects the public demo
    from abuse and runaway API spend.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.decoder import decode_document, decode_letter
from app.prompts import IMAGE_MEDIA_TYPES, PDF_MEDIA_TYPE
from app.schema import DecodeRequest

load_dotenv()

MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", "12000"))
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "6"))
# Cap uploads well under the Anthropic 32 MB request limit for the public demo.
MAX_FILE_BYTES = int(os.environ.get("MAX_FILE_BYTES", str(10 * 1024 * 1024)))
ALLOWED_MEDIA_TYPES = frozenset((PDF_MEDIA_TYPE, *IMAGE_MEDIA_TYPES))

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Bureaucracy Decoder")

# In-memory sliding-window rate limiter (per client IP). Fine for a single-instance
# free-tier demo; swap for Redis if this ever needs to scale horizontally.
_hits: dict[str, deque[float]] = defaultdict(deque)


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    window = _hits[ip]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_MINUTE:
        return True
    window.append(now)
    return False


def _run_decode(decode_call) -> JSONResponse:
    """Run a decoder call and map failures to the same friendly HTTP responses.

    Shared by the text and file endpoints so both surface upstream API errors,
    connection problems, and refusals/unparseable output identically. Nothing is
    persisted — we return the structured result and forget the input.
    """
    try:
        result = decode_call()
    except anthropic.APIStatusError as exc:  # upstream API problem (incl. oversized/too-many-pages)
        return JSONResponse(status_code=502, content={"error": f"Decoding service error: {exc.message}"})
    except anthropic.APIConnectionError:
        return JSONResponse(status_code=502, content={"error": "Could not reach the decoding service. Try again."})
    except ValueError as exc:  # refusal / unparseable
        return JSONResponse(status_code=422, content={"error": str(exc)})
    return JSONResponse(content=result.model_dump())


@app.post("/api/decode")
async def decode(req: DecodeRequest, request: Request) -> JSONResponse:
    text = (req.text or "").strip()
    if not text:
        return JSONResponse(status_code=400, content={"error": "Please paste the letter text."})
    if len(text) > MAX_INPUT_CHARS:
        return JSONResponse(
            status_code=413,
            content={"error": f"That text is too long (limit {MAX_INPUT_CHARS} characters). "
                              "Paste one letter at a time."},
        )

    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "You're going a bit fast — please wait a minute and try again."},
        )

    return _run_decode(lambda: decode_letter(text))


@app.post("/api/decode-file")
async def decode_file(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    media_type = file.content_type or ""
    if media_type not in ALLOWED_MEDIA_TYPES:
        return JSONResponse(
            status_code=415,
            content={"error": "Please upload a PDF or a photo (PNG, JPEG, GIF, or WebP) of the letter."},
        )

    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "You're going a bit fast — please wait a minute and try again."},
        )

    data = await file.read()
    if not data:
        return JSONResponse(status_code=400, content={"error": "That file appears to be empty."})
    if len(data) > MAX_FILE_BYTES:
        limit_mb = MAX_FILE_BYTES // (1024 * 1024)
        return JSONResponse(
            status_code=413,
            content={"error": f"That file is too large (limit {limit_mb} MB). "
                              "Try a smaller photo or one letter at a time."},
        )

    return _run_decode(lambda: decode_document(data, media_type))


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


# Serve the SPA at "/". Mounted last so /api and /healthz take precedence.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
