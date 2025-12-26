@echo off
SETLOCAL EnableDelayedExpansion

echo ========================================
echo FineTuneMe Local V2.0 - Quick Install
echo ========================================
echo.

REM --- PYTHON DETECTION LOGIC ---
set PYTHON_CMD=python

python --version >nul 2>&1
if %errorlevel% equ 0 goto :FOUND_PYTHON

echo [INFO] 'python' command not found. Checking 'py' launcher...
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :FOUND_PYTHON
)

echo [INFO] 'py' command not found. Checking 'python3'...
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    goto :FOUND_PYTHON
)

echo [ERROR] Python is not installed or not in PATH.
echo Please install Python 3.10+ from python.org and check "Add to PATH".
pause
exit /b 1

:FOUND_PYTHON
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version') do set PYTHON_VER_STR=%%i
echo [OK] Using %PYTHON_VER_STR% (%PYTHON_CMD%)
echo.

REM Create venv
echo [STEP 1/3] Creating lightweight virtual environment...
if exist ".venv" rmdir /s /q .venv
%PYTHON_CMD% -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create venv
    pause
    exit /b 1
)

REM Activate
call .venv\Scripts\activate.bat

REM Upgrade pip
echo [STEP 2/3] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install Core Dependencies (No PyTorch)
echo [STEP 3/3] Installing core services...
pip install -e . --quiet

echo.
echo ========================================
echo [SUCCESS] Core System Ready!
echo ========================================
echo.
echo You can now run the app in "Cloud Mode" (Groq/OpenAI).
echo.
exit /b 0
