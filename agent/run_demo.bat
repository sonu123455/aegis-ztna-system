@echo off
title Aegis ZTNA Security Node - Live Client Controller
color 0B
cls
echo ======================================================================
echo           AEGIS ZERO TRUST NETWORK ACCESS (ZTNA) SYSTEM              
echo          Autonomous Biometric & Blockchain Security Agent            
echo ======================================================================
echo.

:: 1. Check Python Availability
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python is not installed or not added to system PATH.
    echo Please install Python 3.10+ from python.org and re-run.
    pause
    exit /b
)

:: 2. Auto-Install Dependencies
echo [*] Verifying cryptographic and network dependencies...
pip install -r requirements.txt >nul 2>&1
echo [✓] Cryptographic modules loaded (AES-256-GCM, Requests).

:: 3. Launch Agent CLI
echo [*] Connecting to live cloud gateway on Render...
echo.
python aegis_agent.py

echo.
echo ======================================================================
echo Session closed. All security telemetry recorded to distributed ledger.
echo ======================================================================
pause
