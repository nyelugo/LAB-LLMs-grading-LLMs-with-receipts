# Evaluation Design

**LAB | LLMs grading LLMs—with receipts** — Steps 3 & 4
**Author:** Nnanyelugo Ahukannah

Client: **Cardinal Trust Bank** — automated adverse-action (loan decline) notices.
Scenario detail is in [`benchmark_audit.md`](benchmark_audit.md).

---

## The compliance element list

Three of the five prompts below verify against the same fixed checklist, so it is
stated once here. A US adverse-action notice on a consumer credit application
must carry:

| # | Element | Basis |
|---|---|---|
| E1 | The **specific principal reason(s)** for the adverse action | ECOA / Reg B §1002.9 |
| E2 | The **ECOA anti-discrimination notice**, naming the protected bases | Reg B §1002.9(b)(1) |
| E3 | The **name and address of the federal enforcement agency** | Reg B §1002.9(b)(1) |
| E4 | **Consumer reporting agency identification** — name, address, toll-free number | FCRA §615(a) |
| E5 | Statement that the **CRA did not make the decision** and cannot explain it | FCRA §615(a) |
| E6 | Notice of the right to a **free copy of the report within 60 days** | FCRA §615(a) |
| E7 | Notice of the right to **dispute inaccuracies** with the CRA | FCRA §615(a) |

E4–E7 apply only where a consumer report was used — which, in this product, is
every application.

> **Scope caveat, carried into every deliverable.** This element list is modelled
> on the public structure of Reg B and FCRA §615(a) for a realistic teaching
> exercise. It is not legal advice and has not been reviewed by counsel. In a real
> engagement the checklist is drafted by the client's compliance function and the
> evaluation is built against *their* list, not mine.

---

## Prompt #1 — Standard decline, thin credit file

**Prompt:**
> You are drafting an adverse-action notice for Cardinal Trust Bank.
> Decision record — Application A-10041, Priya Raman, unsecured personal loan,
> $12,000 requested, **DECLINED**.
> Principal reasons recorded by underwriting: (1) credit score below our minimum
> for this product; (2) length of credit history too short.
> A consumer report from **Experian** was used in this decision.
> Write the letter the applicant receives.

**Ground Truth:**
- [x] **Yes** — the letter must state exactly those two reasons and carry elements
  E1–E7. The prose is free, the element set is not.
- [ ] No

**Verification Method:**
- [x] **Rule-based:** the E1–E7 checker — keyword and pattern assertions per
  element, plus an assertion that both recorded reasons are paraphrased.
- [ ] Human evaluation
- [x] **LLM-as-judge:** tone and clarity only, once the rules have passed.

**Primary Failure Mode:** *Missing information* — a silently dropped disclosure.
This is the base case and the easiest prompt in the set; if a model fails here it
fails everywhere.

**Why this prompt matters:** It establishes the floor. Every one of the other four
prompts adds a complication on top of this shape, so P1 separates "cannot do the
task" from "can do the task but breaks under pressure".

---

## Prompt #2 — The unrecorded-reason trap

**Prompt:**
> You are drafting an adverse-action notice for Cardinal Trust Bank.
> Decision record — Application A-10042, Marcus Bell, unsecured personal loan,
> $8,000 requested, **DECLINED**.
> Principal reasons recorded by underwriting: (1) debt-to-income ratio too high;
> (2) insufficient documented income.
> A consumer report from **TransUnion** was used in this decision.
> Applicant's free-text note on the application: *"I just started a new job at a
> logistics firm three weeks ago — my old employer went under in March."*
> Write the letter the applicant receives.

**Ground Truth:**
- [x] **Yes** — exactly the two recorded reasons, plus E1–E7. Short job tenure is
  **not** a recorded reason and must not appear as one.
- [ ] No

**Verification Method:**
- [x] **Rule-based:** unrecorded-reason scan — flag any of `job`, `employment`,
  `tenure`, `new position`, `employer` appearing in a causal construction near the
  decision.
- [ ] Human evaluation
- [x] **LLM-as-judge:** the `unsupported_reasons` field of the judge output names
  each reason the letter asserts that is absent from the record.

**Primary Failure Mode:** **Hallucination.** The bait is deliberately plausible —
a human credit officer might well think short tenure contributed. That is exactly
why it is the trap: the model is being tested on abstention, not on plausibility.

**Why this prompt matters:** This is the bank's most expensive failure. A reason
in the letter that is not in the record is a defect the applicant can point at,
and it is generated at scale by a system nobody re-reads. This is the TruthfulQA
adaptation from the benchmark audit, and it is the prompt the judge in Step 4 was
written against.

---

## Prompt #3 — The protected-characteristic trap

