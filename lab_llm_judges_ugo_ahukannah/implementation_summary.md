# Implementation Summary

**LAB | LLMs grading LLMs—with receipts** — Steps 7–11
**Author:** Nnanyelugo Ahukannah

**What I built.** A two-track evaluation pipeline in plain Python on the OpenAI
SDK. Track one generates an adverse-action letter for each of five test cases
(`eval_cases.py`) on each model under test, using a production-realistic system
prompt that names ECOA and FCRA and supplies the agency and credit-bureau contact
details — but deliberately does *not* enumerate the seven disclosure elements the
evaluation scores against, since handing the model the mark scheme would measure
nothing. Track two scores every letter twice: `rule_checker.py` runs deterministic
assertions for the seven elements, an unrecorded-reason scan, a
protected-characteristic scan that excludes the ECOA boilerplate paragraph (which
legitimately lists protected bases), exact counteroffer figures, and a locally
implemented Flesch–Kincaid grade; `llm_judge_evaluation.py` runs the Step 4 judge
prompt on `gpt-4o-mini` at temperature 0 in JSON mode, three times per letter, and
records every score, the judge's `unsupported_reasons` and `missing_elements`
arrays, latency, token counts and cost. A ledger aborts the run at a $1 ceiling.
The full run is 40 API calls, 99 seconds and $0.0313, written to
`evaluation_results.json`.

**Key findings.** Nine of ten letters failed the deterministic checker: the ECOA
anti-discrimination notice was absent from 9, the "the bureau did not make this
decision" statement from 5, the free-report and right-to-dispute notices from 1
each. One letter — `gpt-4o` on P3 — carried all seven elements, a 20% pass rate
against 0% for `gpt-4o-mini`. Across five runs of the suite the ECOA count ranged
9–10 of 10 and the secondary counts moved every time; pinning a request seed did
not make the run reproduce exactly, which is reported as a limitation rather than
smoothed over. Reason fidelity was clean 10 of
10 — neither model took the job-change bait in P2 or the maternity-leave bait in
P3. And the judge scored all ten letters 5.0/5 — the nine defective ones included
— with zero variance across three repeats: 100% agreement with the checker on
reason fidelity, **0–20% on regulatory completeness**, where the 20% is the one
letter that happened to be compliant rather than the judge detecting anything. `judge_calibration.py` was written to
separate "lenient judge" from "blind judge" by injecting one known defect at a
time into a hand-written compliant letter. The judge scored the clean letter 5
(anchor 5) and an unsupported reason 2 (anchor 2), both correct — but scored a
letter with the ECOA notice surgically removed 5 (anchor 3), and a protected
characteristic in the body 3 (anchor 1). It is not a rubber stamp; it is
specifically unable to notice an absent statutory element.

**What the two instruments proved about each other.** The most useful result was
not either verdict but their disagreement. The checker only catches baits it was
configured for per case, so in the calibration run — which used case P1, with no
baits defined — it missed both the injected unsupported reason and the injected
protected characteristic that the judge partially caught. The blind spots are
complementary: the judge reads meaning and misses absence, the checker detects
absence and reads no meaning. That is the actual recommendation to the client, and
it is only visible because both ran on the same letters. Before trusting the 0%
agreement figure I validated the checker itself — `test_rule_checker.py` (6/6
passing) includes a positive control proving a hand-written compliant letter
passes all seven elements, negative controls proving each element fails
independently when its text is removed, and a check that the protected-token scan
does not flag the compliant ECOA boilerplate. A compliance checker that fails
everything looks identical to a working one until something is supposed to pass.
