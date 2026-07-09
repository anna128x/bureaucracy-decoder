"""Pure, deterministic grading helpers for the eval harness.

These functions take an already-decoded ``DecodeResult`` and a case's expectations
and return pass/fail checks. Keeping them free of any API calls lets the tests grade
a hand-built result without spending tokens.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from app.schema import DecodeResult

CASES_DIR = Path(__file__).resolve().parent / "cases"

_MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"],
        start=1,
    )
}


def _parse_date(s: str) -> Optional[tuple[int, int, int]]:
    """Extract a (year, month, day) tuple from a date string, or None.

    Handles both numeric (03/31/2026) and written ("March 31, 2026") forms so the
    grader doesn't fail just because Claude reformatted a correct date.
    """
    s = (s or "").strip()
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", s)
    if m:
        return (int(m.group(3)), int(m.group(1)), int(m.group(2)))
    m = re.search(r"\b([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})\b", s)
    if m and m.group(1).lower() in _MONTHS:
        return (int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
    return None


def _date_matches(expected_substr: str, actual_date: Optional[str]) -> bool:
    """True if the extracted date means the same calendar day as expected.

    Compares parsed (year, month, day) tuples when both sides are real calendar
    dates. Falls back to a case-insensitive substring match for relative deadlines
    like "60 days" or "180 days" that have no fixed date.
    """
    actual_date = actual_date or ""
    exp, act = _parse_date(expected_substr), _parse_date(actual_date)
    if exp and act:
        return exp == act
    return expected_substr.lower().strip() in actual_date.lower()


def load_cases() -> list[dict[str, Any]]:
    """Load every synthetic case, sorted by id for stable ordering."""
    cases = [json.loads(p.read_text()) for p in sorted(CASES_DIR.glob("*.json"))]
    return sorted(cases, key=lambda c: c["id"])


def _contains_any(haystack: str, needles: list[str]) -> bool:
    low = haystack.lower()
    return any(n.lower() in low for n in needles)


def grade_deterministic(result: DecodeResult, expected: dict[str, Any]) -> dict[str, bool]:
    """Return a dict of check-name -> passed for the deterministic checks."""
    checks: dict[str, bool] = {}

    # Category: document_type mentions one of the expected keywords.
    checks["category_match"] = _contains_any(
        result.document_type, expected.get("category_keywords", [])
    )

    # Deadline presence matches expectation.
    checks["deadline_presence"] = result.deadline.has_deadline == expected["expects_deadline"]

    # If a deadline is expected with a specific date, the extracted date should mean
    # the same calendar day (format-agnostic) — see _date_matches.
    if expected.get("expected_date_substr"):
        checks["deadline_date_match"] = _date_matches(
            expected["expected_date_substr"], result.deadline.date
        )

    # At least one action step (or the summary) should mention a key expected action.
    all_action_text = " ".join(
        [s.step_en for s in result.action_steps] + [result.summary_en, result.deadline.description_en]
    )
    checks["key_action_present"] = _contains_any(
        all_action_text, expected.get("key_action_keywords", [])
    )

    # Both languages are populated and non-trivially different (i.e. a real translation).
    checks["bilingual_populated"] = bool(
        result.summary_en.strip()
        and result.summary_ru.strip()
        and result.summary_en.strip() != result.summary_ru.strip()
    )

    return checks


def score_case(checks: dict[str, bool]) -> float:
    if not checks:
        return 0.0
    return sum(1 for v in checks.values() if v) / len(checks)
