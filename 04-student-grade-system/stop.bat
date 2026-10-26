@echo off
setlocal

taskkill /FI "WINDOWTITLE eq SGS-Backend*" /T /F >nul 2>&1

set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080" ^| findstr "LISTENING"') do (
    set FOUND=1
    taskkill /PID %%a /T /F >nul 2>&1
)

if %FOUND% EQU 0 (
    echo Service already stopped.
) else (
    echo Service stopped.
)

endlocal
