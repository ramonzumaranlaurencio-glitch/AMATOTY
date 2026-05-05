# ─────────────────────────────────────────────────────────────
#  start_safepay.ps1
#  Arranca el microservicio Trujillo SafePay PRO en puerto 5001
#  Ejecutar desde la raíz del proyecto:
#    .\start_safepay.ps1
# ─────────────────────────────────────────────────────────────

$ROOT   = $PSScriptRoot
$VENV   = Join-Path $ROOT ".venv"
$PY     = Join-Path $VENV "Scripts\python.exe"
$APP    = Join-Path $ROOT "safepay\app.py"
$REQ    = Join-Path $ROOT "safepay\requirements.txt"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   Trujillo SafePay PRO  |  Puerto 5001     " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Verificar/crear entorno virtual
if (-not (Test-Path $PY)) {
    Write-Host "[1/3] Creando entorno virtual..." -ForegroundColor Yellow
    python -m venv $VENV
}

# Instalar dependencias de SafePay
Write-Host "[2/3] Instalando dependencias de SafePay..." -ForegroundColor Yellow
& $PY -m pip install --quiet -r $REQ

# Arrancar SafePay
Write-Host "[3/3] Iniciando SafePay en http://127.0.0.1:5001 ..." -ForegroundColor Green
Write-Host "      Presiona Ctrl+C para detener." -ForegroundColor Gray
Write-Host ""
& $PY $APP
