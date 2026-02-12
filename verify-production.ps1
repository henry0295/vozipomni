#!/usr/bin/env pwsh
# Script de verificación de configuración para producción
# Ejecutar antes de desplegar: .\verify-production.ps1

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "   VozipOmni - Verificación de Configuración de Producción" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

$errorsFound = 0
$warningsFound = 0

# Función para verificar archivos
function Test-FileExists {
    param(
        [string]$Path,
        [string]$Description,
        [bool]$Critical = $true
    )
    
    if (Test-Path $Path) {
        Write-Host "[OK] $Description" -ForegroundColor Green
        return $true
    } else {
        if ($Critical) {
            Write-Host "[ERROR] $Description - Archivo no encontrado: $Path" -ForegroundColor Red
            $script:errorsFound++
        } else {
            Write-Host "[WARN] $Description - Archivo no encontrado: $Path" -ForegroundColor Yellow
            $script:warningsFound++
        }
        return $false
    }
}

# Función para verificar contenido de archivo
function Test-FileContent {
    param(
        [string]$Path,
        [string]$Pattern,
        [string]$Description,
        [bool]$ShouldExist = $true
    )
    
    if (Test-Path $Path) {
        $content = Get-Content $Path -Raw
        $found = $content -match $Pattern
        
        if ($ShouldExist -eq $found) {
            Write-Host "[OK] $Description" -ForegroundColor Green
            return $true
        } else {
            Write-Host "[ERROR] $Description" -ForegroundColor Red
            $script:errorsFound++
            return $false
        }
    } else {
        Write-Host "[ERROR] No se puede verificar '$Description' - Archivo no encontrado: $Path" -ForegroundColor Red
        $script:errorsFound++
        return $false
    }
}

Write-Host "1. Verificando archivos esenciales..." -ForegroundColor Yellow
Write-Host ""

Test-FileExists -Path ".env" -Description "Archivo .env principal"
Test-FileExists -Path "docker-compose.prod.yml" -Description "Docker Compose de producción"
Test-FileExists -Path "ssl/fullchain.pem" -Description "Certificado SSL" -Critical $false
Test-FileExists -Path "ssl/privkey.pem" -Description "Clave privada SSL" -Critical $false

Write-Host ""
Write-Host "2. Verificando configuración de seguridad..." -ForegroundColor Yellow
Write-Host ""

if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    
    # Verificar DEBUG
    if ($envContent -match "DEBUG\s*=\s*False") {
        Write-Host "[OK] DEBUG está en False (producción)" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] DEBUG debe estar en False para producción" -ForegroundColor Red
        $errorsFound++
    }
    
    # Verificar SECRET_KEY
    if ($envContent -match "SECRET_KEY\s*=\s*CHANGE") {
        Write-Host "[ERROR] SECRET_KEY no ha sido cambiada - CRÍTICO" -ForegroundColor Red
        $errorsFound++
    } else {
        Write-Host "[OK] SECRET_KEY ha sido configurada" -ForegroundColor Green
    }
    
    # Verificar CORS_ALLOW_ALL
    if ($envContent -match "CORS_ALLOW_ALL\s*=\s*False") {
        Write-Host "[OK] CORS_ALLOW_ALL está en False (seguro)" -ForegroundColor Green
    } else {
        Write-Host "[WARN] CORS_ALLOW_ALL debería estar en False para producción" -ForegroundColor Yellow
        $warningsFound++
    }
    
    # Verificar CORS_ORIGINS
    if ($envContent -match "CORS_ORIGINS\s*=\s*.+") {
        Write-Host "[OK] CORS_ORIGINS está configurado" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] CORS_ORIGINS debe estar configurado" -ForegroundColor Red
        $errorsFound++
    }
    
    # Verificar ALLOWED_HOSTS
    if ($envContent -match "ALLOWED_HOSTS\s*=\s*.+") {
        Write-Host "[OK] ALLOWED_HOSTS está configurado" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] ALLOWED_HOSTS debe estar configurado" -ForegroundColor Red
        $errorsFound++
    }
    
    # Verificar contraseñas por defecto
    if ($envContent -match "CHANGE_THIS") {
        Write-Host "[ERROR] Hay contraseñas sin cambiar (contienen 'CHANGE_THIS')" -ForegroundColor Red
        $errorsFound++
    } else {
        Write-Host "[OK] Las contraseñas parecen haber sido cambiadas" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "3. Verificando configuración del frontend..." -ForegroundColor Yellow
Write-Host ""

Test-FileContent -Path "frontend/nuxt.config.ts" -Pattern "serverBundle" -Description "Configuración de iconos serverBundle"
Test-FileContent -Path "frontend/middleware/auth.ts" -Pattern "loadFromStorage" -Description "Middleware de autenticación actualizado"

Write-Host ""
Write-Host "4. Verificando configuración del backend..." -ForegroundColor Yellow
Write-Host ""

Test-FileExists -Path "backend/apps/api/auth_serializers.py" -Description "Serializer personalizado de autenticación"
Test-FileContent -Path "backend/apps/api/views.py" -Pattern "CustomTokenObtainPairView" -Description "Vista personalizada de login"
Test-FileContent -Path "backend/config/settings.py" -Pattern "CORS_ORIGIN_ALLOW_ALL.*default=False" -Description "CORS seguro por defecto"

Write-Host ""
Write-Host "5. Verificando estructura de directorios..." -ForegroundColor Yellow
Write-Host ""

$directories = @(
    "logs",
    "ssl",
    "backend/static",
    "backend/media"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "[CREATED] Directorio creado: $dir" -ForegroundColor Blue
    } else {
        Write-Host "[OK] Directorio existe: $dir" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "   RESUMEN DE VERIFICACIÓN" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

if ($errorsFound -eq 0 -and $warningsFound -eq 0) {
    Write-Host "✅ ÉXITO: No se encontraron errores ni advertencias" -ForegroundColor Green
    Write-Host ""
    Write-Host "El sistema está listo para producción." -ForegroundColor Green
    Write-Host ""
    Write-Host "Próximos pasos:" -ForegroundColor Cyan
    Write-Host "  1. docker-compose -f docker-compose.prod.yml build" -ForegroundColor White
    Write-Host "  2. docker-compose -f docker-compose.prod.yml up -d" -ForegroundColor White
    Write-Host "  3. docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate" -ForegroundColor White
    Write-Host "  4. docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser" -ForegroundColor White
    Write-Host ""
    exit 0
} else {
    Write-Host "⚠️  ADVERTENCIA: Se encontraron problemas" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Errores críticos: $errorsFound" -ForegroundColor Red
    Write-Host "Advertencias: $warningsFound" -ForegroundColor Yellow
    Write-Host ""
    
    if ($errorsFound -gt 0) {
        Write-Host "❌ NO DESPLEGAR: Hay errores críticos que deben corregirse" -ForegroundColor Red
        Write-Host ""
        Write-Host "Pasos recomendados:" -ForegroundColor Cyan
        Write-Host "  1. Revisar los errores anteriores" -ForegroundColor White
        Write-Host "  2. Consultar PRODUCCION_CONFIG.md para más información" -ForegroundColor White
        Write-Host "  3. Corregir los problemas y ejecutar este script nuevamente" -ForegroundColor White
        Write-Host ""
        exit 1
    } else {
        Write-Host "⚠️  PRECAUCIÓN: Hay advertencias pero el sistema puede desplegarse" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Se recomienda revisar las advertencias antes de continuar." -ForegroundColor Yellow
        Write-Host ""
        exit 0
    }
}
