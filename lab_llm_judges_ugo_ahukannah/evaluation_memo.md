# Evaluation Memo

**LAB | LLMs grading LLMs—with receipts** — Step 5
**Author:** Nnanyelugo Ahukannah

---

**TO:** Alice Nwosu, Head of Consumer Lending Operations — Cardinal Trust Bank
**FROM:** Nnanyelugo Ahukannah
**DATE:** 21 August 2026
**SUBJECT:** LLM Evaluation Results — Automated Adverse-Action Notices

---

## EXECUTIVE SUMMARY

We tested whether an LLM can draft your personal-loan decline letters, across five
cases built around your four stated failure modes. Both candidate models write
fluent, accurate letters, and **9 of the 10 were missing the ECOA
anti-discrimination notice — one letter in the run was fully compliant.** The
finding that should change your plan is its companion: an LLM judge scored all ten
5/5, the nine defective ones included.

## METHODOLOGY

We audited three public benchmarks (IFEval, FinBen, TruthfulQA) and used none
as-is: two are saturated or contaminated enough that their scores are not evidence
about these models, and the third measures financial reading comprehension, not
constrained writing. We kept their methods and built five custom prompts — a
baseline decline, one baiting an unrecorded reason, one baiting a protected
characteristic, a distressed applicant, and a counteroffer under a readability
constraint.

Every letter was scored twice. A deterministic Python checker verifies the seven
mandatory disclosure elements, the counteroffer figures and reading grade, with no
model involved. An LLM judge (`gpt-4o-mini`, temperature 0, three repeats) scores
reason fidelity, regulatory completeness and tone. Models tested: `gpt-4o-mini`
and `gpt-4o`. Ten letters, 40 API calls, 99 seconds, $0.03.

## RESULTS

**Nine of ten letters failed the checker.** The ECOA notice was absent from 9; the
"the bureau did not make this decision" statement from 5; the free-report notice
and the right-to-dispute notice from 1 each. Exactly one letter carried all seven
elements — `gpt-4o` on the protected-characteristic case — a 20% pass rate for
that model against 0% for `gpt-4o-mini`. The models are not careless; they omit
what our production prompt did not name. Reason fidelity was clean 10 of 10:
neither took the job-change or maternity-leave bait, the failure we most
expected.

**The judge agreed with the checker 100% on fidelity and 0–20% on regulatory
completeness** — and that 20% is an artefact of the one letter that happened to be
compliant, not of the judge noticing anything. A calibration study injecting one known defect at a time explains
why: the judge correctly dropped an unsupported reason to 2/5, but scored a letter
with the ECOA notice surgically removed 5/5. It is not lenient across the board —
it is specifically blind to a missing statutory element. Scores showed zero
variance across three repeats, so this is stable bias, not noise.

## CAVEATS & LIMITATIONS

Five prompts on one product is a probe, not an assurance. The checker confirms the
elements are present; it cannot confirm the list is right. **That list is my
reconstruction of Reg B and FCRA §615(a) and has not been reviewed by counsel** —
replace it with your compliance function's before relying on any number here. The
judge shares a model family with one candidate, so its tone scores are not
independent, and tone was never validated against human reviewers. One further
caveat on reproducibility, which we can evidence rather than assert: we ran this
suite five times, and at temperature 0 the letters varied every time. The ECOA
omission ranged between 9 and 10 of 10, and the secondary counts moved more than
that. We then pinned a request seed, and the run still did not reproduce exactly.
Treat the direction as the finding and each individual count as indicative. If you
need a reproducible acceptance gate, it has to be the deterministic checker — no
sampled model output will give you one.

## RECOMMENDATION

**Under these conditions, for this task: `gpt-4o-mini`, with the disclosure text
supplied as fixed template rather than generated.** The models were
indistinguishable on fidelity, tone and judge score, and `gpt-4o` costs 17.2× more
per letter. It did produce the run's single compliant letter — one case out of
five, on a suite whose counts move between runs, which is not evidence of anything
and should not be priced as if it were. Confidence is high on cost and fidelity,
moderate on tone, and low that either model is safe unsupervised — both defects
we found are ones a fluent letter hides. Do not ship a judge-only gate.

## ADDITIONAL METRICS

Generation costs $0.000250/letter on `gpt-4o-mini` against $0.004310 on `gpt-4o` —
at 4,000 letters a month, **$1.00 versus $17.24**. Latency was 3.37s and 4.39s
respectively, but the ordering flipped between runs, so treat latency as
indistinguishable at this sample size rather than as an argument for either
model.
Judging cost $0.0085 for 30 judgements, 27% of the run; the deterministic checker
costs nothing per letter and runs in milliseconds, which is the argument for
putting it in front of the judge rather than behind it. Against a credit officer's
time, the model spend is a rounding error — the decision rests on the review
design, not the token bill.
