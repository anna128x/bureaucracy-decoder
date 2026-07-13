# Bureaucracy Decoder

**Paste the text of a confusing US government or insurance letter — get back, in plain
English and Russian, what it means, what deadline applies, and what to do next.**

> _Live demo: https://bureaucracy-decoder.onrender.com/_

A USCIS notice, an IRS or state tax letter, an insurance Explanation of Benefits — these
arrive in dense officialese, often to people who are still learning English. This tool
turns one into a two-column, plain-language explanation with the deadline pulled out and
concrete next steps, in **English and Russian**.

It's built on the Claude API with a small, honest surface: one structured model call, a
simple web UI, a real evaluation harness, and a runbook so it keeps working after I'm
gone.

## Why Russian, and why me

I grew up translating official mail for my Russian-speaking family — the immigration
notices, the tax letters, the insurance statements nobody could parse. This tool is that
job, done better and given away. That's also why it's engineered for handoff rather than
as a throwaway demo: the point is that it keeps running for the people who need it.

## What it does

- **Plain-language summary** in English and Russian, at ~8th-grade reading level.
- **Deadline extraction** — the date, or an honest "no clear deadline; check the
  document." It will **not** invent a deadline.
- **Next steps** — concrete, ordered actions, each tagged by urgency.
- **Document-type detection** and a confidence signal.

## How it works

```
Browser (static/)  ──POST /api/decode──▶  FastAPI (app/main.py)
                                              │
                                              ▼
                         app/decoder.py → client.messages.parse(...)
                                              │  one structured Claude call
                                              ▼
                         DecodeResult (app/schema.py) → JSON → rendered EN/RU
```

- **One structured call.** `client.messages.parse(output_format=DecodeResult)` constrains
  Claude to a typed Pydantic schema, so the deadline, action steps, and both languages
  come back reliably in a single request — no brittle string parsing.
- **Model.** Defaults to `claude-opus-4-8`; set `ANTHROPIC_MODEL=claude-sonnet-5` for a
  cheaper public demo (see `RUNBOOK.md`).

## Judgment built in (the part that isn't code)

This decodes sensitive government and medical letters, so it's deliberately conservative:

- **Never invents a deadline.** If the letter doesn't state one, it says so.
- **Not advice.** Every screen carries: _informational only — not legal, tax, or medical
  advice; verify against your original document and consult a professional or the issuing
  agency._
- **Stores nothing.** Pasted letter text is never saved or logged — it exists only in
  memory for the length of one request. That's a design choice, stated in the UI.
- **Guards the demo.** Input length cap + per-IP rate limit; a spend cap on the API key.

## Evaluation harness

A tool that reads people's official mail has to be *checked*, not vibe-tested. `evals/`
holds ~10 **synthetic** letters (USCIS receipt / biometrics / RFE, IRS CP2000, CA FTB,
insurance EOB, DMV, jury summons, SSA award — no real PII) each with expected fields.

`python -m evals.run_evals` grades every case two ways:

- **Deterministic:** schema-valid, deadline presence + date match, document-type match,
  a key action present, and both languages populated and genuinely different.
- **LLM-judge:** a separate Claude call rates English readability (1–5) and the
  faithfulness of the Russian translation (1–5) against a rubric.

It prints a scorecard and writes [`evals/REPORT.md`](evals/REPORT.md).

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload # open http://localhost:8000
```

```bash
pytest                        # tests; mocks the Claude call, no API key needed
python -m evals.run_evals     # run the eval scorecard (needs a key)
```

Full run/deploy/handoff instructions are in **[RUNBOOK.md](RUNBOOK.md)**.

## Deploy

`render.yaml` is included for one-click Render deploys; Hugging Face Spaces is the
free-forever alternative. See `RUNBOOK.md` → Deploy. Set `ANTHROPIC_API_KEY` as a secret
and put a spend cap on that key.

## Not for

Legal, tax, or medical advice; automated filing or decisions; storing anyone's letters.
It explains — it doesn't act on your behalf.
