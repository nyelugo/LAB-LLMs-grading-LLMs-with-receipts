#!/bin/bash
# Controls for the deterministic rule checker - no API calls, no cost
cd "$(dirname "$0")"
PY=/opt/homebrew/Caskroom/miniconda/base/envs/bootcamp-env/bin/python
[ -x "$PY" ] || PY=python3
"$PY" test_rule_checker.py 
echo
echo "Press any key to close..."
read -n 1 -s
