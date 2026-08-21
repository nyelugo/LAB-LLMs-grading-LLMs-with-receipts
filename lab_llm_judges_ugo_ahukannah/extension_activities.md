# Extension Activities

**LAB | LLMs grading LLMs—with receipts**
**Author:** Nnanyelugo Ahukannah

The lab lists four optional extensions. Two are complete, one is partially
complete, and one was not done — recorded honestly rather than claimed.

## 1. Compare two models — **done**

Both `gpt-4o-mini` and `gpt-4o` generate a letter for all five test cases, and
every letter is scored by the same judge and the same deterministic checker, so
the comparison is like-for-like.

| | judge score | rule pass | reason fidelity | $/letter | $/month @ 4,000 |
|---|---|---|---|---|---|
| `gpt-4o-mini` | 5.0/5 | 0/5 | 5/5 | $0.000250 | $1.00 |
| `gpt-4o` | 5.0/5 | 1/5 | 5/5 | $0.004310 | $17.24 |

The models were indistinguishable on every quality measure computable here, and
`gpt-4o` costs **17.2x** more per letter. It produced the run's single compliant
letter — one case out of five, on a suite whose counts move between runs, which is
not evidence and is not priced as if it were. Run it with
`python llm_judge_evaluation.py --models gpt-4o-mini,gpt-4o`.

## 2. Calibration study — **done**, and it carried the lab

`judge_calibration.py`. The main run left two explanations open — a *lenient*
judge or a *blind* one — which need different fixes, so they had to be separated.
Method: one hand-written compliant letter, exactly one known defect injected per
variant, each mapped to a rubric score anchor.

| variant | anchor | judge score | verdict |
|---|---|---|---|
| clean | 5 | 5 | correct |
| ECOA notice removed | 3 | **5** | missed |
| unsupported reason added | 2 | 2 | correct |
| protected characteristic in body | 1 | **3** | partly missed |

**The judge is not a rubber stamp** — it catches an invented decline reason
exactly right. It is specifically unable to see that a required element is
*absent*. The deterministic checker has the opposite blind spot: it detects
absence and reads no meaning. That complementarity is the recommendation in the
client memo, and it is only visible because both graders ran on the same letters.

The lab suggests calibrating on "10 examples with known quality levels". This uses
4 variants with a *single* injected defect each, which is a deliberate change:
one defect per variant is what makes the failure attributable to a specific
criterion. Ten mixed-quality examples would have shown the judge scoring poorly
without showing *which* criterion it was failing on.

## 3. Cost optimization — **done**

Per-call token counts and costs are recorded for every generation and every
judgement, priced from a stated list-price table rather than guessed, and rolled
up per model. Judging cost $0.0085 of the run's $0.0313 — **27%** — which is the
argument for putting the free deterministic checker *in front of* the judge rather
than behind it: it catches the dominant defect at zero marginal cost, and the
judge only ever sees what survives.

The lab suggests comparing `gpt-3.5-turbo` against `gpt-4o-mini` for the judge.
Not run: the calibration study showed the limitation is the judge's blindness to
an absent element, and a weaker judge model cannot improve on that. Testing a
*stronger* judge would be the informative experiment, and it is listed below.

## 4. Human evaluation — **not done**

The lab suggests having a classmate score 2–3 examples and comparing. This was not
done, and the gap is real rather than cosmetic: **tone is the one criterion in
this evaluation with no ground truth and no deterministic check**, so it is the
one place a human is not optional. `evaluation_design.md` sets out the intended
design — 20 letters labelled by two of the bank's compliance reviewers, with their
inter-rater agreement treated as the ceiling on any automated tone score — but no
human labels were collected, so every tone number here rests on the judge alone
and is reported as unvalidated.

## Beyond the lab's list

Three things were built that the extensions do not ask for, because the finding
demanded them:

- **A deterministic rule checker** (`rule_checker.py`) alongside the judge. The
  lab asks only for an LLM judge; without a second grader there is no way to know
  the judge is wrong, and the entire finding disappears.
- **Controls for the checker** (`test_rule_checker.py`, 6/6). A positive control
  proving a compliant letter passes all seven elements — a checker that rejects
  everything is indistinguishable from a working one until something is supposed
  to pass.
- **A reproducibility probe.** Five full runs plus a pinned request seed,
  establishing that temperature 0 does not make this suite reproduce, which is
  reported as a limitation instead of being averaged away.

## What I would do next

1. **Re-run the calibration study with `gpt-4o` as the judge.** It answers whether
   completeness blindness is a model limit or a prompt limit — roughly 20 minutes
   and a few cents, and it is the first question a reviewer would ask.
2. **Collect the human tone labels.** The honest gap above.
3. **Template the disclosures and re-measure.** The recommendation is to supply
   E2–E7 as fixed text; showing the checker go from 1/10 to 10/10 would close the
   loop and turn a recommendation into a demonstrated fix.
