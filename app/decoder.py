"""Core Claude integration: one structured call that decodes a letter.

We use ``client.messages.parse(output_format=DecodeResult)`` so the Anthropic SDK
validates the response against our Pydantic schema and hands back a typed object —
the reliable way to get structured extraction (deadline, action steps, both
languages) in a single request.

Model note: default is ``claude-opus-4-8`` (highest quality). Set ANTHROPIC_MODEL to
``claude-sonnet-5`` for the cost-sensitive public demo — see RUNBOOK.md.
"""

from __future__ import annotations

import base64
import os

import anthropic

from app.prompts import SYSTEM_PROMPT, build_file_content, build_user_content
from app.schema import DecodeResult

DEFAULT_MODEL = "claude-opus-4-8"
MAX_TOKENS = 2048


def _client() -> anthropic.Anthropic:
    # Reads ANTHROPIC_API_KEY from the environment (or an `ant auth login` profile).
    return anthropic.Anthropic()


def _parse(content: list[dict], *, client: anthropic.Anthropic | None = None) -> DecodeResult:
    """Run the single structured Claude call for whatever user content we built.

    Raises anthropic.APIError subclasses on API failure; callers handle those.
    """
    client = client or _client()
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    response = client.messages.parse(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        output_format=DecodeResult,
    )

    result = response.parsed_output
    if result is None:
        # Model refused or output could not be parsed to the schema.
        raise ValueError("Could not decode this letter into the expected format.")
    return result


def decode_letter(letter_text: str, *, client: anthropic.Anthropic | None = None) -> DecodeResult:
    """Decode one letter's pasted text into a structured, bilingual explanation."""
    return _parse(build_user_content(letter_text), client=client)


def decode_document(
    data: bytes, media_type: str, *, client: anthropic.Anthropic | None = None
) -> DecodeResult:
    """Decode one letter uploaded as a PDF or photo/scan.

    Claude reads the text out of the document itself — no OCR step. ``media_type`` must
    be one of the types ``build_file_content`` accepts, or it raises ValueError.
    """
    data_b64 = base64.standard_b64encode(data).decode("ascii")
    return _parse(build_file_content(data_b64, media_type), client=client)
