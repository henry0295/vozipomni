# Script para subir cambios de migración PJSIP a Git
# VoziPOmni - Configuración PJSIP
# PowerShell Version

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  SUBIENDO CAMBIOS PJSIP A GIT - VoziPOmni" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "❌ Error: No estás en el directorio raíz del proyecto" -ForegroundColor Red
    Write-Host "   Ejecuta: cd 'c:\Users\PT\OneDrive - VOZIP COLOMBIA\Documentos\GitHub\vozipomni'" -ForegroundColor Yellow
    exit 1
}

# Ver estado actual
Write-Host "📋 Estado actual del repositorio:`n" -ForegroundColor Green
git status
Write-Host ""

# Agregar archivos modificados y nuevos
Write-Host "➕ Agregando archivos al staging...`n" -ForegroundColor Green

# Archivos de configuración corregidos
git add docker/asterisk/configs/asterisk.conf

# Archivos Python actualizados
git add backend/apps/telephony/views.py
git add backend/apps/telephony/asterisk_config.py

# Scripts de ayuda
git add asterisk-docker.sh
git add check-pjsip.sh
git add asterisk-helper.ps1
git add test_asterisk_connection.py
git add push-pjsip-changes.sh
git add push-pjsip-changes.ps1

# Documentación
git add DIAGNOSTICO_ASTERISK.md
git add SOLUCION_ASTERISK_CLI.md
git add GUIA_PJSIP.md
git add RESUMEN_PJSIP.md

# Archivo de entorno
git add .env

Write-Host "✅ Archivos agregados`n" -ForegroundColor Green

# Ver qué se va a commitear
Write-Host "📦 Archivos que serán commiteados:`n" -ForegroundColor Green
git status --short
Write-Host ""

# Confirmar
$continue = Read-Host "¿Deseas continuar con el commit? (s/n)"

if ($continue -ne "s" -and $continue -ne "S" -and $continue -ne "y" -and $continue -ne "Y") {
    Write-Host "`n❌ Operación cancelada`n" -ForegroundColor Red
    exit 0
}

# Crear commit
Write-Host "`n📝 Creando commit..." -ForegroundColor Green

$commitMessage = @"
fix: Migración completa a PJSIP y corrección de acceso CLI Asterisk

- Fix: Corregido error 'Unable to connect to remote asterisk'
  * Cambiado alwaysfork=no y nofork=yes en asterisk.conf
  * Ahora se puede acceder con: docker compose exec asterisk asterisk -r

- Migración SIP → PJSIP:
  * Actualizado views.py para recargar res_pjsip.so en lugar de chan_sip.so
  * Corregido asterisk_config.py para usar Dial(PJSIP/...) en lugar de Dial(SIP/...)
  * Sistema ahora 100% compatible con PJSIP (Asterisk 21)

- Scripts de ayuda añadidos:
  * asterisk-docker.sh - Gestión completa del contenedor Asterisk
  * check-pjsip.sh - Verificación y diagnóstico de PJSIP
  * asterisk-helper.ps1 - Helper para Windows PowerShell
  * test_asterisk_connection.py - Prueba de conexión AMI
  * push-pjsip-changes.sh/ps1 - Scripts para subir cambios a Git

- Documentación completa:
  * DIAGNOSTICO_ASTERISK.md - Guía de diagnóstico general
  * SOLUCION_ASTERISK_CLI.md - Solución específica error CLI
  * GUIA_PJSIP.md - Guía completa de uso de PJSIP
  * RESUMEN_PJSIP.md - Resumen ejecutivo de cambios

- Configuración:
  * Agregado archivo .env para configuración de entorno

Cambios probados y funcionando en Asterisk 21 con Docker.
chan_sip NO está disponible (deprecado) - usar PJSIP.
"@

git commit -m $commitMessage

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Commit creado exitosamente`n" -ForegroundColor Green
    
    # Mostrar el commit
    Write-Host "📄 Detalles del commit:" -ForegroundColor Green
    git log -1 --stat
    Write-Host ""
    
    # Preguntar si desea hacer push
    $doPush = Read-Host "¿Deseas hacer push al repositorio remoto? (s/n)"
    
    if ($doPush -eq "s" -or $doPush -eq "S" -or $doPush -eq "y" -or $doPush -eq "Y") {
        Write-Host "`n🚀 Haciendo push..." -ForegroundColor Green
        
        # Obtener rama actual
        $branch = git branch --show-current
        
        # Hacer push
        git push origin $branch
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n================================================================" -ForegroundColor Green
            Write-Host "  ✅ CAMBIOS SUBIDOS EXITOSAMENTE A GIT" -ForegroundColor Green
            Write-Host "================================================================`n" -ForegroundColor Green
            Write-Host "Rama: $branch" -ForegroundColor White
            Write-Host "`n📋 Siguiente paso en el servidor:" -ForegroundColor Cyan
            Write-Host "   cd /opt/vozipomni" -ForegroundColor Yellow
            Write-Host "   git pull origin $branch" -ForegroundColor Yellow
            Write-Host "   docker compose restart asterisk`n" -ForegroundColor Yellow
        } else {
            Write-Host "`n❌ Error al hacer push" -ForegroundColor Red
            Write-Host "   Verifica tu conexión y permisos del repositorio`n" -ForegroundColor Yellow
        }
    } else {
        Write-Host "`nℹ️  Commit creado pero no se hizo push" -ForegroundColor Blue
        Write-Host "   Para hacer push manualmente:" -ForegroundColor Gray
        Write-Host "   git push origin $branch`n" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n❌ Error al crear commit`n" -ForegroundColor Red
    exit 1
}
