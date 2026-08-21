"""Calibration study: does the judge discriminate, or does it rubber-stamp?

The main evaluation returned 5/5 on every letter while the deterministic checker
failed every letter. Two explanations fit that: either the judge is lenient, or
the judge is not reading the criteria at all. Those call for different fixes, so
this script separates them.

Method: take one hand-written compliant letter and inject a single known defect
per variant, each mapped to a specific score anchor in the rubric. If the judge
is calibrated, the scores fall in the anchored order. If every variant scores 5,
the judge is not discriminating and no amount of averaging repairs it.

Run:  python judge_calibration.py

Author: Nnanyelugo Ahukannah
"""

from __future__ import annotations

import json
import os
import statistics
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from eval_cases import TEST_CASES
from llm_judge_evaluation import CostLedger, RUN_COST_CEILING_USD, judge_letter
from rule_checker import rule_check
from test_rule_checker import GOLDEN_P1

HERE = Path(__file__).resolve().parent
load_dotenv(Path.home() / ".config/ironhack/.env.local")
load_dotenv(HERE / ".env", override=True)

CASE = TEST_CASES[0]  # P1
REPEATS = 3

# Each variant carries exactly one defect, mapped to the rubric's score anchor.
VARIANTS = [
    {
        "name": "clean",
        "defect": "none — all seven elements present",
        "expected_score": 5,
        "letter": GOLDEN_P1,
    },
    {
        "name": "missing_ecoa_notice",
        "defect": "E2 removed (ECOA anti-discrimination notice)",
        "expected_score": 3,
        "letter": GOLDEN_P1.replace(
            "Notice: The federal Equal Credit Opportunity Act prohibits creditors from\n"
            "discriminating against credit applicants on the basis of race, color, religion,\n"
            "national origin, sex, marital status, age (provided the applicant has the\n"
            "capacity to enter into a binding contract); because all or part of the\n"
            "applicant's income derives from any public assistance program; or because the\n"
            "applicant has in good faith exercised any right under the Consumer Credit\n"
            "Protection Act. The federal agency",
            "The federal agency",
        ),
    },
    {
        "name": "unsupported_reason",
        "defect": "a decline reason absent from the decision record",
        "expected_score": 2,
        "letter": GOLDEN_P1.replace(
            "2. The length of your credit history is too short.",
            "2. The length of your credit history is too short.\n"
            "3. Your recent change of employer left your income unverified.",
        ),
    },
    {
        "name": "protected_characteristic",
        "defect": "protected characteristic cited in the letter body",
        "expected_score": 1,
        "letter": GOLDEN_P1.replace(
            "Dear Ms. Raman,",
            "Dear Ms. Raman,\n\nWe understand from your application that you are "
            "currently on maternity leave and that part of your household income "
            "is public assistance.",
        ),
    },
]


def main() -> int:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    ledger = CostLedger(RUN_COST_CEILING_USD)
    rows = []

    print(f"Judging {len(VARIANTS)} variants x {REPEATS} repeats @ T=0\n")
    for v in VARIANTS:
        # Sanity: confirm the injected defect is really there before judging it.
        rc = rule_check(v["letter"], CASE)
        judgements = [judge_letter(client, CASE, v["letter"], ledger) for _ in range(REPEATS)]
        scores = [j["score"] for j in judgements]
        rows.append(
            {
                "variant": v["name"],
                "defect": v["defect"],
                "expected_score": v["expected_score"],
                "judge_scores": scores,
                "judge_mean": round(statistics.mean(scores), 2),
                "checker_missing_elements": rc["missing_elements"],
                "checker_forbidden_hits": rc["forbidden_token_hits"],
                "judge_missing_elements": judgements[0]["missing_elements"],
                "judge_unsupported_reasons": judgements[0]["unsupported_reasons"],
                "judge_reasoning": judgements[0]["reasoning"],
            }
        )

    print(f"{'variant':<26}{'expected':>9}{'judge':>8}{'spread':>8}   checker caught")
    print("-" * 86)
    for r in rows:
        spread = max(r["judge_scores"]) - min(r["judge_scores"])
        caught = r["checker_missing_elements"] + r["checker_forbidden_hits"] or ["-"]
        print(f"{r['variant']:<26}{r['expected_score']:>9}{r['judge_mean']:>8}"
              f"{spread:>8}   {', '.join(map(str, caught))}")

    means = [r["judge_mean"] for r in rows]
    expected = [r["expected_score"] for r in rows]
    discriminates = len(set(means)) > 1
    ordered = all(a >= b for a, b in zip(means, means[1:]))

    print("\nVERDICT")
    print(f"  judge separates the variants at all : {discriminates}")
    print(f"  ordering matches the rubric anchors : {ordered and discriminates}")
    print(f"  judge score range across variants   : {min(means)} - {max(means)} "
          f"(expected {min(expected)} - {max(expected)})")
    if not discriminates:
        print("\n  The judge returns one score regardless of injected defect. It is not\n"
              "  measuring the rubric. Averaging more repeats cannot fix this; the judge\n"
              "  model or the prompt has to change.")

    payload = {
        "case": CASE["id"],
        "judge_repeats": REPEATS,
        "variants": rows,
        "verdict": {
            "discriminates": discriminates,
            "ordering_matches_anchors": ordered and discriminates,
            "judge_score_range": [min(means), max(means)],
            "expected_score_range": [min(expected), max(expected)],
        },
        "cost_usd": round(ledger.total_cost, 6),
    }
    out = HERE / "judge_calibration_results.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nCost ${ledger.total_cost:.4f} — written to {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
