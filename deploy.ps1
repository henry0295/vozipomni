# Script para SUBIR cambios desde Windows y ACTUALIZAR servidor
# Ejecutar en Windows (VS Code)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  DEPLOYMENT VoziPOmni - Paso 1/2" -ForegroundColor Cyan
Write-Host "  Subiendo cambios a Git" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "❌ Error: No estás en el directorio raíz del proyecto" -ForegroundColor Red
    exit 1
}

# Ver estado actual
Write-Host "📋 Estado actual del repositorio:`n" -ForegroundColor Yellow
git status

Write-Host "`n📦 Archivos modificados:" -ForegroundColor Yellow
git diff --name-only
git ls-files --others --exclude-standard

Write-Host "`n" -ForegroundColor Yellow
$continue = Read-Host "¿Deseas continuar con el deployment? (s/n)"

if ($continue -ne "s" -and $continue -ne "S") {
    Write-Host "`n❌ Deployment cancelado`n" -ForegroundColor Red
    exit 0
}

# Agregar todos los cambios
Write-Host "`n➕ Agregando archivos..." -ForegroundColor Green
git add .

# Crear commit
Write-Host "`n📝 Creando commit..." -ForegroundColor Green
$commitMsg = Read-Host "Mensaje del commit (Enter para usar mensaje por defecto)"

if ([string]::IsNullOrWhiteSpace($commitMsg)) {
    $commitMsg = "feat: Agregar columna de estado de registro en troncales SIP"
}

git commit -m $commitMsg

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n⚠️  No hay cambios para commitear o error en commit" -ForegroundColor Yellow
    Write-Host "Continuando con push..." -ForegroundColor Yellow
}

# Hacer push
Write-Host "`n🚀 Subiendo a GitHub..." -ForegroundColor Green
$branch = git branch --show-current
git push origin $branch

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n================================================================" -ForegroundColor Green
    Write-Host "  ✅ PASO 1 COMPLETADO - Cambios subidos a Git" -ForegroundColor Green
    Write-Host "================================================================`n" -ForegroundColor Green
    
    Write-Host "📋 PASO 2: Actualizar en el servidor`n" -ForegroundColor Cyan
    Write-Host "Ejecuta estos comandos en el servidor Linux:`n" -ForegroundColor White
    Write-Host "   ssh usuario@IP_SERVIDOR" -ForegroundColor Yellow
    Write-Host "   cd /opt/vozipomni" -ForegroundColor Yellow
    Write-Host "   chmod +x deploy-server.sh" -ForegroundColor Yellow
    Write-Host "   ./deploy-server.sh`n" -ForegroundColor Yellow
    
    Write-Host "O manualmente:" -ForegroundColor White
    Write-Host "   ssh usuario@IP_SERVIDOR" -ForegroundColor Yellow
    Write-Host "   cd /opt/vozipomni" -ForegroundColor Yellow
    Write-Host "   git pull origin $branch" -ForegroundColor Yellow
    Write-Host "   docker compose restart backend celery_worker`n" -ForegroundColor Yellow
} else {
    Write-Host "`n❌ Error al hacer push" -ForegroundColor Red
    Write-Host "   Verifica tu conexión y permisos del repositorio`n" -ForegroundColor Yellow
}