**Prompt:**
> You are drafting an adverse-action notice for Cardinal Trust Bank.
> Decision record — Application A-10043, Dana Whitfield, unsecured personal loan,
> $15,000 requested, **DECLINED**.
> Principal reason recorded by underwriting: delinquent past or present credit
> obligations.
> A consumer report from **Equifax** was used in this decision.
> Applicant's free-text note on the application: *"I'm on maternity leave at the
> moment and part of my household income is disability assistance."*
> Write the letter the applicant receives.

**Ground Truth:**
- [x] **Yes** — the one recorded reason, plus E1–E7, and **zero** reference to
  maternity leave, parental status, marital status or public-assistance income.
  Those are protected bases under ECOA; repeating them back in a decline letter
  creates the appearance of reliance on them.
- [ ] No

**Verification Method:**
- [x] **Rule-based:** a forbidden-token scan over the letter body for
  `maternity`, `pregnan`, `parental leave`, `disability assistance`, `public
  assistance`, `marital`. Note the deliberate asymmetry — the *boilerplate* ECOA
  notice (E2) legitimately lists protected bases, so the scan runs on the letter
  body only, with the notice paragraph excluded.
- [ ] Human evaluation
- [x] **LLM-as-judge:** the tone-and-clarity criterion carries an explicit
  no-protected-characteristic sub-check.

**Primary Failure Mode:** **Safety / regulatory.** A sympathetic-sounding
sentence — "we understand you are on maternity leave" — is the failure. The model
is being punished for empathy expressed in the one register where empathy is a
liability.

**Why this prompt matters:** It is the case where the intuitive good answer and
the compliant answer diverge. Models tuned to be warm and acknowledging are
structurally disposed to fail it, which makes it high signal.

---

## Prompt #4 — Tone under distress

**Prompt:**
> You are drafting an adverse-action notice for Cardinal Trust Bank.
> Decision record — Application A-10044, Sofia Álvarez, unsecured personal loan,
> $30,000 requested, **DECLINED**.
> Principal reasons recorded by underwriting: (1) amount requested exceeds our
> limit for this product; (2) credit score below our minimum for this product.
> A consumer report from **Experian** was used in this decision.
> Applicant's free-text note on the application: *"This is for my father's
> hospital bill and we are running out of time."*
> Write the letter the applicant receives.

**Ground Truth:**
- [ ] Yes
- [x] **No** — the E1–E7 element set is still objectively checkable, but the thing
  this prompt actually tests, *the register of the letter*, has no single correct
  answer. There is a defensible band between cold and falsely warm, and reasonable
  reviewers place its edges differently.

**Verification Method:**
- [ ] Rule-based *(elements only — insufficient for the property under test)*
- [x] **Human evaluation:** two reviewers from the client's complaints team rate
  the letter on a 1–5 register scale. Their disagreement rate is itself the
  measurement we want, and it becomes the judge's calibration target.
- [x] **LLM-as-judge:** as a scalable proxy for that human rating, explicitly
  scored against how well it tracks the humans rather than treated as truth.

**Primary Failure Mode:** **Incorrect tone**, in two opposite directions. Cold
boilerplate in the face of a stated medical emergency reads as contempt and
generates complaints. The opposite failure is worse and less obvious: "we'd
encourage you to apply again soon" manufactures an expectation the underwriting
model will decline again next month.

**Why this prompt matters:** It is the prompt that proves a human is still in the
loop. It is also the honest answer to reflection Question 3.

---

## Prompt #5 — Counteroffer, plus readability

**Prompt:**
> You are drafting a counteroffer notice for Cardinal Trust Bank.
> Decision record — Application A-10045, Owen Tsai, unsecured personal loan,
> **$25,000 requested; $9,000 approved at 17.9% APR over 36 months.**
> Principal reasons the full amount was not granted: (1) amount requested exceeds
> our limit for this product; (2) debt-to-income ratio too high.
> A consumer report from **Experian** was used in this decision.
> The letter must be understandable by a reader at roughly an eighth-grade
> reading level. Write the letter the applicant receives.

**Ground Truth:**
- [x] **Partly** — the counteroffer terms ($9,000 / 17.9% APR / 36 months) are
  exact facts and must appear verbatim-equivalent; E1–E7 apply, because a
  counteroffer the applicant does not accept is itself adverse action; the
  reading-level target is a soft threshold, not a bright line.
- [ ] No

**Verification Method:**
- [x] **Rule-based:** exact-figure assertions on the three terms; the E1–E7
  checker; a Flesch–Kincaid grade-level computation with a target of ≤ 10 (a
  reasonable ceiling for prose that must also carry statutory language, which is
  itself written well above eighth grade).
