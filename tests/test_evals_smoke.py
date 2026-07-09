"""Smoke tests for the eval harness — cases load and grading logic is sound.

Does not call the API. Grades the shared sample_result against hand-built cases so
the grading functions are exercised deterministically.
"""

from evals.grading import grade_deterministic, load_cases, score_case


def test_cases_load():
    cases = load_cases()
    assert len(cases) >= 8
    for c in cases:
        assert "letter_text" in c and c["letter_text"].strip()
        exp = c["expected"]
        assert "category_keywords" in exp
        assert isinstance(exp["expects_deadline"], bool)


def test_grading_rewards_a_good_result(sample_result):
    # A USCIS-receipt-style expectation the sample_result should satisfy.
    expected = {
        "category_keywords": ["uscis", "notice"],
        "expects_deadline": False,
        "key_action_keywords": ["case status", "receipt number"],
    }
    checks = grade_deterministic(sample_result, expected)
    assert checks["category_match"] is True
    assert checks["deadline_presence"] is True
    assert checks["bilingual_populated"] is True
    assert score_case(checks) == 1.0


def test_grading_penalizes_wrong_deadline(sample_result):
    # Expect a deadline the sample_result doesn't have -> that check fails.
    expected = {
        "category_keywords": ["uscis"],
        "expects_deadline": True,
        "expected_date_substr": "March 3, 2026",
        "key_action_keywords": ["case status"],
    }
    checks = grade_deterministic(sample_result, expected)
    assert checks["deadline_presence"] is False
    assert checks["deadline_date_match"] is False
    assert score_case(checks) < 1.0
