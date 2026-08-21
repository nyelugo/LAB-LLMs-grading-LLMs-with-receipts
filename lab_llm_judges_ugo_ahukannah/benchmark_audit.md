# Benchmark Audit

**LAB | LLMs grading LLMs—with receipts** — Step 2
**Author:** Nnanyelugo Ahukannah

---

## Client scenario

**Cardinal Trust Bank**, a mid-size US regional lender, wants to automate the
adverse-action notices it sends to declined unsecured personal-loan applicants.
Today a credit officer hand-writes each letter from a structured decision record;
the bank sends roughly 4,000 a month and wants an LLM to draft them.

**Key requirements.** Each letter must (a) state *only* the principal reasons
recorded by the underwriting engine, (b) carry every disclosure the Equal Credit
Opportunity Act (Regulation B) and the Fair Credit Reporting Act require when a
consumer report was used, and (c) read as plain, respectful English to a
distressed reader.

**Main concerns / failure modes.** Hallucinated decline reasons that were never
in the decision record; a missing mandatory disclosure; language that references
a protected characteristic (age, marital status, receipt of public assistance);
and tone that is either cold boilerplate or falsely encouraging.

**Why the failure modes are asymmetric.** A dull letter is a customer-experience
problem. A fabricated reason or a dropped ECOA notice is a regulatory finding
with per-notice civil-penalty exposure. The evaluation has to weight those
differently, and no general-purpose leaderboard does.

---

## Benchmark Evaluation Card 1

**Benchmark Name:** IFEval (Instruction-Following Evaluation)
**Year:** 2023
**Source:** Zhou et al., *Instruction-Following Evaluation for Large Language Models*, arXiv:2311.07911 — https://arxiv.org/abs/2311.07911

**Why it seemed relevant:**
Cardinal Trust's compliance requirements are, mechanically, a list of verifiable
instructions: include this sentence, name this agency, stay under this length,
do not mention that. IFEval is built on exactly this idea — ~500 prompts carrying
~25 types of instruction that a Python function can check without a model or a
human in the loop. Of the three benchmarks audited, its *methodology* is the
closest match to what the bank actually needs verified.

**Contamination risk:**
- [ ] Low
- [x] **Medium** — Some overlap possible
- [ ] High

*Explanation:* The prompt set has been public on GitHub since late 2023 and IFEval
is a scored task on the Hugging Face Open LLM Leaderboard v2, so the items are
near-certain to appear in post-2024 pretraining corpora. The reason this is not
scored High is that IFEval grades *constraint satisfaction programmatically*
rather than comparing to a memorised gold answer — memorising the prompt does not
hand a model the check. Contamination inflates the headline number but does not
void the method.

**Saturation risk:**
- [ ] Low
- [ ] Medium
- [x] **High** — Many models achieve near-perfect scores

*Explanation:* Frontier and near-frontier instruction-tuned models cluster in the
high-80s to low-90s on strict prompt-level accuracy. Once a benchmark's spread
collapses to a few points, it stops discriminating between the two candidates we
actually have to choose between.

**Format:**
- [ ] Multiple Choice
- [x] **Free-form text** with programmatic constraint verification
- [ ] Code generation

**Verdict:**
- [ ] Use it as-is
- [x] **Adapt it**
- [ ] Reject it

*How:* Take the *verifiable-instruction* pattern, discard the item set. Cardinal
Trust's mandatory-disclosure elements become the constraint list, and a Python
checker asserts each one against the generated letter — the same
"score-without-a-judge" discipline, applied to the bank's own instructions. This
audit is the reason the implementation ships a deterministic rule checker
alongside the LLM judge rather than trusting the judge alone.

---

## Benchmark Evaluation Card 2

**Benchmark Name:** FinBen (successor to PIXIU / FLARE)
**Year:** 2024 (FLARE, 2023)
**Source:** Xie et al., *FinBen: A Holistic Financial Benchmark for Large Language Models*, arXiv:2402.12659 — https://arxiv.org/abs/2402.12659 (predecessor: arXiv:2306.05443)

**Why it seemed relevant:**
It is the most complete open financial-domain benchmark available — dozens of
datasets across quantitative reasoning, information extraction, sentiment and
risk tasks. If any public benchmark were going to tell us whether a model
"understands consumer lending", this would be it.