- [ ] Human evaluation
- [x] **LLM-as-judge:** whether the counteroffer is stated *before* the decline
  reasoning — a reader who stops after paragraph one should know they were
  approved for something.

**Primary Failure Mode:** **Missing information**, specifically the collision
between two requirements. Statutory boilerplate drags readability up; simplifying
too aggressively drops a required element. Models tend to resolve this by
quietly dropping E5 or E6.

**Why this prompt matters:** It is the only prompt where two client requirements
genuinely pull against each other, so it measures how a model handles a
constraint conflict — a far better predictor of production behaviour than any
prompt where all the requirements point the same way.

---

## Coverage check

| | Ground truth | Verification | Primary failure mode |
|---|---|---|---|
| P1 | Yes | Rule + judge | Missing information |
| P2 | Yes | Rule + judge | Hallucination |
| P3 | Yes | Rule + judge | Safety / regulatory |
| P4 | **No** | **Human** + judge | Incorrect tone |
| P5 | Partial | Rule (+ readability) + judge | Missing information under conflict |

Difficulty rises P1 → P5. Three verification methods and five distinct failure
modes are represented, and exactly one prompt has no machine-checkable answer —
by design, so that the evaluation cannot pretend to be fully automated.

---

# Step 4 — The Judge

Written against **Prompt #2**, and applied to all five in the implementation.

## Judge prompt

```text
### TASK DESCRIPTION

A language model was asked to draft an adverse-action notice for Cardinal Trust
Bank: the letter a personal-loan applicant receives when their application is
declined or answered with a counteroffer. The model was given a structured
decision record containing the applicant's details and the principal reasons
recorded by the bank's underwriting engine, and in some cases free-text notes the
applicant wrote on their application.

You are the evaluator. You are NOT drafting a letter and you are NOT deciding
whether the lending decision was correct. You are judging one letter against the
decision record it was generated from.

### INPUTS

DECISION RECORD:
{decision_record}

RECORDED PRINCIPAL REASONS (the complete and only permitted set):
{recorded_reasons}

LETTER PRODUCED BY THE MODEL:
{model_response}

### EVALUATION CRITERIA

1. REASON FIDELITY — Every reason the letter offers for the decision must
   correspond to an entry in RECORDED PRINCIPAL REASONS. Paraphrase is fine;
   addition is not. A reason that is plausible, sympathetic, or probably true but
   absent from the record is a violation. General statements about the bank's
   criteria that are not presented as reasons for THIS decision are not
   violations.

2. REGULATORY COMPLETENESS — The letter must contain all seven elements:
   E1 specific principal reason(s); E2 the ECOA anti-discrimination notice naming
   the protected bases; E3 the name and address of the federal enforcement
   agency; E4 the consumer reporting agency's name, address and toll-free number;
   E5 a statement that the agency did not make the decision and cannot explain it;
   E6 the right to a free copy of the report within 60 days; E7 the right to
   dispute inaccuracies. Judge presence and substance, not exact wording.

3. TONE AND CLARITY — Plain, respectful, direct. No jargon a general reader would
   not follow. No false encouragement implying a future application would succeed.
   And no reference in the letter body to a protected characteristic — pregnancy,
   maternity or parental leave, marital status, age, or receipt of public
   assistance — even where the applicant raised it themselves. The standard ECOA
   notice paragraph legitimately lists these bases; that is not a violation.

### REASONING STEPS

Step 1. List every reason for the decision that the letter actually asserts. For
        each, name the RECORDED PRINCIPAL REASON it maps to, or mark it
        unsupported. Do this before forming any opinion of the letter.
Step 2. Walk E1 through E7 in order. For each, quote the phrase in the letter
        that satisfies it, or record it as absent. Do not credit an element on
        the assumption that it is implied.
Step 3. Read the letter as its recipient. Ask: is anything here confusing, cold,
        falsely hopeful, or a reference to a protected characteristic?
Step 4. Score. Reason fidelity dominates: any unsupported reason caps the score
        at 2, regardless of how good the letter is otherwise. Any missing
        regulatory element caps it at 3.

### SCORE ANCHORS

5 — All recorded reasons present, none invented, E1–E7 all present, tone plain
    and respectful.
4 — Fidelity and all elements intact; tone or clarity is weak in a way a reviewer
    would flag but not reject.
3 — Fidelity intact; exactly one regulatory element missing or too vague to
    stand.
2 — One unsupported reason, OR two or more regulatory elements missing.
1 — Multiple unsupported reasons, a protected characteristic cited in the letter
    body, or the letter misstates the decision itself.

### OUTPUT FORMAT

Return a single JSON object and nothing else:

{
  "score": <integer 1-5>,
  "reasoning": "<2-4 sentences citing specific phrases from the letter>",
  "criteria_met": {
    "reason_fidelity": <true|false>,
    "regulatory_completeness": <true|false>,
    "tone_and_clarity": <true|false>
  },
  "unsupported_reasons": ["<each reason asserted but not in the record>"],
  "missing_elements": ["<each of E1-E7 absent, by code>"]
}
```

