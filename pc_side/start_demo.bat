@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "MODEL=..\board_side\model\best_soham_yolo11n.pt"
if not "%~1"=="" set "MODEL=%~1"
"%PYTHON%" web_demo.py --model "%MODEL%" --camera 0
pause
