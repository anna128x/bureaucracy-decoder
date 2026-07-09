"""Run the decoder over every synthetic case, grade it, and write a scorecard.

Grading is two-part:
  * Deterministic (evals/grading.py): schema-valid, deadline presence/date match,
    category match, key action present, both languages populated.
  * LLM-judge: a separate Claude call rates summary_en readability (1-5) and the
    faithfulness of the Russian translation (1-5) against a rubric.

Usage:
    python -m evals.run_evals            # full run, needs ANTHROPIC_API_KEY
    python -m evals.run_evals --no-judge # skip the LLM-judge pass

Writes evals/REPORT.md (committed; the README cites its numbers).
"""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.decoder import decode_letter
from app.schema import DecodeResult
from evals.grading import grade_deterministic, load_cases, score_case

REPORT_PATH = Path(__file__).resolve().parent / "REPORT.md"
JUDGE_MODEL = "claude-opus-4-8"


class JudgeScore(BaseModel):
    readability_en: int = Field(ge=1, le=5, description="How plain/clear is the English summary (1-5).")
    faithfulness_ru: int = Field(ge=1, le=5, description="How faithful is the Russian to the English (1-5).")
    comment: str = Field(default="", description="One-line justification.")


JUDGE_SYSTEM = (
    "You are a strict grader. You will be given the English and Russian plain-language "
    "summaries a tool produced for an official US letter. Score two things on a 1-5 scale:\n"
    "readability_en: is the English clear, jargon-free, ~8th-grade level? (5 = excellent)\n"
    "faithfulness_ru: does the Russian faithfully convey the same meaning as the English, "
    "in natural Russian? (5 = excellent). Return only the structured score."
)


def judge(client: anthropic.Anthropic, result: DecodeResult) -> JudgeScore:
    resp = client.messages.parse(
        model=JUDGE_MODEL,
        max_tokens=512,
        system=JUDGE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"ENGLISH SUMMARY:\n{result.summary_en}\n\nRUSSIAN SUMMARY:\n{result.summary_ru}",
            }
        ],
        output_format=JudgeScore,
    )
    return resp.parsed_output


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-judge", action="store_true", help="Skip the LLM-judge pass.")
    args = parser.parse_args()

    client = anthropic.Anthropic()
    cases = load_cases()

    rows = []
    det_scores: list[float] = []
    read_scores: list[int] = []
    faith_scores: list[int] = []

    print(f"Running {len(cases)} cases...\n")
    for case in cases:
        result = decode_letter(case["letter_text"], client=client)
        checks = grade_deterministic(result, case["expected"])
        det = score_case(checks)
        det_scores.append(det)

        js = None
        if not args.no_judge:
            js = judge(client, result)
            read_scores.append(js.readability_en)
            faith_scores.append(js.faithfulness_ru)

        failed = [k for k, v in checks.items() if not v]
        judge_str = f"read={js.readability_en}/5 faith={js.faithfulness_ru}/5" if js else "—"
        print(
            f"  {case['id']:<20} det={det:>4.0%}  {judge_str}"
            + (f"  FAILED: {', '.join(failed)}" if failed else "")
        )
        rows.append((case["id"], det, checks, js))

    write_report(rows, det_scores, read_scores, faith_scores)
    print(f"\nWrote {REPORT_PATH}")
    print(f"Deterministic mean: {statistics.mean(det_scores):.0%}")
    if read_scores:
        print(f"Readability mean:   {statistics.mean(read_scores):.2f}/5")
        print(f"Faithfulness mean:  {statistics.mean(faith_scores):.2f}/5")


def write_report(rows, det_scores, read_scores, faith_scores) -> None:
    lines = ["# Eval Report — Bureaucracy Decoder", ""]
    lines.append(f"- Cases: **{len(rows)}** synthetic letters (no real PII)")
    lines.append(f"- Deterministic checks mean: **{statistics.mean(det_scores):.0%}**")
    if read_scores:
        lines.append(f"- LLM-judge English readability mean: **{statistics.mean(read_scores):.2f}/5**")
        lines.append(f"- LLM-judge Russian faithfulness mean: **{statistics.mean(faith_scores):.2f}/5**")
    lines += ["", "| Case | Deterministic | Readability (EN) | Faithfulness (RU) | Failed checks |",
              "|---|---|---|---|---|"]
    for case_id, det, checks, js in rows:
        failed = ", ".join(k for k, v in checks.items() if not v) or "—"
        read = f"{js.readability_en}/5" if js else "—"
        faith = f"{js.faithfulness_ru}/5" if js else "—"
        lines.append(f"| {case_id} | {det:.0%} | {read} | {faith} | {failed} |")
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
