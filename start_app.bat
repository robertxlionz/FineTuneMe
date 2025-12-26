@echo off
SETLOCAL EnableDelayedExpansion

echo ===================================================
echo   FineTuneMe V2.0 - Universal Launcher
echo ===================================================
echo.

REM --- INTERACTIVE MODE SELECTION ---
echo Select Deployment Mode:
echo.
echo [1] Cloud Only (Fast, No GPU Required)
echo     - Lightweight installation
echo     - Use Groq, OpenAI, or Anthropic APIs
echo     - No local AI processing
echo.
echo [2] Local AI (GPU-Powered, Heavy Setup)
echo     - Full installation with PyTorch
echo     - Run Ollama locally + Cloud providers
echo     - Requires NVIDIA GPU
echo.

set /p MODE_CHOICE="Enter your choice (1 or 2): "

if "%MODE_CHOICE%"=="1" goto CLOUD_MODE
if "%MODE_CHOICE%"=="2" goto LOCAL_MODE

echo.
echo [ERROR] Invalid choice. Please enter 1 or 2.
pause
exit /b

:CLOUD_MODE
echo.
echo [MODE] Cloud Only selected
set FTM_DEPLOYMENT_MODE=cloud
set INSTALLER_SCRIPT=install.bat
goto CHECK_ENV

:LOCAL_MODE
echo.
echo [MODE] Local AI selected
set FTM_DEPLOYMENT_MODE=local
REM install_gpu.bat will be run after activation
goto CHECK_ENV

:CHECK_ENV

echo.

REM --- AUTO-INSTALLER CHECK ---
if not exist ".venv\Scripts\activate.bat" (
    echo [FIRST RUN DETECTED]
    echo.
    echo System environment is missing. Initializing auto-setup...
    echo.
    call scripts\install.bat
    if %errorlevel% neq 0 (
        echo [ERROR] Installation failed.
        pause
        exit /b
    )
    echo.
    echo [SETUP COMPLETE] Starting application...
    echo.
)

REM --- LAUNCH APPLICATION (Single Window) ---
echo [INFO] Activating Python environment...
call .venv\Scripts\activate.bat

REM --- LOCAL MODE GPU CHECK ---
if not "%FTM_DEPLOYMENT_MODE%"=="local" goto SKIP_GPU

echo.
echo [INFO] Verifying Local AI Environment (GPU/Torch)...
call scripts\install_gpu.bat
if %errorlevel% neq 0 (
    echo [WARNING] GPU Setup returned warnings. Check output above.
)

:SKIP_GPU

echo [INFO] Launching FineTuneMe in %FTM_DEPLOYMENT_MODE% mode...
echo.
echo - Frontend: http://localhost:3000
echo - Backend API: http://localhost:8000
echo.
echo Press CTRL+C to stop servers.
echo.

cd ui
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    call npm install --legacy-peer-deps
)

REM Execute directly in the same window
call npm run dev
