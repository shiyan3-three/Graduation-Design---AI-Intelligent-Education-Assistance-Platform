@echo off
setlocal EnableExtensions

cd /d "%~dp0"
set "SCRIPT_DIR=%cd%"
for %%I in ("%SCRIPT_DIR%\..") do set "ROOT_DIR=%%~fI"

set "LOG_DIR=%SCRIPT_DIR%\logs"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "FRONTEND_LOG=%LOG_DIR%\frontend.log"
set "NPM_EXE="
set "RUNNER_SCRIPT=%SCRIPT_DIR%\run-frontend-dev.bat"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>nul

if not exist "%FRONTEND_DIR%\package.json" (
    echo Frontend package.json not found:
    echo %FRONTEND_DIR%\package.json
    call :maybe_pause
    exit /b 1
)

for /f "delims=" %%I in ('where.exe npm.cmd 2^>nul') do (
    if not defined NPM_EXE set "NPM_EXE=%%I"
)

if not defined NPM_EXE (
    for /f "delims=" %%I in ('where.exe npm 2^>nul') do (
        if not defined NPM_EXE set "NPM_EXE=%%I"
    )
)

if not defined NPM_EXE (
    echo npm was not found in PATH.
    echo Please make sure npm -v works in your terminal.
    call :maybe_pause
    exit /b 1
)

call :get_listen_pid 5173 FRONTEND_PID
if defined FRONTEND_PID (
    echo Frontend is already running on port 5173. PID=%FRONTEND_PID%
    echo Run stop-frontend.bat first if you want to restart it.
    call :maybe_pause
    exit /b 0
)

(
    echo @echo off
    echo cd /d "%FRONTEND_DIR%"
    echo call "%NPM_EXE%" run dev -- --host 127.0.0.1 ^> "%FRONTEND_LOG%" 2^>^&1
) > "%RUNNER_SCRIPT%"

start "Graduate Design Frontend" /min "%RUNNER_SCRIPT%"

call :wait_for_listen_pid 5173 FRONTEND_PID 15

if defined FRONTEND_PID (
    echo Frontend started.
    echo URL: http://127.0.0.1:5173
    echo PID: %FRONTEND_PID%
    echo Log file: %FRONTEND_LOG%
) else (
    echo Frontend failed to start. Check the log file:
    echo %FRONTEND_LOG%
)

if exist "%RUNNER_SCRIPT%" del "%RUNNER_SCRIPT%" >nul 2>nul

call :maybe_pause
exit /b 0

:get_listen_pid
setlocal
set "PORT=%~1"
set "PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    set "PID=%%P"
    goto :done
)
:done
endlocal & set "%~2=%PID%"
exit /b 0

:wait_for_listen_pid
setlocal
set "PORT=%~1"
set "PID="
set "MAX_ATTEMPTS=%~3"
if not defined MAX_ATTEMPTS set "MAX_ATTEMPTS=10"
set /a ATTEMPT=0
:wait_loop
call :get_listen_pid %PORT% PID
if defined PID goto :wait_done
set /a ATTEMPT+=1
if %ATTEMPT% GEQ %MAX_ATTEMPTS% goto :wait_done
timeout /t 1 >nul
goto :wait_loop
:wait_done
endlocal & set "%~2=%PID%"
exit /b 0

:maybe_pause
if /I "%NO_PAUSE%"=="1" exit /b 0
pause
exit /b 0
