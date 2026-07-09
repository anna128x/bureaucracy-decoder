# Eval Report — Bureaucracy Decoder

- Cases: **9** synthetic letters (no real PII)
- Deterministic checks mean: **98%**
- LLM-judge English readability mean: **5.00/5**
- LLM-judge Russian faithfulness mean: **5.00/5**

| Case | Deterministic | Readability (EN) | Faithfulness (RU) | Failed checks |
|---|---|---|---|---|
| dmv_registration | 100% | 5/5 | 5/5 | — |
| ftb_balance | 100% | 5/5 | 5/5 | — |
| insurance_eob | 100% | 5/5 | 5/5 | — |
| irs_cp2000 | 100% | 5/5 | 5/5 | — |
| jury_summons | 80% | 5/5 | 5/5 | deadline_date_match |
| ssa_award | 100% | 5/5 | 5/5 | — |
| uscis_biometrics | 100% | 5/5 | 5/5 | — |
| uscis_receipt | 100% | 5/5 | 5/5 | — |
| uscis_rfe | 100% | 5/5 | 5/5 | — |
