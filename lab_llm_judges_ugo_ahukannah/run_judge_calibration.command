#!/bin/bash
# Calibration study: does the judge discriminate between injected defects?
cd "$(dirname "$0")"
PY=/opt/homebrew/Caskroom/miniconda/base/envs/bootcamp-env/bin/python
[ -x "$PY" ] || PY=python3
"$PY" judge_calibration.py 
echo
echo "Press any key to close..."
read -n 1 -s
