# Script para reiniciar frontend - VoziPOmni
# PowerShell Version

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  REINICIAR FRONTEND - VoziPOmni" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "frontend")) {
    Write-Host "❌ Error: No se encuentra el directorio 'frontend'" -ForegroundColor Red
    Write-Host "   Ejecuta desde el directorio raíz del proyecto" -ForegroundColor Yellow
    exit 1
}

# Detener procesos node si existen
Write-Host "1. Deteniendo servidor frontend..." -ForegroundColor Yellow
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# Limpiar caché de Vite
Write-Host "2. Limpiando caché de Vite..." -ForegroundColor Yellow
$viteCachePath = "frontend\node_modules\.vite"
if (Test-Path $viteCachePath) {
    Remove-Item -Recurse -Force $viteCachePath
    Write-Host "   ✓ Caché de Vite eliminado" -ForegroundColor Green
} else {
    Write-Host "   ℹ No hay caché de Vite para limpiar" -ForegroundColor Gray
}

# Limpiar dist si existe
$distPath = "frontend\dist"
if (Test-Path $distPath) {
    Remove-Item -Recurse -Force $distPath
    Write-Host "   ✓ Directorio dist eliminado" -ForegroundColor Green
}

Write-Host "`n3. Iniciando servidor de desarrollo..." -ForegroundColor Yellow
Write-Host "   Presiona Ctrl+C para detener`n" -ForegroundColor Gray

# Cambiar al directorio frontend
Set-Location frontend

# Iniciar servidor de desarrollo
npm run dev
