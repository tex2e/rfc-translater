@echo off

REM 接続が悪いときは5分待機してから再度pingを投げる

ping datatracker.ietf.org -n 1
@echo [+] %date% %time%
if %errorlevel% neq 0 (
    timeout /t 300 1>nul 2>&1
    ping datatracker.ietf.org -n 1
    @echo [+] %date% %time%
    if %errorlevel% neq 0 (
        timeout /t 300 1>nul 2>&1
        ping datatracker.ietf.org -n 1
        @echo [+] %date% %time%
        if %errorlevel% neq 0 (
            timeout /t 300 1>nul 2>&1
            ping datatracker.ietf.org -n 1
            @echo [+] %date% %time%
            if %errorlevel% neq 0 (
                exit %errorlevel%
            )
        )
    )
)