**Contamination risk:**
- [ ] Low
- [x] **Medium** — Some overlap possible
- [ ] High

*Explanation:* FinBen is an aggregation of pre-existing public datasets (FiQA,
FPB, Headlines, ConvFinQA and others), several of which predate the training
cutoff of every model under consideration by years. The aggregation is newer than
its parts, which is precisely the problem — a 2024 wrapper does not make 2018
data unseen.

**Saturation risk:**
- [ ] Low
- [x] **Medium** — Some models perform well
- [ ] High

*Explanation:* Aggregate scores still spread meaningfully across models, but the
spread is carried by the hard quantitative-reasoning subsets, not by anything
resembling regulated customer correspondence.

**Format:**
- [ ] Multiple Choice
- [x] **Mixed** — classification, extraction, numeric QA, some free-form
- [ ] Code generation

**Verdict:**
- [ ] Use it as-is
- [ ] Adapt it
- [x] **Reject it**

*Why:* Construct mismatch, which no amount of adaptation repairs. FinBen measures
whether a model can *read* financial text and answer questions about it. Cardinal
Trust needs to know whether a model can *write* a legally-constrained letter
without inventing facts. A high FinBen score is compatible with a model that
fabricates a decline reason in every third letter, because nothing in FinBen ever
asks it to abstain from adding content. Domain adjacency is not task relevance —
this card exists to record that the most obviously on-topic benchmark was the one
we threw out.

---

## Benchmark Evaluation Card 3

**Benchmark Name:** TruthfulQA
**Year:** 2021 (ACL 2022)
**Source:** Lin, Hilton & Evans, *TruthfulQA: Measuring How Models Mimic Human Falsehoods*, arXiv:2109.07958 — https://arxiv.org/abs/2109.07958

**Why it seemed relevant:**
The bank's single most expensive failure mode is a fabricated decline reason, and
TruthfulQA is the best-known public probe for a model asserting something untrue.
It was worth checking whether a general truthfulness score transfers to
groundedness against a supplied record.

**Contamination risk:**
- [ ] Low
- [ ] Medium
- [x] **High** — Model definitely saw this during training

*Explanation:* 817 fixed questions, public since 2021, and a headline metric on
the original Open LLM Leaderboard for years — which made it a direct optimisation
target. It was dropped from leaderboard v2. Any current score should be read as a
measurement of exposure at least as much as of truthfulness.

**Saturation risk:**
- [ ] Low
- [x] **Medium** — Some models perform well
- [ ] High

*Explanation:* Scores climbed steeply once it became a leaderboard target, though
the adversarial "imitative falsehood" design still catches some models. Medium
rather than High because the ceiling is not yet flat — but the climb is not clean
evidence of improved truthfulness.

**Format:**
- [x] **Both** — free-form generation (judged) and a multiple-choice variant
- [ ] Code generation

**Verdict:**
- [ ] Use it as-is
- [x] **Adapt it**
- [ ] Reject it

*How:* Borrow the *adversarial construction principle*, not the items. TruthfulQA
works by deliberately baiting a model with questions where a plausible-sounding
wrong answer is easy to reach. Applied here: build decline-letter test cases that
plant tempting-but-unrecorded material in the application file — a job change, a
medical hardship note — and check whether the model pulls it into the letter as a
reason. Test case P2 in the evaluation design is that adaptation.

There is also a construct gap worth naming. TruthfulQA measures truth against
*world knowledge*. Cardinal Trust needs *faithfulness to a supplied source* — a
letter citing a real-world-plausible reason that is absent from the decision
record is still a compliance failure. Those are different properties, and only
the second one matters here.

---

## What the audit changed

Three benchmarks, zero usable as-is. That is the finding, not a failure of the
search:

1. **No public benchmark scores the thing the bank is exposed on.** Two of the
   three are saturated or contaminated enough that their headline numbers are not
   evidence about *these* models; the third measures a different construct.
2. **The method survives even where the items do not.** IFEval's programmatic
   constraint checking and TruthfulQA's adversarial baiting both carry over —
   they are the backbone of the custom evaluation in `evaluation_design.md`.
3. **Faithfulness-to-source, not truthfulness, is the target property.** Naming
   that distinction is what stopped this evaluation from being a TruthfulQA
   re-run with a finance costume on.
