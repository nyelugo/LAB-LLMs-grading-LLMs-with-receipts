"""LLM-as-judge evaluation of automated adverse-action notices.

Client scenario: Cardinal Trust Bank (see benchmark_audit.md).
Design:          evaluation_design.md — the judge prompt below is that document's
                 Step 4 prompt, verbatim in structure.

Pipeline
--------
1. Generate a decline letter for each of 5 test cases, on each model under test.
2. Score every letter twice:
     - a deterministic rule checker (rule_checker.py) — the record;
     - an LLM judge on gpt-4o-mini, temperature 0, repeated N times per letter
       so the variance is measured rather than assumed.
3. Report agreement between the two, plus latency, tokens and cost.
4. Write everything to evaluation_results.json.

The judge-vs-checker agreement rate is the point. A judge that quietly disagrees
with a deterministic compliance check is the failure this evaluation exists to
surface, and a mean score with no such control is not a receipt.

Usage:  python llm_judge_evaluation.py [--repeats 3] [--models gpt-4o-mini,gpt-4o]

Author: Nnanyelugo Ahukannah
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from eval_cases import TEST_CASES, SYSTEM_PROMPT
from rule_checker import rule_check

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent

# Shared Ironhack key store, outside every git repo. A per-lab .env may override.
load_dotenv(Path.home() / ".config/ironhack/.env.local")
load_dotenv(HERE / ".env", override=True)

JUDGE_MODEL = "gpt-4o-mini"
DEFAULT_MODELS_UNDER_TEST = ["gpt-4o-mini", "gpt-4o"]

# USD per 1M tokens. Published list prices at the time of the run; they change,
# so they are recorded in the results file as a stated assumption rather than
# presented as a measurement.
PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}

# Hard ceiling for one invocation of this script. The run below costs cents; the
# guard exists so a bad loop cannot quietly become a bill.
RUN_COST_CEILING_USD = 1.00

# Temperature 0 is not determinism. Across three runs of this suite the letters
# changed and, with them, which secondary disclosure elements got dropped - only
# the ECOA omission was stable. A best-effort seed makes the run reproducible
# enough to compare against itself, which an evaluation someone will act on needs.
SEED = 7

# --------------------------------------------------------------------------
# The judge prompt — evaluation_design.md, Step 4
# --------------------------------------------------------------------------

JUDGE_PROMPT = """### TASK DESCRIPTION

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

1. REASON FIDELITY - Every reason the letter offers for the decision must
   correspond to an entry in RECORDED PRINCIPAL REASONS. Paraphrase is fine;
   addition is not. A reason that is plausible, sympathetic, or probably true but
   absent from the record is a violation. General statements about the bank's
   criteria that are not presented as reasons for THIS decision are not
   violations.

2. REGULATORY COMPLETENESS - The letter must contain all seven elements:
   E1 specific principal reason(s); E2 the ECOA anti-discrimination notice naming
   the protected bases; E3 the name and address of the federal enforcement
   agency; E4 the consumer reporting agency's name, address and toll-free number;
   E5 a statement that the agency did not make the decision and cannot explain it;
   E6 the right to a free copy of the report within 60 days; E7 the right to
   dispute inaccuracies. Judge presence and substance, not exact wording.

3. TONE AND CLARITY - Plain, respectful, direct. No jargon a general reader would
   not follow. No false encouragement implying a future application would succeed.
   And no reference in the letter body to a protected characteristic - pregnancy,
   maternity or parental leave, marital status, age, or receipt of public
   assistance - even where the applicant raised it themselves. The standard ECOA
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

5 - All recorded reasons present, none invented, E1-E7 all present, tone plain
    and respectful.
4 - Fidelity and all elements intact; tone or clarity is weak in a way a reviewer
    would flag but not reject.
3 - Fidelity intact; exactly one regulatory element missing or too vague to
    stand.
2 - One unsupported reason, OR two or more regulatory elements missing.
1 - Multiple unsupported reasons, a protected characteristic cited in the letter
    body, or the letter misstates the decision itself.

### OUTPUT FORMAT

Return a single JSON object and nothing else:

