@echo off
REM run_linkedin_post.bat
REM Posts ARIA research findings to LinkedIn.
REM Called by Windows Task Scheduler.

set PROJECT_DIR=C:\Users\V2Rst\aria
set SCRIPT=%PROJECT_DIR%\scripts\update_linkedin.py
set LOG=%PROJECT_DIR%\scripts\linkedin_post.log
set VENV_PY=%USERPROFILE%\aria\.venv\Scripts\python.exe

echo. >> "%LOG%"
echo ===== %DATE% %TIME% ===== >> "%LOG%"

set ARIA_DASHBOARD_URL=https://aria-agent.duckdns.org

if exist "%VENV_PY%" (
    echo Using aria venv >> "%LOG%"
    "%VENV_PY%" "%SCRIPT%" --post >> "%LOG%" 2>&1
) else (
    echo Using system Python >> "%LOG%"
    python "%SCRIPT%" --post >> "%LOG%" 2>&1
)

if %ERRORLEVEL% NEQ 0 (
    echo FAILED with exit code %ERRORLEVEL% >> "%LOG%"
) else (
    echo SUCCESS >> "%LOG%"
)
