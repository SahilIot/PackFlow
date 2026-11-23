@echo off
REM Starts the app from source (for development) without building the exe.
cd /d "%~dp0.."
REM (the script lives in scripts\ ; everything below runs from the project root)
if not exist .venv (py -3 -m venv .venv)
call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt
python main.py
