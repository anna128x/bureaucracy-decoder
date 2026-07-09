"""The structured schema is the contract with Claude — validate it holds."""

import pytest
from pydantic import ValidationError

from app.schema import DecodeResult, Urgency


def test_sample_result_round_trips(sample_result):
    dumped = sample_result.model_dump()
    assert dumped["document_type"] == "USCIS notice"
    assert dumped["deadline"]["has_deadline"] is False
    # Re-parsing the dumped dict yields an equivalent object.
    assert DecodeResult(**dumped) == sample_result


def test_urgency_is_constrained():
    with pytest.raises(ValidationError):
        DecodeResult(
            document_type="x",
            summary_en="a",
            summary_ru="b",
            deadline={"has_deadline": False, "date": None, "description_en": "x", "description_ru": "y"},
            action_steps=[],
            urgency_level="EXTREME",  # not a valid Urgency
            confidence=Urgency.low,
        )


def test_deadline_date_optional():
    r = DecodeResult(
        document_type="tax letter (IRS/FTB)",
        summary_en="You owe a balance.",
        summary_ru="У вас есть задолженность.",
        deadline={"has_deadline": True, "date": "March 3, 2026",
                  "description_en": "Pay by this date.", "description_ru": "Оплатите до этой даты."},
        action_steps=[],
        urgency_level=Urgency.high,
        confidence=Urgency.medium,
    )
    assert r.deadline.date == "March 3, 2026"
