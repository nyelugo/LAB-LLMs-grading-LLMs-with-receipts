@echo off
REM Controls for the deterministic rule checker - no API calls, no cost
cd /d "%~dp0"
python test_rule_checker.py 
echo.
pause
