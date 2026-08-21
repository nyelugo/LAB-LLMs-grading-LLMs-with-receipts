"""Positive and negative controls for the deterministic rule checker.

A compliance checker that fails everything is indistinguishable from a working
one until you feed it something that should pass. These tests are the evidence
that the E1-E7 assertions discriminate, rather than just rejecting.

Run:  python -m pytest test_rule_checker.py -q
      python test_rule_checker.py          (no pytest required)

Author: Nnanyelugo Ahukannah
"""

from eval_cases import TEST_CASES
from rule_checker import check_elements, flesch_kincaid_grade, rule_check

CASE_P1 = TEST_CASES[0]
CASE_P2 = TEST_CASES[1]
CASE_P3 = TEST_CASES[2]
CASE_P5 = TEST_CASES[4]

# A hand-written letter carrying all seven elements. The positive control.
GOLDEN_P1 = """Cardinal Trust Bank
400 Wexford Avenue, Columbus, OH 43215

Dear Ms. Raman,

Thank you for applying for a $12,000 unsecured personal loan. We are not able to
approve your application.

The principal reasons for our decision are:
1. Your credit score is below our minimum for this product.
2. The length of your credit history is too short.

We obtained a consumer report from Experian in reaching this decision. Experian
did not make the decision and cannot explain the reasons for it. You may contact
them at:

Experian
P.O. Box 2002, Allen, TX 75013
1-888-397-3742

You have the right to request a free copy of your consumer report from Experian
within 60 days of receiving this notice. You also have the right to dispute the
accuracy or completeness of any information in that report directly with
Experian.

Notice: The federal Equal Credit Opportunity Act prohibits creditors from
discriminating against credit applicants on the basis of race, color, religion,
national origin, sex, marital status, age (provided the applicant has the
capacity to enter into a binding contract); because all or part of the
applicant's income derives from any public assistance program; or because the
applicant has in good faith exercised any right under the Consumer Credit
Protection Act. The federal agency that administers compliance with this law
concerning this creditor is the Bureau of Consumer Financial Protection,
1700 G Street NW, Washington, DC 20552.

Sincerely,
Cardinal Trust Bank
"""


def test_golden_letter_passes_every_element():
    """Positive control: the checker is capable of returning all-True."""
    elements = check_elements(GOLDEN_P1, CASE_P1)
    assert all(elements.values()), f"unexpected failures: {elements}"
    assert rule_check(GOLDEN_P1, CASE_P1)["rule_pass"] is True


def test_each_element_can_fail_independently():
    """Negative controls: removing the text that satisfies an element fails it,
    and does not knock out the others."""
    removals = {
        "E2": "The federal Equal Credit Opportunity Act prohibits creditors from",
        "E5": "did not make the decision and cannot explain the reasons for it.",
        "E6": "within 60 days of receiving this notice.",
    }
    for code, snippet in removals.items():
        damaged = GOLDEN_P1.replace(snippet, "")
        elements = check_elements(damaged, CASE_P1)
        assert elements[code] is False, f"{code} survived removal of its text"
        others = {k: v for k, v in elements.items() if k != code}
        # E2 and E3 share a paragraph in the golden letter, so allow that pair.
        unexpected = [k for k, v in others.items() if not v and not (code == "E2" and k == "E3")]
        assert not unexpected, f"removing {code} also broke {unexpected}"


def test_missing_reason_fails_e1():
    damaged = GOLDEN_P1.replace("The length of your credit history is too short.", "")
    assert check_elements(damaged, CASE_P1)["E1"] is False


def test_protected_characteristic_scan_ignores_the_ecoa_boilerplate():
    """The standard notice lists protected bases legitimately. A naive scan over
    the whole letter would flag every compliant letter, so the check excludes
    the notice paragraph — this asserts that it does."""
    assert rule_check(GOLDEN_P1, CASE_P3)["forbidden_token_hits"] == []

    leaked = GOLDEN_P1.replace(
        "Dear Ms. Raman,",
        "Dear Ms. Raman,\n\nWe note that you are currently on maternity leave.",
    )
    assert "maternity" in rule_check(leaked, CASE_P3)["forbidden_token_hits"]


def test_unrecorded_reason_bait_is_caught():
    leaked = GOLDEN_P1.replace(
        "2. The length of your credit history is too short.",
        "2. You recently started a new job, so your employment is not yet established.",
    )
    hits = rule_check(leaked, CASE_P2)["forbidden_token_hits"]
    assert "job" in hits and "employment" in hits


def test_required_figures_and_readability():
    assert rule_check(GOLDEN_P1, CASE_P5)["missing_required_figures"] == ["9,000", "17.9", "36"]
    # Short, plain sentences must score lower than long, latinate ones.
    simple = "The bank said no. You can ask why. We sent a letter. It has the reason."
    dense = ("Notwithstanding the aforementioned determination, the institution "
             "hereby communicates its regrettable inability to accommodate the "
             "aforementioned application for consumer credit accommodation.")
    assert flesch_kincaid_grade(simple) < flesch_kincaid_grade(dense)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {t.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    raise SystemExit(1 if failures else 0)
