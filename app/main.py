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
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.decoder import decode_letter
from app.schema import DecodeRequest

load_dotenv()

MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", "12000"))
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "6"))

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

    try:
        result = decode_letter(text)
    except anthropic.APIStatusError as exc:  # upstream API problem
        return JSONResponse(status_code=502, content={"error": f"Decoding service error: {exc.message}"})
    except anthropic.APIConnectionError:
        return JSONResponse(status_code=502, content={"error": "Could not reach the decoding service. Try again."})
    except ValueError as exc:  # refusal / unparseable
        return JSONResponse(status_code=422, content={"error": str(exc)})

    # Nothing is persisted — we return the structured result and forget the input.
    return JSONResponse(content=result.model_dump())


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


# Serve the SPA at "/". Mounted last so /api and /healthz take precedence.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
