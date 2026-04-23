@echo off
setlocal EnableExtensions

call :get_listen_pid 5173 FRONTEND_PID
if not defined FRONTEND_PID (
    echo Frontend is not running. Port 5173 is not listening.
    call :maybe_pause
    exit /b 0
)

taskkill /PID %FRONTEND_PID% /T /F >nul 2>nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Stop-Process -Id %FRONTEND_PID% -Force -ErrorAction SilentlyContinue" >nul 2>nul
timeout /t 1 >nul

call :get_listen_pid 5173 FRONTEND_PID
if defined FRONTEND_PID (
    echo Frontend stop failed. Port 5173 is still used by PID=%FRONTEND_PID%.
) else (
    echo Frontend stopped.
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
