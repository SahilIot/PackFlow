@echo off
REM Builds dist\MachinePackingPrint\MachinePackingPrint.exe and tests the packaged exe.
REM Requires Python 3.10+ for Windows (python.org, tick "Add python.exe to PATH").
setlocal
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version || (echo Python was not found. Install it from https://www.python.org/downloads/ & exit /b 1)

if not exist .venv (
    %PY% -m venv .venv || exit /b 1
)
call .venv\Scripts\activate.bat || exit /b 1
python -m pip install --upgrade pip || exit /b 1
python -m pip install -r requirements.txt || exit /b 1

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --noconfirm --clean MachinePackingPrint.spec || exit /b 1

echo.
echo ===== Testing the packaged executable =====
del "%TEMP%\MachinePackingPrint_selftest.txt" >nul 2>nul
start /wait "" "dist\MachinePackingPrint\MachinePackingPrint.exe" --selftest
set RC=%ERRORLEVEL%
if exist "%TEMP%\MachinePackingPrint_selftest.txt" type "%TEMP%\MachinePackingPrint_selftest.txt"
echo.
if not "%RC%"=="0" (echo SELF-TEST FAILED - see above. & exit /b 1)
echo Build OK: dist\MachinePackingPrint\MachinePackingPrint.exe
echo Copy the whole dist\MachinePackingPrint folder to the factory PC (or zip it).
endlocal
