@echo off
setlocal
cd /d "%~dp0"

set "JDK_HOME="
for /d %%D in ("%~dp0env\jdk\jdk-*") do set "JDK_HOME=%%D"

if not defined JDK_HOME goto NOJDK
set "JAVA=%JDK_HOME%\bin\java.exe"
set "JAR=%~dp0backend\target\student-grade-system-1.0.0.jar"
if not exist "%JAR%" goto NOJAR

if not exist "%~dp0tmp" mkdir "%~dp0tmp"

echo.
echo   Starting backend service...
echo.

REM Launch detached: the service keeps running even if this window is closed
start "SGS-Backend" /min "%JAVA%" -Djava.io.tmpdir="%~dp0tmp" -jar "%JAR%"

set /a N=0
:WAIT
timeout /t 2 /nobreak >nul
set /a N+=1
powershell -NoProfile -Command "try{(Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://localhost:8080/api/auth/login).StatusCode}catch{exit 1}" >nul 2>&1
if %ERRORLEVEL% EQU 0 goto OK
if %N% LSS 30 goto WAIT
goto TIMEOUT

:OK
start "" "http://localhost:8080"
echo   ============================================
echo    OK  -  system is running
echo   ============================================
echo.
echo    URL:      http://localhost:8080
echo    Database: http://localhost:8080/h2-console
echo               (JDBC: jdbc:h2:mem:sgs  user: sa  pwd: empty)
echo.
echo    Accounts (password 123456):
echo      admin     administrator
echo      teacher1  teacher
echo      student1  student
echo.
echo    The service window is minimized as "SGS-Backend".
echo    Do NOT close it while using the system.
echo    To stop: run stop.bat
echo.
pause
goto EOF

:NOJDK
echo [ERROR] JDK not found in env\jdk
pause
goto EOF

:NOJAR
echo [ERROR] JAR not found:
echo   %JAR%
pause
goto EOF

:TIMEOUT
echo.
echo [ERROR] Startup timeout after 60 seconds.
echo   1. Port 8080 may be occupied - run stop.bat first
echo   2. Check the SGS-Backend window for errors
echo.
pause
goto EOF

:EOF
endlocal
