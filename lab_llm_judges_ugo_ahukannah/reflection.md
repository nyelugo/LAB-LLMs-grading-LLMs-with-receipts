# Reflection

**LAB | LLMs grading LLMs—with receipts** — Step 6
**Author:** Nnanyelugo Ahukannah

> *Note on length:* the brief asks for "2-3 paragraphs each" and "approximately
> 300-400 words total", which cannot both hold across three questions. I have
> favoured the paragraph structure and kept each answer to two.

---

## Q1 — What would change if the client's data was in French?

The layer that survives translation is the rule checker; the layer that does not
is the judge. Element E4 asks for a toll-free number and a bureau address, and a
regex does not care what language surrounds it — but the *element list itself*
would be replaced wholesale, because ECOA and FCRA are US statutes with no French
counterpart. A French lender's obligations come from the Code de la consommation
and, for automated decisions, GDPR Article 22 and its right to human review. So
the honest answer is that almost nothing transfers except the method: audit
benchmarks, discover the real element list from the client's compliance function,
encode it deterministically, and reserve the judge for what cannot be encoded.

Two new problems appear. First, benchmark scarcity: the audit found three
English-centric benchmarks and rejected all three; the French shortlist would be
shorter still, which strengthens the case for a custom evaluation rather than
weakening it. Second, my own competence becomes the bottleneck. I can read a
French letter well enough to be dangerous — well enough to think it reads
naturally, not well enough to notice that *vous* has slipped to a register that
sounds curt to a native reader. In this run the judge was the thing I could not
trust; in French, I am. The response is structural, not linguistic: native-speaker
reviewers own the tone criterion outright, and the calibration set gets labelled
by them before any judge score is quoted to the client.

---

## Q2 — Your client asks "is this model AGI-level?" — how do you respond?

I would say that the question has no measurable form, and then convert it into one
that does. "AGI-level" is not a property a benchmark reports, because it names
general competence across unbounded tasks, while every instrument I have measures
bounded performance on a specified task under specified conditions. The trap is
that the question sounds answerable — leaderboards publish single numbers next to
model names, and it is easy to point at a high MMLU score and imply something. The
benchmark audit in this lab is the argument against doing that: MMLU-style
leaderboard numbers are the most contaminated and most saturated evidence
available, and a model at the top of one still omitted a mandatory legal
disclosure in 10 out of 10 letters.

What I would offer instead is the operational question underneath: *can this
model be trusted to run this process without a person in the loop?* That one is
measurable, and we measured it — the answer for Cardinal Trust is no, with two
named defects and the specific gate each one requires. The caveat I would attach
is the one this run demonstrates rather than asserts: a model can be fluent,
accurate on the facts it was given, and superficially excellent while failing the
requirement that actually carries the liability. Generality is not the property
that matters here; verified behaviour on this task is, and it does not generalise
from anything else.

---

## Q3 — What is the one thing you could not evaluate without a human?

Tone in the register of bad news — prompt P4, where the applicant is trying to
pay a father's hospital bill. Everything else in this evaluation reduced to
something checkable. Whether the ECOA notice is present is a string test. Whether
a reason was invented is a comparison against a fixed record, and the judge
handled it correctly at 2/5. But whether a sentence reads as decent rather than
cold, or as kind rather than falsely hopeful, has no ground truth to compare
against — the target is an effect on a distressed reader, and the only instrument
that measures it is a reader.

The two automated methods fail for different reasons, and both matter. A rule can
be written for anything sayable in advance, and this failure is not: "we wish you
well in your circumstances" is warm in one letter and glib in another, decided
entirely by context a keyword never sees. An LLM judge fails for a subtler reason
— it can produce a plausible tone score, which is worse than producing none,
because there is no external check to catch it being wrong. This run showed
exactly that shape on the criterion where a check did exist: the judge asserted
regulatory completeness on 10 letters that lacked it, and only the checker
revealed it. On tone there is no checker. In practice I would sample 20 letters a
week to two of the bank's complaints reviewers, treat their inter-rater agreement
as the ceiling on any automated tone score, and let the judge screen volume — but
never let it be the last thing that reads a letter before a person receives it.