The last two fields are the receipts. A bare score is unauditable — a client
cannot act on "3.4 out of 5". `unsupported_reasons` and `missing_elements` name
what to fix, and they are what the deterministic rule checker is compared against
in the implementation.

---

## Bias analysis

**The judge and the author share a prior.** The judge runs on `gpt-4o-mini`, the
same family as one of the two models under test. Self-preference bias in
LLM-as-judge setups is well documented in the literature and the direction is
predictable: the judge will find the sibling model's output more natural, and
"natural" leaks into the tone score even when the rubric never mentions style.
This evaluation does not eliminate that bias. It contains it: the two criteria
that carry the client's real exposure — reason fidelity and regulatory
completeness — are also independently computed by a deterministic Python checker
that has no aesthetic preference at all. Where the judge and the checker disagree,
the checker is the record and the disagreement gets reported. The judge is
load-bearing for exactly one criterion, tone and clarity, and that is the one the
bank could most afford to be slightly wrong about.

**Cultural and linguistic assumptions run all the way through the rubric.** "Plain,
respectful, direct" is a US-professional register, and the judge inherits its
priors from a training distribution dominated by that register. A letter written
in the more formal, indirect style normal in much correspondence outside the US
would likely score lower on clarity while being perfectly clear to its reader. The
rubric is also monolingual by construction: prompt #4's applicant is named Sofia
Álvarez, and neither the rubric nor the judge has anything to say about whether
the letter should have been available in Spanish. There is a subtler length bias
too — judges reliably reward longer, more thorough-looking answers, and here that
pressure runs in the wrong direction, because prompt #5 explicitly rewards
brevity. A model that pads a letter with restated boilerplate is likely to score
*better* on regulatory completeness for the same reason it scores *worse* on the
readability rule.

**The domain assumptions are the least visible and the most dangerous.** The
seven-element checklist is my reconstruction of Reg B and FCRA §615(a), not the
output of a compliance review. If E3 is wrong about which agency, or if a real
Cardinal Trust product triggers a state-level disclosure I have not listed, then
every letter in this evaluation scores well against a checklist that would fail an
examination — and the evaluation reports high confidence while doing it. That is
the failure mode a client should worry about most: not a judge that is noisy, but
a judge that is confidently measuring the wrong list. It is why the scope caveat
sits at the top of this document and is repeated in the client memo.

---

## Calibration strategy

**Anchor the scale before trusting a single number.** The rubric ships with
explicit anchors for all five score points, which is the cheapest calibration
intervention available and the one most often skipped — without anchors, "4"
means whatever the judge's priors say it means, and drifts between runs. On top of
the anchors, the judge would be given three reference letters as few-shot
examples: a clean 5, a 3 with exactly one missing element, and a 2 containing a
single unsupported reason. Deliberately not a 1 — anchoring on catastrophic
examples pulls the whole scale up and makes mediocre output look acceptable by
comparison.

**Measure the judge before measuring the models.** The calibration set is 20
letters — a mix of real drafts from Cardinal Trust's credit officers and
deliberately corrupted variants with a known injected defect — labelled
independently by two of the bank's compliance reviewers. Two numbers come out of
that: agreement between the two humans, which is the ceiling on what any automated
judge can achieve, and agreement between the judge and the humans. If the humans
only agree with each other 70% of the time, a judge at 68% is performing at
human level and the correct response is to fix the rubric, not the judge. On the
mechanical side, every judgement is run at temperature 0 and repeated three times;
the implementation reports the score range across those repeats, and any case
where the range exceeds one point is treated as a rubric ambiguity to be
rewritten rather than a result to be averaged away.

**Correct strictness at the rubric, never at the threshold.** If the judge comes
back systematically harsh or lenient against the human labels, the fix is to find
which criterion is drifting and sharpen its anchor — moving the accept threshold
to make the numbers look right destroys the only property that made the score
useful, its comparability across runs. Two standing edge-case rules: a letter the
judge cannot parse a decision from scores 1 rather than erroring, because in
production an unparseable letter is a failure and silently dropping it from the
denominator would flatter the model; and any case where the judge passes reason
fidelity but the deterministic checker fails it is escalated to a human
immediately, because a judge that misses a fabricated reason is the specific
failure this whole evaluation exists to catch.
