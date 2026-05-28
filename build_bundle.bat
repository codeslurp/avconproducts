@echo off
REM ============================================================================
REM  build_bundle.bat -- ONE-TIME setup, run on a developer machine with internet.
REM
REM  Downloads embeddable Python and pre-installs Flask + openpyxl into the
REM  python\ folder. After this finishes, ZIP the entire valve-selector\ folder
REM  and ship it to end users. They can run run.bat with no Python installed.
REM
REM  Idempotent: skips download if python\python.exe already exists. Pass
REM  --force as the first arg to wipe and rebuild.
REM ============================================================================

setlocal
cd /d "%~dp0"

set "PYVER=3.12.7"
set "PYZIP=python-%PYVER%-embed-amd64.zip"
set "PYURL=https://www.python.org/ftp/python/%PYVER%/%PYZIP%"
set "GETPIP_URL=https://bootstrap.pypa.io/get-pip.py"

if /i "%1"=="--force" (
  echo Removing existing python\ folder...
  rmdir /s /q python 2>nul
)

if exist "python\python.exe" (
  echo python\python.exe already present. Use --force to rebuild.
  goto :install_packages
)

echo.
echo [1/4] Downloading embeddable Python %PYVER%...
curl -L -o "%PYZIP%" "%PYURL%"
if errorlevel 1 (
  echo ERROR: Download failed. Check internet connection and try again.
  exit /b 1
)

echo.
echo [2/4] Extracting to python\ ...
mkdir python 2>nul
tar -xf "%PYZIP%" -C python
if errorlevel 1 (
  echo ERROR: Extract failed.
  exit /b 1
)
del "%PYZIP%"

echo.
echo [3/4] Enabling site-packages in embeddable distribution...
REM Embeddable Python ships with python3XX._pth file that disables site.py and
REM thus prevents pip from working. We need to uncomment the "import site" line.
REM Find the ._pth file (its name depends on Python minor version).
for %%F in (python\python*._pth) do (
  echo   Patching %%F
  REM Read the file, replace "#import site" with "import site"
  powershell -NoProfile -Command "(Get-Content -Raw '%%F') -replace '#import site', 'import site' | Set-Content -NoNewline '%%F'"
)

:install_packages
echo.
echo [4/4] Bootstrapping pip and installing Flask + openpyxl...
if not exist "python\get-pip.py" (
  curl -L -o "python\get-pip.py" "%GETPIP_URL%"
  if errorlevel 1 (
    echo ERROR: get-pip.py download failed.
    exit /b 1
  )
)
python\python.exe python\get-pip.py --no-warn-script-location
if errorlevel 1 (
  echo ERROR: pip bootstrap failed.
  exit /b 1
)
python\python.exe -m pip install --no-warn-script-location Flask openpyxl
if errorlevel 1 (
  echo ERROR: package install failed.
  exit /b 1
)

echo.
echo ============================================================
echo Bundle ready. Next steps:
echo   1. (optional) Test by running: run.bat
echo   2. ZIP the entire "valve-selector" folder
echo   3. Distribute the ZIP. Users extract and double-click run.bat.
echo ============================================================
endlocal
