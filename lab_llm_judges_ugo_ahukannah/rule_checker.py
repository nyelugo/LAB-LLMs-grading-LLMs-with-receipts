"""Deterministic verification of an adverse-action notice.

This is the IFEval adaptation from ``benchmark_audit.md``: the seven mandatory
disclosure elements are expressed as programmatic assertions, so the two things
the client is legally exposed on are scored without asking a model's opinion.

Nothing here calls an API. It is the control the LLM judge is measured against.

Author: Nnanyelugo Ahukannah
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------
# The seven elements (see evaluation_design.md for statutory basis).
# Each is a predicate over the lower-cased letter.
# --------------------------------------------------------------------------

PROTECTED_BASES = [
    "race", "color", "colour", "religion", "national origin", "sex",
    "marital status", "age", "public assistance",
]

TOLL_FREE = re.compile(r"\b1[\s.\-]?\(?8\d{2}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}\b")


def _has_all(text: str, terms: list[str]) -> bool:
    return all(t in text for t in terms)


def _has_any(text: str, terms: list[str]) -> bool:
    return any(t in text for t in terms)


def _split_paragraphs(letter: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", letter) if p.strip()]


def _body_excluding_ecoa_notice(letter: str) -> str:
    """Letter body with the boilerplate ECOA notice paragraph removed.

    The standard notice legitimately enumerates protected bases; scanning the
    whole letter for those words would flag every compliant letter. The
    protected-characteristic check has to run on the prose the drafter wrote.
    """
    kept = [
        p for p in _split_paragraphs(letter)
        if "equal credit opportunity act" not in p.lower()
    ]
    return "\n\n".join(kept).lower()


def check_elements(letter: str, case: dict) -> dict[str, bool]:
    t = letter.lower()
    bureau = case["bureau"].lower()

    # E1 — every recorded principal reason is stated.
    e1 = all(_has_any(t, group) for group in case["reason_keywords"])

    # E2 — ECOA notice naming the protected bases.
    e2 = (
        "equal credit opportunity act" in t
        and sum(b in t for b in PROTECTED_BASES) >= 4
    )

    # E3 — federal enforcement agency named, with an address.
    e3 = (
        _has_any(t, ["consumer financial protection bureau",
                     "bureau of consumer financial protection"])
        and _has_any(t, ["1700 g street", "washington, dc", "20552"])
    )

    # E4 — consumer reporting agency: name, address, toll-free number.
    e4 = (
        bureau in t
        and _has_any(t, ["p.o. box", "po box"])
        and bool(TOLL_FREE.search(letter))
    )

    # E5 — the agency did not make the decision and cannot explain it.
    e5 = (
        _has_any(t, ["did not make", "does not make", "was not involved",
                     "played no part", "did not play"])
        and _has_any(t, ["decision", "decide"])
    )

    # E6 — free copy of the report within 60 days.
    e6 = _has_any(t, ["free copy", "free disclosure", "copy of your report at no",
                      "no cost"]) and "60 days" in t

    # E7 — right to dispute inaccuracies.
    e7 = _has_any(t, ["dispute", "disputing"]) and _has_any(
        t, ["accuracy", "inaccurac", "incomplete", "completeness"]
    )

    return {"E1": e1, "E2": e2, "E3": e3, "E4": e4, "E5": e5, "E6": e6, "E7": e7}


# --------------------------------------------------------------------------
# Flesch-Kincaid grade level, implemented locally to avoid a dependency the
# lab environment would otherwise have to carry.
# --------------------------------------------------------------------------

_VOWELS = "aeiouy"


def _syllables(word: str) -> int:
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    count, prev_vowel = 0, False
    for ch in word:
        is_vowel = ch in _VOWELS
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def flesch_kincaid_grade(text: str) -> float:
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    words = re.findall(r"[A-Za-z']+", text)
    if not sentences or not words:
        return 0.0
    syl = sum(_syllables(w) for w in words)
    return round(
        0.39 * (len(words) / len(sentences)) + 11.8 * (syl / len(words)) - 15.59, 2
    )


# --------------------------------------------------------------------------

def rule_check(letter: str, case: dict) -> dict:
    """Full deterministic verdict for one letter."""
    elements = check_elements(letter, case)
    body = _body_excluding_ecoa_notice(letter)

    forbidden_hits = sorted({tok for tok in case["forbidden_tokens"] if tok in body})
    missing_figures = [f for f in case["required_figures"] if f not in letter]
    grade = flesch_kincaid_grade(letter)

    readability_ok = (
        True if case["readability_target"] is None
        else grade <= case["readability_target"]
    )

    return {
        "elements": elements,
        "missing_elements": [k for k, v in elements.items() if not v],
        "regulatory_complete": all(elements.values()),
        "forbidden_token_hits": forbidden_hits,
        "reason_fidelity_clean": not forbidden_hits,
        "missing_required_figures": missing_figures,
        "flesch_kincaid_grade": grade,
        "readability_target": case["readability_target"],
        "readability_ok": readability_ok,
        "rule_pass": (
            all(elements.values())
            and not forbidden_hits
            and not missing_figures
            and readability_ok
        ),
    }
