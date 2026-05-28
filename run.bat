@echo off
REM Valve Code Selector launcher.
REM Prefers the bundled python\ folder (for distribution); falls back to system
REM "py" launcher (for dev machines that already have Python installed).

cd /d "%~dp0"

REM --- Free port 5037 if a previous instance is still holding it ---
REM Avoids the "Address already in use" silent crash where the window
REM closes before you can read the error.
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":5037 " ^| findstr "LISTENING"') do (
  echo Killing stale process %%P holding port 5037...
  taskkill /PID %%P /F >nul 2>&1
)

if exist "python\python.exe" (
  set "PYEXE=python\python.exe"
) else (
  where py >nul 2>&1
  if %errorlevel%==0 (
    set "PYEXE=py"
  ) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
      set "PYEXE=python"
    ) else (
      echo.
      echo ERROR: No Python found.
      echo This bundle is missing the python\ folder. Re-extract the ZIP, or
      echo install Python 3.10+ from https://www.python.org and re-run.
      echo.
      pause
      exit /b 1
    )
  )
)

echo Starting Valve Code Selector...
echo (Browser will open in ~2 seconds. Close this window to stop.)
echo.
"%PYEXE%" app\server.py

REM If we reach here, the server exited. Pause so any error is readable
REM instead of the window vanishing.
echo.
echo --- Server stopped (exit code %errorlevel%) ---
pause
