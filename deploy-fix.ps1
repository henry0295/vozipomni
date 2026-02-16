# Script de Deploy - Subir Correcciones al Repositorio
# Ejecutar desde: PowerShell en Windows

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  VoziPOmni - Deploy de Correcciones Críticas" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Cambiar al directorio del proyecto
$projectPath = "c:\Users\PT\OneDrive - VOZIP COLOMBIA\Documentos\GitHub\vozipomni"
Set-Location $projectPath

Write-Host "Directorio actual: $projectPath" -ForegroundColor Yellow
Write-Host ""

# Verificar estado de Git
Write-Host "Archivos modificados/nuevos:" -ForegroundColor Green
git status --short

Write-Host ""
Write-Host "Archivos que se van a commitear:" -ForegroundColor Green
Write-Host "  - backend/apps/agents/migrations/0001_initial.py" -ForegroundColor White
Write-Host "  - backend/apps/campaigns/migrations/0001_initial.py" -ForegroundColor White
Write-Host "  - backend/apps/contacts/migrations/0001_initial.py" -ForegroundColor White
Write-Host "  - backend/apps/queues/migrations/0001_initial.py" -ForegroundColor White
Write-Host "  - backend/apps/queues/migrations/0002_queuemember.py" -ForegroundColor White
Write-Host "  - backend/apps/telephony/migrations/0001_initial.py" -ForegroundColor White
Write-Host "  - frontend/nuxt.config.ts" -ForegroundColor White
Write-Host "  - DEPLOY_MIGRATIONS_FIX.md" -ForegroundColor White
Write-Host ""

# Pedir confirmación
$confirm = Read-Host "¿Desea continuar con el commit y push? (S/N)"

if ($confirm -ne "S" -and $confirm -ne "s") {
    Write-Host "Operación cancelada" -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "Agregando archivos al staging..." -ForegroundColor Yellow

# Agregar archivos específicos
git add backend/apps/agents/migrations/0001_initial.py
git add backend/apps/campaigns/migrations/0001_initial.py
git add backend/apps/contacts/migrations/0001_initial.py
git add backend/apps/queues/migrations/0001_initial.py
git add backend/apps/queues/migrations/0002_queuemember.py
git add backend/apps/telephony/migrations/0001_initial.py
git add frontend/nuxt.config.ts
git add DEPLOY_MIGRATIONS_FIX.md

Write-Host "Archivos agregados correctamente" -ForegroundColor Green
Write-Host ""

# Hacer commit
Write-Host "Creando commit..." -ForegroundColor Yellow
$commitMessage = @"
Fix: Add all missing initial migrations and fix Nuxt build

- Created initial migrations for: agents, campaigns, contacts, queues, telephony
- Added QueueMember migration (0002) for circular dependency resolution
- Fixed Nuxt prerender error by removing non-existent routes
- Added comprehensive deployment documentation
- Resolves: NodeNotFoundError in production deployments
- Resolves: Nuxt build failure due to missing sitemap/rss routes

This fix is critical for install.sh to work correctly on fresh installations.
"@

git commit -m $commitMessage

if ($LASTEXITCODE -eq 0) {
    Write-Host "Commit creado exitosamente" -ForegroundColor Green
} else {
    Write-Host "Error al crear commit" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Subiendo cambios al repositorio..." -ForegroundColor Yellow

# Push al repositorio
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "  ✅ DEPLOY EXITOSO" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Los cambios han sido subidos al repositorio." -ForegroundColor White
    Write-Host ""
    Write-Host "Próximos pasos en el servidor de producción:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. Conectarse al servidor:" -ForegroundColor White
    Write-Host "     ssh root@SERVIDOR_IP" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  2. Actualizar código:" -ForegroundColor White
    Write-Host "     cd /opt/vozipomni" -ForegroundColor Cyan
    Write-Host "     git pull origin main" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  3. Reconstruir frontend:" -ForegroundColor White
    Write-Host "     docker compose build --no-cache frontend" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  4. Reiniciar servicios:" -ForegroundColor White
    Write-Host "     docker compose down" -ForegroundColor Cyan
    Write-Host "     docker compose up -d" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  5. Verificar migraciones:" -ForegroundColor White
    Write-Host "     docker compose logs -f backend" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Ver documentación completa en:" -ForegroundColor Yellow
    Write-Host "  DEPLOY_MIGRATIONS_FIX.md" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "  ❌ ERROR AL HACER PUSH" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Posibles causas:" -ForegroundColor Yellow
    Write-Host "  - No tienes permisos de escritura en el repositorio" -ForegroundColor White
    Write-Host "  - No estás autenticado en GitHub" -ForegroundColor White
    Write-Host "  - Hay conflictos con el repositorio remoto" -ForegroundColor White
    Write-Host ""
    Write-Host "Intenta:" -ForegroundColor Yellow
    Write-Host "  1. Verificar autenticación: gh auth status" -ForegroundColor Cyan
    Write-Host "  2. Hacer pull primero: git pull origin main" -ForegroundColor Cyan
    Write-Host "  3. Resolver conflictos si los hay" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}