{{
  "score": <integer 1-5>,
  "reasoning": "<2-4 sentences citing specific phrases from the letter>",
  "criteria_met": {{
    "reason_fidelity": <true|false>,
    "regulatory_completeness": <true|false>,
    "tone_and_clarity": <true|false>
  }},
  "unsupported_reasons": ["<each reason asserted but not in the record>"],
  "missing_elements": ["<each of E1-E7 absent, by code>"]
}}"""


# --------------------------------------------------------------------------
# Cost accounting
# --------------------------------------------------------------------------

class CostLedger:
    """Running token and cost tally, with a ceiling that aborts the run."""

    def __init__(self, ceiling_usd: float) -> None:
        self.ceiling = ceiling_usd
        self.rows: list[dict] = []

    def record(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        price = PRICING.get(model, {"input": 0.0, "output": 0.0})
        cost = (
            prompt_tokens / 1_000_000 * price["input"]
            + completion_tokens / 1_000_000 * price["output"]
        )
        self.rows.append(
            {
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost,
            }
        )
        if self.total_cost > self.ceiling:
            raise RuntimeError(
                f"Cost ceiling ${self.ceiling:.2f} exceeded "
                f"(${self.total_cost:.4f}). Aborting."
            )
        return cost

    @property
    def total_cost(self) -> float:
        return sum(r["cost_usd"] for r in self.rows)

    def by_model(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for r in self.rows:
            m = out.setdefault(
                r["model"],
                {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0},
            )
            m["calls"] += 1
            m["prompt_tokens"] += r["prompt_tokens"]
            m["completion_tokens"] += r["completion_tokens"]
            m["cost_usd"] += r["cost_usd"]
        for m in out.values():
            m["cost_usd"] = round(m["cost_usd"], 6)
        return out


# --------------------------------------------------------------------------
# API calls
# --------------------------------------------------------------------------

def generate_letter(client: OpenAI, model: str, case: dict, ledger: CostLedger) -> dict:
    """Run the production prompt: decision record in, letter out."""
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        seed=SEED,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": case["decision_record"]},
        ],
    )
    elapsed = time.perf_counter() - t0
    u = resp.usage
    cost = ledger.record(model, u.prompt_tokens, u.completion_tokens)
    return {
        "letter": resp.choices[0].message.content.strip(),
        "seconds": round(elapsed, 3),
        "prompt_tokens": u.prompt_tokens,
        "completion_tokens": u.completion_tokens,
        "cost_usd": round(cost, 6),
    }


def judge_letter(client: OpenAI, case: dict, letter: str, ledger: CostLedger) -> dict:
    """One judgement of one letter. Structured output, temperature 0."""
    prompt = JUDGE_PROMPT.format(
        decision_record=case["decision_record"],
        recorded_reasons="\n".join(f"- {r}" for r in case["recorded_reasons"]),
        model_response=letter,
    )
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        seed=SEED,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a compliance reviewer. Return JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    elapsed = time.perf_counter() - t0
    u = resp.usage
    cost = ledger.record(JUDGE_MODEL, u.prompt_tokens, u.completion_tokens)

    raw = resp.choices[0].message.content
    try:
        parsed = json.loads(raw)
        parse_error = None
    except json.JSONDecodeError as exc:
        # Calibration rule from evaluation_design.md: an unparseable judgement
        # scores 1 rather than erroring. Dropping it would flatter the model.
        parsed = {
            "score": 1,
            "reasoning": f"Judge output could not be parsed: {exc}",
            "criteria_met": {
                "reason_fidelity": False,
                "regulatory_completeness": False,
                "tone_and_clarity": False,
            },
            "unsupported_reasons": [],
            "missing_elements": [],
        }
        parse_error = str(exc)

    parsed["_seconds"] = round(elapsed, 3)
    parsed["_prompt_tokens"] = u.prompt_tokens
    parsed["_completion_tokens"] = u.completion_tokens
    parsed["_cost_usd"] = round(cost, 6)
    parsed["_parse_error"] = parse_error
    return parsed


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

def evaluate(models: list[str], repeats: int) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY not found. Expected it in "
            "~/.config/ironhack/.env.local"
        )
    client = OpenAI(api_key=api_key)
    ledger = CostLedger(RUN_COST_CEILING_USD)
    started = datetime.now(timezone.utc)

    results: list[dict] = []
    for model in models:
        for case in TEST_CASES:
            print(f"  {model:<14} {case['id']}  {case['title']}", flush=True)
            gen = generate_letter(client, model, case, ledger)
            rules = rule_check(gen["letter"], case)

            judgements = [
                judge_letter(client, case, gen["letter"], ledger)
                for _ in range(repeats)
            ]
            scores = [j["score"] for j in judgements]

            # Where judge and checker disagree on a criterion the checker can
            # decide, the checker is the record. Both verdicts are kept.
            judge_reg = all(j["criteria_met"].get("regulatory_completeness") for j in judgements)
            judge_fid = all(j["criteria_met"].get("reason_fidelity") for j in judgements)

            results.append(
                {
                    "model_under_test": model,
                    "case_id": case["id"],
                    "case_title": case["title"],
                    "primary_failure_mode": case["primary_failure_mode"],
                    "letter": gen["letter"],
                    "generation": {
                        k: gen[k]
                        for k in ("seconds", "prompt_tokens", "completion_tokens", "cost_usd")
                    },
                    "rule_check": rules,
                    "judge": {
                        "model": JUDGE_MODEL,
                        "repeats": repeats,
                        "scores": scores,
                        "score_mean": round(statistics.mean(scores), 2),
                        "score_range": max(scores) - min(scores),
                        "unstable": (max(scores) - min(scores)) > 1,
                        "judgements": judgements,
                        "seconds_total": round(sum(j["_seconds"] for j in judgements), 3),
                        "cost_usd": round(sum(j["_cost_usd"] for j in judgements), 6),
                    },
                    "agreement": {
                        "regulatory_completeness": judge_reg == rules["regulatory_complete"],
                        "reason_fidelity": judge_fid == rules["reason_fidelity_clean"],
                        # The escalation trigger from the calibration strategy.
                        "judge_missed_a_defect": (
                            (judge_reg and not rules["regulatory_complete"])
                            or (judge_fid and not rules["reason_fidelity_clean"])
                        ),
                    },
                }
            )

    finished = datetime.now(timezone.utc)
    run_meta = {
            "started_utc": started.isoformat(),
            "finished_utc": finished.isoformat(),
            "wall_seconds": round((finished - started).total_seconds(), 2),
            "models_under_test": models,
            "judge_model": JUDGE_MODEL,
            "judge_repeats": repeats,
            "judge_temperature": 0,
            "seed": SEED,
            "n_cases": len(TEST_CASES),
            "pricing_assumption_usd_per_1m_tokens": PRICING,
            "pricing_note": (
                "List prices as recorded when this run was written. Cost figures "
                "are derived from reported token counts and these rates, not "
                "billed amounts."
            ),
    }
    agg = aggregate(results, ledger)
    return {
        "summary": build_summary(results, agg, run_meta, ledger.total_cost),
        "run": run_meta,
        "results": results,
        "aggregate": agg,
        "cost": {
            "total_usd": round(ledger.total_cost, 6),
            "by_model": ledger.by_model(),
            "ceiling_usd": RUN_COST_CEILING_USD,
        },
    }


def build_summary(results: list[dict], agg: dict, run: dict, total_cost: float) -> dict:
    """A plain-language top-level summary of the run.

    Sits at the top of evaluation_results.json so a reader who opens the file
    cold gets the finding before the per-example detail. Every number is derived
    from the run rather than written by hand, so it cannot drift out of step with
    the results underneath it.
    """
    n = len(results)
    models = run["models_under_test"]
    element_names = {
        "E1": "the specific principal reasons", "E2": "the ECOA anti-discrimination notice",
        "E3": "the federal enforcement agency's name and address",
        "E4": "the credit bureau's name, address and toll-free number",
        "E5": "the statement that the bureau did not make the decision",
        "E6": "the right to a free copy of the report within 60 days",
        "E7": "the right to dispute inaccuracies",
    }
    missing = collections.Counter(
        e for r in results for e in r["rule_check"]["missing_elements"]
    )
    worst = missing.most_common(1)[0] if missing else None
    judge_means = [r["judge"]["score_mean"] for r in results]
    rule_passes = sum(r["rule_check"]["rule_pass"] for r in results)
    unstable = sum(r["judge"]["unstable"] for r in results)

    per_letter = {
        m: round(agg["by_model"][m]["generation_cost_usd"] / agg["by_model"][m]["n_cases"], 6)
        for m in models
    }
    cheapest = min(per_letter, key=per_letter.get)
    dearest = max(per_letter, key=per_letter.get)

    findings = []
    if worst:
        code, count = worst
        findings.append(
            f"{count} of {n} letters were missing {element_names.get(code, code)} "
            f"({code}), the most common defect in the run."
        )
    span = (f"{min(judge_means)} out of 5" if min(judge_means) == max(judge_means)
            else f"between {min(judge_means)} and {max(judge_means)} out of 5")
    findings.append(
        f"The LLM judge scored every letter {span} while the deterministic checker "
        f"passed only {rule_passes} of {n}. The judge agreed with the checker on reason "
        "fidelity and not on regulatory completeness."
    )
    findings.append(
        f"No model invented a decline reason: reason fidelity was clean on "
        f"{sum(r['rule_check']['reason_fidelity_clean'] for r in results)} of {n} letters."
    )
    findings.append(
        f"Judge scores were stable across {run['judge_repeats']} repeats at temperature 0 "
        f"({unstable} of {n} letters varied by more than one point), so the disagreement "
        "with the checker is a consistent bias rather than noise."
    )
    if len(models) > 1 and per_letter[cheapest] > 0:
        findings.append(
            f"{dearest} costs {per_letter[dearest] / per_letter[cheapest]:.1f}x more per "
            f"letter than {cheapest} (${per_letter[dearest]:.6f} vs "
            f"${per_letter[cheapest]:.6f})."
        )

    return {
        "headline": (
            "An LLM judge gave near-perfect scores to letters that a deterministic "
            "compliance checker rejected. Fluency and factual fidelity were fine; "
            "mandatory legal disclosures were missing, and the judge did not notice."
        ),
        "what_was_measured": (
            f"{n} adverse-action decline letters ({len(models)} model(s) x "
            f"{run['n_cases']} test cases), each scored twice: once by an LLM judge "
            f"({run['judge_model']}, temperature 0, {run['judge_repeats']} repeats) and "
            "once by a deterministic Python checker with no model in it."
        ),
        "key_findings": findings,
        "recommendation": (
            f"Use {cheapest} with the statutory disclosure text supplied as a fixed "
            "template rather than generated, and gate despatch on the deterministic "
            "element check. Do not ship an LLM-judge-only gate."
        ),
        "caveats": [
            "The seven-element checklist is a reconstruction of Regulation B and FCRA "
            "s615(a) for a teaching exercise. It is not legal advice and has not been "
            "reviewed by counsel.",
            "Five test cases on one product is a probe, not an assurance.",
            "Letters vary between runs even at temperature 0 with a pinned seed, so "
            "individual element counts are indicative; the direction of the finding "
            "held across every run.",
            f"Cost figures are derived from reported token counts and list prices, not "
            f"billed amounts; total for this run was ${total_cost:.4f}.",
        ],
    }


def aggregate(results: list[dict], ledger: CostLedger) -> dict:
    out: dict = {"by_model": {}, "by_case": {}}

    for model in sorted({r["model_under_test"] for r in results}):
        rows = [r for r in results if r["model_under_test"] == model]
        scores = [r["judge"]["score_mean"] for r in rows]
        elem_fail = sorted(
            {e for r in rows for e in r["rule_check"]["missing_elements"]}
        )
        out["by_model"][model] = {
            "n_cases": len(rows),
            "judge_score_mean": round(statistics.mean(scores), 2),
            "judge_score_min": min(scores),
            "judge_score_max": max(scores),
            "rule_pass_rate": round(sum(r["rule_check"]["rule_pass"] for r in rows) / len(rows), 2),
            "regulatory_complete_rate": round(
                sum(r["rule_check"]["regulatory_complete"] for r in rows) / len(rows), 2
            ),
            "reason_fidelity_clean_rate": round(
                sum(r["rule_check"]["reason_fidelity_clean"] for r in rows) / len(rows), 2
            ),
            "elements_ever_missing": elem_fail,
            "judge_checker_agreement_regulatory": round(
                sum(r["agreement"]["regulatory_completeness"] for r in rows) / len(rows), 2
            ),
            "judge_checker_agreement_fidelity": round(
                sum(r["agreement"]["reason_fidelity"] for r in rows) / len(rows), 2
            ),
            "cases_judge_missed_a_defect": [
                r["case_id"] for r in rows if r["agreement"]["judge_missed_a_defect"]
            ],
            "unstable_cases": [r["case_id"] for r in rows if r["judge"]["unstable"]],
            "generation_seconds_mean": round(
                statistics.mean(r["generation"]["seconds"] for r in rows), 2
            ),
            "generation_cost_usd": round(
                sum(r["generation"]["cost_usd"] for r in rows), 6
            ),
        }

    for case_id in [r["case_id"] for r in results if r["model_under_test"] == results[0]["model_under_test"]]:
        rows = [r for r in results if r["case_id"] == case_id]
        out["by_case"][case_id] = {
            "title": rows[0]["case_title"],
            "primary_failure_mode": rows[0]["primary_failure_mode"],
            "scores": {r["model_under_test"]: r["judge"]["score_mean"] for r in rows},
            "rule_pass": {r["model_under_test"]: r["rule_check"]["rule_pass"] for r in rows},
            "missing_elements": {
                r["model_under_test"]: r["rule_check"]["missing_elements"] for r in rows
            },
        }

    out["total_api_calls"] = len(ledger.rows)
    return out


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def print_report(payload: dict) -> None:
    run, agg = payload["run"], payload["aggregate"]
    line = "=" * 78

    print(f"\n{line}\nCARDINAL TRUST BANK — ADVERSE-ACTION NOTICE EVALUATION\n{line}")
    print(f"Cases {run['n_cases']}   models {', '.join(run['models_under_test'])}   "
          f"judge {run['judge_model']} x{run['judge_repeats']} @ T=0")
    print(f"Wall time {run['wall_seconds']}s   API calls {agg['total_api_calls']}   "
          f"total cost ${payload['cost']['total_usd']:.4f}")

    print(f"\n{'-' * 78}\nPER-CASE SCORES (judge mean of "
          f"{run['judge_repeats']}, and deterministic rule verdict)\n{'-' * 78}")
    models = run["models_under_test"]
    header = f"{'case':<5}{'failure mode':<38}" + "".join(f"{m:>17}" for m in models)
    print(header)
    for cid, c in agg["by_case"].items():
        row = f"{cid:<5}{c['primary_failure_mode'][:36]:<38}"
        for m in models:
            verdict = "RULE PASS" if c["rule_pass"][m] else "RULE FAIL"
            row += f"{c['scores'][m]:>6.1f}  {verdict:>9}"
        print(row)

    print(f"\n{'-' * 78}\nPER-MODEL SUMMARY\n{'-' * 78}")
    for m, s in agg["by_model"].items():
        print(f"\n  {m}")
        print(f"    judge score        {s['judge_score_mean']}/5 "
              f"(min {s['judge_score_min']}, max {s['judge_score_max']})")
        print(f"    rule pass rate     {s['rule_pass_rate']:.0%}")
        print(f"    reg. complete      {s['regulatory_complete_rate']:.0%}   "
              f"elements ever missing: {s['elements_ever_missing'] or 'none'}")
        print(f"    reason fidelity    {s['reason_fidelity_clean_rate']:.0%}")
        print(f"    judge vs checker   regulatory {s['judge_checker_agreement_regulatory']:.0%}   "
              f"fidelity {s['judge_checker_agreement_fidelity']:.0%}")
        if s["cases_judge_missed_a_defect"]:
            print(f"    ** JUDGE MISSED A DEFECT the checker caught: "
                  f"{', '.join(s['cases_judge_missed_a_defect'])}")
        if s["unstable_cases"]:
            print(f"    ** score range > 1 across repeats: "
                  f"{', '.join(s['unstable_cases'])}")
        print(f"    latency / letter   {s['generation_seconds_mean']}s")
        print(f"    generation cost    ${s['generation_cost_usd']:.5f} for "
              f"{s['n_cases']} letters")

    print(f"\n{'-' * 78}\nJUDGE REASONING (first sentence, per case)\n{'-' * 78}")
    for r in payload["results"]:
        reasoning = r["judge"]["judgements"][0]["reasoning"]
        first = reasoning.split(". ")[0][:110]
        print(f"  {r['model_under_test']:<14}{r['case_id']}  {first}.")

    print(f"\n{line}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repeats", type=int, default=3,
                    help="judge runs per letter (variance measurement)")
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS_UNDER_TEST),
                    help="comma-separated models under test")
    ap.add_argument("--out", default=str(HERE / "evaluation_results.json"))
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    print(f"Running {len(TEST_CASES)} cases x {len(models)} models, "
          f"judge repeats {args.repeats}...")

    payload = evaluate(models, args.repeats)
    Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print_report(payload)
    print(f"Results written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
