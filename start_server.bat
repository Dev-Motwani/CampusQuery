@echo off
title CampusQuery - Hosting Server
echo =================================================================
echo  CampusQuery - Starting Application Server (Front-End + Backend + DB)
echo =================================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run: python -m venv .venv
    pause
    exit /b 1
)

echo [INFO] Starting CampusQuery Server on all interfaces (0.0.0.0:5000)...
echo [INFO] Access locally:    http://localhost:5000 or http://127.0.0.1:5000
echo [INFO] Demo Admin Login:  admin@campusqueri.edu / Admin@123
echo [INFO] Demo Student Login: student@campusqueri.edu / Student@123
echo -----------------------------------------------------------------
.venv\Scripts\python.exe run.py
pause
