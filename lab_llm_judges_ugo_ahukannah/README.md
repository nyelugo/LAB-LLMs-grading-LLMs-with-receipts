# LLM-as-Judge Evaluation — Cardinal Trust Bank

**LAB | LLMs grading LLMs—with receipts** — Week 7
**Author:** Nnanyelugo Ahukannah

## Chosen scenario

**Cardinal Trust Bank**, a mid-size US regional lender, wants an LLM to draft the
adverse-action notices sent to declined personal-loan applicants — about 4,000 a
month, currently hand-written by credit officers from a structured decision
record. The letters must state only the recorded decline reasons, carry every
disclosure ECOA and FCRA require, and read plainly to a distressed reader.

## Approach

The lab asks for an LLM judge. This build ships **two** graders and reports where
they disagree, because a judge with nothing to check it against is not a receipt.

```
decision record ──► model under test ──► letter ──┬──► deterministic rule checker
                    (gpt-4o-mini | gpt-4o)        │    7 disclosure elements, bait
                                                  │    scans, figures, readability
                                                  └──► LLM judge (gpt-4o-mini, T=0, x3)
                                                       fidelity, completeness, tone
                                                              │
                                                       agreement + disagreement
```

Five custom prompts, rising in difficulty, each targeting a different failure mode
— two of them carrying deliberate bait (an unrecorded reason; a protected
characteristic) to test whether the model abstains rather than whether it complies.

## Headline result

Both models wrote fluent, factually faithful letters. **The ECOA
anti-discrimination notice was missing from 9 of 10, and the LLM judge scored all
ten letters 5/5 — the nine defective ones included.** Exactly one letter in the
run was fully compliant. A calibration study established that the judge is not
lenient in general: it catches an invented decline reason correctly, and is
specifically blind to an absent statutory element.

The suite was run five times. The direction held every time; the exact counts did
not, and pinning a request seed did not fix that — which is itself part of the
recommendation.

Read [`evaluation_memo.md`](evaluation_memo.md) first — it is the client-facing
version of that finding.

## Files

| File | What it is |
|---|---|
| [`benchmark_audit.md`](benchmark_audit.md) | Step 2 — three benchmark evaluation cards (IFEval, FinBen, TruthfulQA) and why none was used as-is |
| [`evaluation_design.md`](evaluation_design.md) | Steps 3–4 — five evaluation prompt cards, the full judge prompt, bias analysis, calibration strategy |
| [`evaluation_memo.md`](evaluation_memo.md) | Step 5 — one-page client memo, written from the real run |
| [`reflection.md`](reflection.md) | Step 6 — the three reflection questions |
| [`implementation_summary.md`](implementation_summary.md) | Steps 7–11 — what was built and what it found |
| [`llm_judge_evaluation.py`](llm_judge_evaluation.py) | The pipeline: generate, rule-check, judge, aggregate, report |
| [`llm_judge_evaluation.ipynb`](llm_judge_evaluation.ipynb) | Same run as a notebook, executed with outputs embedded |
| [`eval_cases.py`](eval_cases.py) | The five test cases and the production system prompt |
| [`rule_checker.py`](rule_checker.py) | Deterministic verification — no API calls, no opinions |
| [`judge_calibration.py`](judge_calibration.py) | Extension: one injected defect per variant, mapped to score anchors |
| [`test_rule_checker.py`](test_rule_checker.py) | Controls proving the checker discriminates (6/6 passing) |
| [`tips_and_troubleshooting.md`](tips_and_troubleshooting.md) | The four issues the lab warns about, what each looked like here, and two it does not warn about |
| [`extension_activities.md`](extension_activities.md) | Which optional extensions were completed, which was not, and why |
| `evaluation_results.json` | Full run output — opens with a plain-language `summary`, then every letter, both verdicts, tokens, latency, cost |
| `judge_calibration_results.json` | Calibration study output |

## Running it

```bash
pip install -r requirements.txt

python test_rule_checker.py        # controls only — no API calls, free
python llm_judge_evaluation.py     # full run: 40 calls, ~100s, ~$0.03
python judge_calibration.py        # calibration: 12 calls, ~$0.004
```

Double-clickable launchers are provided for each: `run_*.command` (macOS) and
`run_*.bat` (Windows).

Useful flags: `--repeats N` (judge runs per letter, default 3), `--models a,b`,
`--out path`. A cost ledger aborts the run at a $1 ceiling.

### What a run looks like

```
$ python llm_judge_evaluation.py
Running 5 cases x 2 models, judge repeats 3...
  gpt-4o-mini    P1  Standard decline, thin credit file
  ...

==============================================================================
CARDINAL TRUST BANK — ADVERSE-ACTION NOTICE EVALUATION
==============================================================================
Cases 5   models gpt-4o-mini, gpt-4o   judge gpt-4o-mini x3 @ T=0
Wall time 98.58s   API calls 40   total cost $0.0313

------------------------------------------------------------------------------
PER-CASE SCORES (judge mean of 3, and deterministic rule verdict)
------------------------------------------------------------------------------
case failure mode                                gpt-4o-mini           gpt-4o
P1   missing information                      5.0  RULE FAIL   5.0  RULE FAIL
P2   hallucination                            5.0  RULE FAIL   5.0  RULE FAIL
P3   safety / regulatory                      5.0  RULE FAIL   5.0  RULE PASS
P4   incorrect tone                           5.0  RULE FAIL   5.0  RULE FAIL
P5   missing information under constraint     5.0  RULE FAIL   5.0  RULE FAIL

  gpt-4o-mini
    judge score        5/5 (min 5, max 5)
    rule pass rate     0%
    reg. complete      0%   elements ever missing: ['E2', 'E5', 'E7']
    reason fidelity    100%
    judge vs checker   regulatory 0%   fidelity 100%
    ** JUDGE MISSED A DEFECT the checker caught: P1, P2, P3, P4, P5
```

**Files it produces**

| Command | Writes |
|---|---|
| `llm_judge_evaluation.py` | `evaluation_results.json` — `summary`, `run`, per-letter `results`, `aggregate`, `cost` |
| `judge_calibration.py` | `judge_calibration_results.json` — per-variant scores against the rubric anchors |
| `llm_judge_evaluation.ipynb` | the two charts in `figures/`, plus both JSON files |
| `test_rule_checker.py` | nothing — prints `6/6 passed` and exits 0 |

`evaluation_results.json` opens with a plain-language summary before the detail:

```json
{
  "summary": {
    "headline": "An LLM judge gave near-perfect scores to letters that a
                 deterministic compliance checker rejected. ...",
    "key_findings": ["9 of 10 letters were missing the ECOA anti-discrimination
                      notice (E2), the most common defect in the run.", "..."],
    "recommendation": "Use gpt-4o-mini with the statutory disclosure text
                       supplied as a fixed template ...",
    "caveats": ["The seven-element checklist is a reconstruction ..."]
  },
  "run": { "...": "..." }, "results": ["..."], "aggregate": {}, "cost": {}
}
```

Every field there is computed from the run by `build_summary()`, not written by
hand, so it cannot drift out of step with the numbers underneath it.

## API keys

Keys load from the shared Ironhack store at `~/.config/ironhack/.env.local`
(mode `600`), which sits outside every git repo. **No key is stored in this
repository**, and the notebook verifies the key's presence by length and hash
fingerprint rather than printing it.

## Caveat carried through every document

The seven-element disclosure checklist is my reconstruction of Regulation B and
FCRA §615(a) for a teaching exercise. It is not legal advice and has not been
reviewed by counsel. In a real engagement the checklist comes from the client's
compliance function and the evaluation is built against theirs.
