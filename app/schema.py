"""Pydantic models for the decode request and the structured Claude response.

The ``DecodeResult`` model is passed to ``client.messages.parse(output_format=...)``
so Claude is constrained to return exactly this shape. Keeping the schema here (not
inline in decoder.py) lets the tests validate it without importing the Anthropic SDK.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Urgency(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"


class Deadline(BaseModel):
    has_deadline: bool = Field(
        description="True only if the letter states or clearly implies a concrete deadline."
    )
    date: Optional[str] = Field(
        default=None,
        description="The deadline date as written in the letter (e.g. 'March 15, 2026'). "
        "Null if there is no deadline. Never invent or estimate a date.",
    )
    description_en: str = Field(
        description="Plain-English note about what the deadline is for, or a short note "
        "telling the reader to check the document if none is stated."
    )
    description_ru: str = Field(description="Russian translation of description_en.")


class ActionStep(BaseModel):
    step_en: str = Field(description="One concrete next step, in plain English.")
    step_ru: str = Field(description="Russian translation of step_en.")
    urgency: Urgency = Field(description="How time-sensitive this specific step is.")


class DecodeResult(BaseModel):
    """The full structured decoding of one official letter."""

    document_type: str = Field(
        description="Best-guess category, e.g. 'USCIS notice', 'tax letter (IRS/FTB)', "
        "'insurance EOB', 'DMV notice', 'jury summons', or 'unknown'."
    )
    summary_en: str = Field(
        description="2-4 sentence plain-English explanation of what this letter means, "
        "at roughly an 8th-grade reading level. No legalese."
    )
    summary_ru: str = Field(description="Russian translation of summary_en.")
    deadline: Deadline
    action_steps: list[ActionStep] = Field(
        description="Ordered list of concrete next steps. May be empty if none apply."
    )
    urgency_level: Urgency = Field(description="Overall urgency of the whole letter.")
    confidence: Urgency = Field(
        description="How confident this reading is, given the text provided."
    )
    notes: str = Field(
        default="",
        description="Optional caveats, e.g. 'text looks truncated' or 'could not identify sender'.",
    )


class DecodeRequest(BaseModel):
    text: str = Field(description="Raw pasted text from the official letter.")
