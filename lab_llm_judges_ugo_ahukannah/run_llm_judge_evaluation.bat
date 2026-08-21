@echo off
REM Full evaluation: 5 cases x 2 models, judged 3x each (~40 API calls, ~$0.03)
cd /d "%~dp0"
python llm_judge_evaluation.py 
echo.
pause
