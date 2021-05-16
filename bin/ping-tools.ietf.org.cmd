@echo off

ping tools.ietf.org -n 1
@echo [+] %date% %time%
if %errorlevel% neq 0 (
    timeout /t 300 1>nul 2>&1
    ping tools.ietf.org -n 1
    @echo [+] %date% %time%
    if %errorlevel% neq 0 (
        timeout /t 300 1>nul 2>&1
        ping tools.ietf.org -n 1
        @echo [+] %date% %time%
        if %errorlevel% neq 0 (
            timeout /t 300 1>nul 2>&1
            ping tools.ietf.org -n 1
            @echo [+] %date% %time%
        )
    )
)
