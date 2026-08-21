# Tips & Troubleshooting — what actually happened

**LAB | LLMs grading LLMs—with receipts**
**Author:** Nnanyelugo Ahukannah

The lab's Tips section names four common issues. All four came up. This records
what each looked like in practice and what the build does about it, because the
handling is in the code and is otherwise easy to miss.

## 1. JSON parsing errors in judge responses

**What the lab warns about:** the judge returns something that is not valid JSON.

**What was done.** The judge call sets `response_format={"type": "json_object"}`
(`llm_judge_evaluation.py`), which is the lab's own first suggestion, and no parse
failure occurred across 30 judgements. The `try/except` around `json.loads` is
still there, and it does something deliberate rather than re-raising:

```python
except json.JSONDecodeError as exc:
    parsed = {"score": 1, "reasoning": f"Judge output could not be parsed: {exc}", ...}
```

**An unparseable judgement scores 1, it does not error and it is not dropped.**
Dropping it would remove it from the denominator and flatter the model — in
production an unparseable letter is a failure, so it has to score like one. The
recorded `_parse_error` field preserves the cause for anyone auditing later.

## 2. Inconsistent judge scores

**What the lab warns about:** LLM judges have variance; consider averaging.

**What was done.** Temperature 0, and **three repeats per letter** — not to average
the noise away but to *measure* whether there is any. The pipeline records
`scores`, `score_mean`, `score_range` and an `unstable` flag per letter.

The result was more interesting than the warning suggested: **score range was 0 on
all 10 letters.** That mattered, because it turned "the judge is unreliable" into
the much stronger and more actionable "the judge has a stable bias" — a judge that
is consistently wrong in one direction is a different problem from a noisy one,
and only repeats could tell them apart.

## 3. High API costs

**What the lab warns about:** use a small model, cache, start with a small set.

**What was done.** `gpt-4o-mini` as the judge throughout; five test cases; a
`CostLedger` that tallies every call and **aborts the run** if it crosses
`RUN_COST_CEILING_USD = 1.00`:

```python
if self.total_cost > self.ceiling:
    raise RuntimeError(f"Cost ceiling ${self.ceiling:.2f} exceeded ...")
```

The full run costs about **$0.03** — nowhere near the ceiling, which is the point:
the guard exists so that a bad loop cannot quietly become a bill, not because this
run was expensive. Per-call token counts and costs are recorded per letter, which
is what made the `gpt-4o` vs `gpt-4o-mini` comparison (17.2x per letter) possible
without a separate measurement pass.

## 4. Judge too strict or too lenient

**What the lab warns about:** add calibration examples, provide score anchors.

**What was done, and what it found.** The judge prompt ships explicit **score
anchors for all five points** (`evaluation_design.md`), which is the lab's
suggestion. That was not enough on its own, so `judge_calibration.py` tests it
directly: take one hand-written compliant letter, inject exactly one known defect
per variant, and map each variant to the anchor it should hit.

| variant | anchor | judge said | |
|---|---|---|---|
| clean | 5 | 5 | correct |
| ECOA notice removed | 3 | **5** | missed |
| unsupported reason added | 2 | 2 | correct |
| protected characteristic added | 1 | **3** | partly missed |

The judge was **neither too strict nor too lenient in general** — it is accurate on
reason fidelity and blind to an absent statutory element. That is a third
diagnosis the lab's two options do not cover, and it changes the fix: no amount of
calibration text repairs it, so regulatory completeness moved to the deterministic
checker instead.

## Two problems the lab does not warn about

**A compliance checker that fails everything looks identical to one that works.**
The first run had the rule checker rejecting 10 of 10 letters, which is exactly
what a broken checker would also produce. `test_rule_checker.py` settles it with a
**positive control** — a hand-written compliant letter that must pass all seven
elements — plus negative controls proving each element fails independently when
its supporting text is removed. 6/6 passing. Without that, the headline finding
would have been unpublishable.

**Temperature 0 is not determinism, and a seed did not fix it.** Across five runs
the letters varied every time, and which *secondary* elements got dropped varied
with them; only the ECOA omission held steady at 9–10 of 10. Adding `seed=7` to
the requests did not make the run reproduce exactly. The consequence is reported
rather than smoothed: the direction is the finding, individual counts are
indicative, and the only reproducible gate in the build is the deterministic
checker.
