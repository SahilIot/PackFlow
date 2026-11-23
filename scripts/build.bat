@echo off
REM Builds dist\PackFlow\PackFlow.exe and tests the packaged exe.
REM Requires Python 3.10+ for Windows (python.org, tick "Add python.exe to PATH").
setlocal
cd /d "%~dp0.."
REM (the script lives in scripts\ ; everything below runs from the project root)

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
pyinstaller --noconfirm --clean packaging\PackFlow.spec || exit /b 1

echo.
echo ===== Checking that the Qt printing components were packaged =====
dir /s /b "dist\PackFlow\Qt6PrintSupport.dll" 2>nul | find /i "Qt6PrintSupport.dll" >nul || (echo ERROR: Qt6PrintSupport.dll is missing from the build. & exit /b 1)
dir /s /b "dist\PackFlow\QtPrintSupport.pyd" 2>nul | find /i "QtPrintSupport.pyd" >nul || (echo ERROR: QtPrintSupport.pyd is missing from the build. & exit /b 1)
dir /s /b "dist\PackFlow\qwindows.dll" 2>nul | find /i "qwindows.dll" >nul || (echo ERROR: Qt Windows platform plugin is missing. & exit /b 1)
echo Qt printing components found.

echo.
echo ===== Testing the packaged executable =====
del "%TEMP%\PackFlow_selftest.txt" >nul 2>nul
start /wait "" "dist\PackFlow\PackFlow.exe" --selftest
set RC=%ERRORLEVEL%
if exist "%TEMP%\PackFlow_selftest.txt" type "%TEMP%\PackFlow_selftest.txt"
echo.
if not "%RC%"=="0" (echo SELF-TEST FAILED - see above. & exit /b 1)
echo ===== Printers as seen by the packaged exe =====
set MPP_NO_DIALOG=1
del "%TEMP%\PackFlow_printers.txt" >nul 2>nul
start /wait "" "dist\PackFlow\PackFlow.exe" --printer-diag
if exist "%TEMP%\PackFlow_printers.txt" type "%TEMP%\PackFlow_printers.txt"
echo.
echo Build OK: dist\PackFlow\PackFlow.exe
echo Copy the whole dist\PackFlow folder to the factory PC (or zip it).
endlocal
