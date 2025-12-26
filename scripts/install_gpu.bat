@echo off
SETLOCAL EnableDelayedExpansion

echo ========================================
echo FineTuneMe - GPU Optimization Setup
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
pause
exit /b 1

:FOUND_PYTHON
echo [OK] Using %PYTHON_CMD% for GPU setup...

REM Check if venv exists
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

echo [STEP 1/2] Detecting GPU hardware...
python scripts\check_pre_install.py
if %errorlevel% equ 99 (
    echo [INFO] Installation aborted by user.
    exit /b
)
SET HARDWARE_TIER=%errorlevel%

REM Read hardware status from JSON file
SET PYTORCH_MODE=stable
SET GPU_NAME=Unknown

if exist hardware_status.json (
    for /f "delims=" %%i in ('powershell -Command "Get-Content hardware_status.json | ConvertFrom-Json | Select-Object -ExpandProperty pytorch_mode"') do set PYTORCH_MODE=%%i
    for /f "delims=" %%i in ('powershell -Command "Get-Content hardware_status.json | ConvertFrom-Json | Select-Object -ExpandProperty gpu_name"') do set GPU_NAME=%%i
)

echo.
echo [INFO] Detected GPU: %GPU_NAME%
echo [INFO] PyTorch Mode: %PYTORCH_MODE%
echo.

echo [STEP 2/2] Installing PyTorch...
echo.

if "%PYTORCH_MODE%"=="nightly" goto INSTALL_NIGHTLY
if "%PYTORCH_MODE%"=="stable" goto INSTALL_STABLE
goto INSTALL_CPU

:INSTALL_NIGHTLY
echo ⚡ Installing PyTorch NIGHTLY for Blackwell GPU...
echo This may take several minutes...
pip install torch --pre --index-url https://download.pytorch.org/whl/nightly/cu124
goto SETUP_DONE

:INSTALL_STABLE
echo ✅ Installing PyTorch STABLE for modern NVIDIA GPU...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
goto SETUP_DONE

:INSTALL_CPU
echo ⚠️  Installing PyTorch CPU-ONLY (no GPU support)...
pip install torch torchvision torchaudio
goto SETUP_DONE

:SETUP_DONE

echo.
echo [SUCCESS] GPU Setup Complete!
echo You can now use Local Ollama inference.

