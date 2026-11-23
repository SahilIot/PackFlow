@echo off
REM Creates installer\Output\PackFlow-Setup.exe  (needs Inno Setup 6: https://jrsoftware.org/isdl.php and a finished build.bat)
setlocal
cd /d "%~dp0"
if not exist "dist\PackFlow\PackFlow.exe" (echo Run build.bat first. & exit /b 1)
set ISCC=
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do if exist %%P set ISCC=%%~P
if "%ISCC%"=="" (echo Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php & exit /b 1)
"%ISCC%" installer\PackFlow.iss || exit /b 1
echo.
echo Installer: installer\Output\PackFlow-Setup.exe
endlocal
