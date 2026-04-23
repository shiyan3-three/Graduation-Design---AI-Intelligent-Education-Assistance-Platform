@echo off
setlocal EnableExtensions

call :get_listen_pid 8000 BACKEND_PID
if not defined BACKEND_PID (
    echo Backend is not running. Port 8000 is not listening.
    call :maybe_pause
    exit /b 0
)

taskkill /PID %BACKEND_PID% /T /F >nul 2>nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Stop-Process -Id %BACKEND_PID% -Force -ErrorAction SilentlyContinue" >nul 2>nul
timeout /t 1 >nul

call :get_listen_pid 8000 BACKEND_PID
if defined BACKEND_PID (
    echo Backend stop failed. Port 8000 is still used by PID=%BACKEND_PID%.
) else (
    echo Backend stopped.
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

:maybe_pause
if /I "%NO_PAUSE%"=="1" exit /b 0
pause
exit /b 0
