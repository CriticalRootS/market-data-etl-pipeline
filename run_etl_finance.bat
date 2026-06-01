@echo off
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "LOG_DIR=%SCRIPT_DIR%logs"

:: ─────────── Load .env if it exists ──────────────────────────────
if exist "%SCRIPT_DIR%.env" (
    for /f usebackq tokens^=1^,2^ delims^== %%A in ("%SCRIPT_DIR%.env") do (
        echo %%A | findstr /b "#" >nul
        if errorlevel 1 (
            for /f "tokens=1 delims==" %%K in ("%%A") do (
                set "line=%%B"
                set "line=!line:"=!"
                set "%%K=!line!"
            )
        )
    )
)

:: ────────────────── Defaults (override from .env if not set) ──────────
if not defined TICKERS              set "TICKERS=BTC-USD"
if not defined PERIOD               set "PERIOD=1mo"
if not defined INTERVAL              set "INTERVAL=1d"
if not defined POSTGRES_USER         set "POSTGRES_USER=myuser"
if not defined POSTGRES_PASSWORD     set "POSTGRES_PASSWORD=postgres_password"
if not defined POSTGRES_HOST          set "POSTGRES_HOST=127.0.0.1"
if not defined POSTGRES_PORT          set "POSTGRES_PORT=5432"
if not defined POSTGRES_DB            set "POSTGRES_DB=mydatabase"

:: ──────── Logging ───────────────────────────────────────────────────
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "LOG_STAMP=%%i"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\etl_finance_%LOG_STAMP%.log"

:: ─────────────── Docker Compose ────────────────────────────────────────────
echo [%DATE% %TIME%] Stopping existing containers... >> "%LOG_FILE%" 2>&1
docker compose down >> "%LOG_FILE%" 2>&1

echo [%DATE% %TIME%] Starting Docker Compose... >> "%LOG_FILE%" 2>&1
docker compose up -d >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%DATE% %TIME%] Docker Compose failed. >> "%LOG_FILE%" 2>&1
    exit /b 1
)

:: ──────────────────────────── ETL ─────────────────────────────────────────
echo [%DATE% %TIME%] Starting ETL for %TICKERS%... >> "%LOG_FILE%" 2>&1
python "%SCRIPT_DIR%etl_finance.py" --tickers %TICKERS% --period %PERIOD% --interval %INTERVAL% >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%DATE% %TIME%] ETL failed. >> "%LOG_FILE%" 2>&1
    exit /b 1
)

echo [%DATE% %TIME%] ETL completed successfully. >> "%LOG_FILE%" 2>&1
endlocal
