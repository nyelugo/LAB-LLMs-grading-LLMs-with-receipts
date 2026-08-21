@echo off
REM Calibration study: does the judge discriminate between injected defects?
cd /d "%~dp0"
python judge_calibration.py 
echo.
pause
