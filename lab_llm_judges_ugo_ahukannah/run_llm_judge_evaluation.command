#!/bin/bash
# Full evaluation: 5 cases x 2 models, judged 3x each (~40 API calls, ~$0.03)
cd "$(dirname "$0")"
PY=/opt/homebrew/Caskroom/miniconda/base/envs/bootcamp-env/bin/python
[ -x "$PY" ] || PY=python3
"$PY" llm_judge_evaluation.py 
echo
echo "Press any key to close..."
read -n 1 -s
