@echo off
setlocal EnableExtensions

cd /d "%~dp0"
set "SCRIPT_DIR=%cd%"
for %%I in ("%SCRIPT_DIR%\..") do set "ROOT_DIR=%%~fI"

set "RUNTIME_DIR=%SCRIPT_DIR%\runtime"
set "LOG_DIR=%SCRIPT_DIR%\logs"
set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"
set "BACKEND_DB=%RUNTIME_DIR%\backend_runtime.db"
set "BACKEND_LOG=%LOG_DIR%\backend.log"

if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%" >nul 2>nul
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>nul

if not exist "%PYTHON_EXE%" (
    echo Python executable not found:
    echo %PYTHON_EXE%
    echo Please make sure .venv exists in the project root.
    call :maybe_pause
    exit /b 1
)

call :get_listen_pid 8000 BACKEND_PID
if defined BACKEND_PID (
    echo Backend is already running on port 8000. PID=%BACKEND_PID%
    echo Run stop-backend.bat first if you want to restart it.
    call :maybe_pause
    exit /b 0
)

start "Graduate Design Backend" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& { $env:APP_DB_PATH = '%BACKEND_DB%'; Set-Location '%ROOT_DIR%'; & '%PYTHON_EXE%' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 *> '%BACKEND_LOG%' }"

call :wait_for_listen_pid 8000 BACKEND_PID 15

if defined BACKEND_PID (
    echo Backend started.
    echo URL: http://127.0.0.1:8000
    echo PID: %BACKEND_PID%
    echo Runtime DB: %BACKEND_DB%
    echo Log file: %BACKEND_LOG%
) else (
    echo Backend failed to start. Check the log file:
    echo %BACKEND_LOG%
)

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
