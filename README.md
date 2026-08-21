# LAB | LLMs grading LLMs—with receipts

Week 7 of the Ironhack AI Consulting Bootcamp — designing, implementing and
running an LLM evaluation strategy for a client, end to end.
**Author:** Nnanyelugo Ahukannah

A fork of [`ai-consulting-bootcamp/lab-llm-judges`](https://github.com/ai-consulting-bootcamp/lab-llm-judges).
The lab brief (`instructions.md`) and grading rubric (`rubric.md`) are kept
unchanged; everything else in this repo is the submission.

## Start here

All lab deliverables live in
**[`lab_llm_judges_ugo_ahukannah/`](lab_llm_judges_ugo_ahukannah/)** — see
[its README](lab_llm_judges_ugo_ahukannah/README.md) for the scenario, the file
map and how to run the code.

The two-minute version:

- The client is a US regional bank automating loan decline letters.
- Two models were tested, and every letter was graded twice — once by an LLM
  judge, once by a deterministic compliance checker.
- **9 of 10 letters were missing a mandatory legal disclosure. The LLM judge
  scored all ten letters 5/5 — the nine defective ones included.**
- [`evaluation_memo.md`](lab_llm_judges_ugo_ahukannah/evaluation_memo.md) is the
  client-facing write-up of that finding.

## Structure

| Path | What it is |
|---|---|
| [`instructions.md`](instructions.md) | The lab brief, unchanged from the upstream bootcamp repo |
| [`rubric.md`](rubric.md) | The grading rubric this submission is reviewed against, unchanged |
| [`lab_llm_judges_ugo_ahukannah/`](lab_llm_judges_ugo_ahukannah/) | Every lab deliverable — the four Part 1 markdown documents, the Python implementation, the executed notebook, and the JSON results |
| `lab_llm_judges_ugo_ahukannah/*.md` | Benchmark audit, evaluation design, client memo, reflection, implementation summary |
| `lab_llm_judges_ugo_ahukannah/*.py` | Pipeline, test cases, rule checker, calibration study, tests |
| `lab_llm_judges_ugo_ahukannah/*.json` | Run outputs, including every generated letter and both graders' verdicts |
| `lab_llm_judges_ugo_ahukannah/run_*.command` / `.bat` | Double-clickable launchers, macOS and Windows |

The folder name follows the submission format in the lab brief
(`lab_llm_judges_[your_name]`).

## Rubric coverage

| Rubric rows | Where |
|---|---|
| 1, 7, 12 — benchmark audit | [`benchmark_audit.md`](lab_llm_judges_ugo_ahukannah/benchmark_audit.md) |
| 2, 8, 13 — five evaluation prompts | [`evaluation_design.md`](lab_llm_judges_ugo_ahukannah/evaluation_design.md) |
| 3, 14 — LLM-as-judge prompt, bias, calibration | [`evaluation_design.md`](lab_llm_judges_ugo_ahukannah/evaluation_design.md) |
| 4, 9, 17–19 — pipeline, setup, judge, dataset | [`llm_judge_evaluation.py`](lab_llm_judges_ugo_ahukannah/llm_judge_evaluation.py), [`eval_cases.py`](lab_llm_judges_ugo_ahukannah/eval_cases.py) |
| 5, 20–21 — run, metrics, analysis, visualisation | [`llm_judge_evaluation.ipynb`](lab_llm_judges_ugo_ahukannah/llm_judge_evaluation.ipynb), `evaluation_results.json`, `figures/` |
| 6, 10, 15 — report with hedging and caveats | [`evaluation_memo.md`](lab_llm_judges_ugo_ahukannah/evaluation_memo.md) |
| 11 — client scenario | [`benchmark_audit.md`](lab_llm_judges_ugo_ahukannah/benchmark_audit.md) |
| 16 — reflection | [`reflection.md`](lab_llm_judges_ugo_ahukannah/reflection.md) |

Extension activities completed: model comparison (`gpt-4o-mini` vs `gpt-4o`) and a
calibration study ([`judge_calibration.py`](lab_llm_judges_ugo_ahukannah/judge_calibration.py)).

## Keys

No API key is stored in this repository. Keys load at runtime from
`~/.config/ironhack/.env.local`, outside every git repo.
