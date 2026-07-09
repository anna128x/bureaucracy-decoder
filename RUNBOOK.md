# RUNBOOK — Bureaucracy Decoder

This is the "make it survive you" document: how to run it, deploy it, keep it healthy,
and hand it off. If you own this after the original author leaves, start here.

## What it is

A small FastAPI web app. A user pastes the text of an official US letter; the app makes
**one** structured Claude API call and returns a plain-language explanation (English +
Russian), the deadline (if any), and next steps.

```
static/          the whole front end (one HTML page + JS + CSS)
app/main.py      FastAPI routes, rate limit, no-storage handling
app/decoder.py   the single Claude call (client.messages.parse)
app/schema.py    the response shape Claude must return
app/prompts.py   the system prompt (safety rules live here)
evals/           synthetic test letters + grading harness
tests/           pytest (no API key needed — the Claude call is mocked)
```

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then paste your ANTHROPIC_API_KEY into .env
uvicorn app.main:app --reload
```

Open http://localhost:8000, paste a letter (use one from `evals/cases/*.json` to try it),
click **Decode**.

## Configuration (environment variables)

| Var | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Your Anthropic API key. |
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Which model to use. See "Cost" below. |
| `MAX_INPUT_CHARS` | `12000` | Reject letters longer than this (cost/abuse guard). |
| `RATE_LIMIT_PER_MINUTE` | `6` | Per-IP request cap for the public demo. |

## Cost control (read before deploying a public demo)

- Each decode is one API call (~a few thousand tokens). At `claude-opus-4-8` that's a
  few cents; at `claude-sonnet-5` it's roughly 5x cheaper and still strong at Russian.
  **For a public demo, set `ANTHROPIC_MODEL=claude-sonnet-5`.**
- **Set a spend cap** on the API key used for the public demo, in the Anthropic Console
  (Billing → Limits). This is the real safety net if the demo gets hammered.
- The per-IP rate limit (`RATE_LIMIT_PER_MINUTE`) and input length cap are first-line
  defenses, but they are per-instance and in-memory — not a substitute for the spend cap.

## Deploy

### Render (blueprint included)
1. Push this repo to GitHub.
2. Render → **New → Blueprint**, select the repo (`render.yaml` is auto-detected).
3. Set `ANTHROPIC_API_KEY` as a secret env var in the Render dashboard.
4. Deploy. The start command is `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

Note: Render's free tier sleeps after inactivity and instances are not permanent.

### Hugging Face Spaces (free, runs indefinitely — best for "still running in 6 months")
1. Create a Space, SDK = **Docker** (or Gradio/Custom); simplest is a tiny Dockerfile
   that installs `requirements.txt` and runs the uvicorn command above on port 7860.
2. Add `ANTHROPIC_API_KEY` as a **Space secret**.
3. Push the repo. This is the better choice if you want the demo link alive long-term.

## Health check

`GET /healthz` returns `{"status": "ok"}`. Point your host's health check at it.

## Tests and evals

```bash
pytest                       # fast; mocks the Claude call, no API key needed
python -m evals.run_evals    # real API calls over evals/cases/, writes evals/REPORT.md
python -m evals.run_evals --no-judge   # skip the LLM-judge pass (cheaper)
```

Add a new test letter by dropping a `*.json` file in `evals/cases/` matching the shape of
the existing ones (`id`, `letter_text`, `expected`). **Use synthetic data only — never a
real person's letter.**

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| 500 on startup / "api_key" error | `ANTHROPIC_API_KEY` not set in the environment / `.env`. |
| Every decode returns 502 | Upstream API error or bad key. Check the key and Anthropic status. |
| 429 to users | They hit `RATE_LIMIT_PER_MINUTE`. Raise it, or it's working as intended. |
| Russian looks off | Try `ANTHROPIC_MODEL=claude-opus-4-8` (higher quality than sonnet). |
| Bill higher than expected | Confirm the spend cap is set; lower the model or rate limit. |

## Handoff checklist

- [ ] New owner can run it locally with their own key.
- [ ] New owner has run `pytest` (green) and `python -m evals.run_evals` (scorecard).
- [ ] New owner has watched a real decode end-to-end and read a Russian output.
- [ ] Spend cap is set on the deployed key; new owner knows where it is.
- [ ] New owner knows this is **not legal/tax/medical advice** and that pasted text is
      intentionally never stored.
