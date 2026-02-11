# ============================================================================
# Script de Deploy Automatizado - Frontend Nuxt 3 (PowerShell)
# VozipOmni Contact Center
# ============================================================================

param(
    [switch]$SkipBackup,
    [switch]$SkipTests,
    [switch]$Force
)

# Configuración
$ErrorActionPreference = "Stop"
$VerbosePreference = "Continue"

# Funciones de utilidad
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Banner
Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " VozipOmni - Deploy Frontend Nuxt 3" -ForegroundColor Cyan
Write-Host " $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "docker-compose.yml")) {
    Write-Error-Custom "No se encontró docker-compose.yml"
    Write-Error-Custom "Por favor ejecuta este script desde el directorio raíz del proyecto"
    exit 1
}

# Paso 1: Backup
if (-not $SkipBackup) {
    Write-Info "Paso 1/10: Creando backup..."
    
    $BackupDate = Get-Date -Format "yyyyMMdd-HHmmss"
    
    # Backup de imagen Docker
    Write-Info "Creando backup de imagen Docker..."
    $BackupTag = "vozipomni-frontend:backup-$BackupDate"
    try {
        docker commit vozipomni-frontend $BackupTag 2>$null
        Write-Success "Backup de imagen creado: $BackupTag"
    }
    catch {
        Write-Warning "Contenedor frontend no encontrado, saltando backup de imagen"
    }
    
    # Backup de archivos
    Write-Info "Creando backup de archivos..."
    if (Test-Path "frontend") {
        $BackupDir = "frontend.backup.$BackupDate"
        Copy-Item -Path "frontend" -Destination $BackupDir -Recurse
        Write-Success "Backup de archivos creado: $BackupDir"
    }
    
    # Backup de docker-compose.yml
    if (Test-Path "docker-compose.yml") {
        Copy-Item "docker-compose.yml" "docker-compose.yml.backup"
        Write-Success "Backup de docker-compose.yml creado"
    }
}
else {
    Write-Warning "Saltando creación de backups (parámetro -SkipBackup)"
}

# Paso 2: Actualizar código
Write-Info "Paso 2/10: Actualizando código desde Git..."
try {
    git fetch origin
    git pull origin main
}
catch {
    try {
        git pull origin master
    }
    catch {
        Write-Warning "No se pudo hacer pull, continuando..."
    }
}

# Paso 3: Verificar archivos
Write-Info "Paso 3/10: Verificando archivos de Nuxt 3..."
if (-not (Test-Path "frontend/nuxt.config.ts")) {
    Write-Error-Custom "No se encontró frontend/nuxt.config.ts"
    Write-Error-Custom "Asegúrate de que el nuevo frontend está en el repositorio"
    exit 1
}
Write-Success "Archivos de Nuxt 3 encontrados"

# Paso 4: Configurar variables de entorno
Write-Info "Paso 4/10: Configurando variables de entorno..."
if (-not (Test-Path "frontend/.env")) {
    Write-Warning "No se encontró frontend/.env"
    $CreateEnv = Read-Host "¿Deseas crear uno desde .env.example? (s/n)"
    if ($CreateEnv -eq "s" -or $CreateEnv -eq "S") {
        if (Test-Path "frontend/.env.example") {
            Copy-Item "frontend/.env.example" "frontend/.env"
            Write-Info "Archivo .env creado. Por favor edítalo con tus valores:"
            Write-Info "notepad frontend\.env"
            Read-Host "Presiona Enter cuando hayas configurado el .env"
        }
    }
}
else {
    Write-Success "Archivo .env encontrado"
}

# Paso 5: Detener servicios
Write-Info "Paso 5/10: Deteniendo servicios..."
try {
    docker-compose stop frontend
    Write-Success "Frontend detenido"
}
catch {
    Write-Warning "No se pudo detener frontend"
}

# Paso 6: Construir nueva imagen
Write-Info "Paso 6/10: Construyendo nueva imagen del frontend..."
Write-Info "Esto puede tomar varios minutos..."

try {
    docker-compose build --no-cache frontend
    Write-Success "Imagen construida exitosamente"
}
catch {
    Write-Error-Custom "Error al construir la imagen"
    Write-Error-Custom "Revisa los logs arriba para más detalles"
    exit 1
}

# Paso 7: Iniciar servicios
Write-Info "Paso 7/10: Iniciando servicios..."
try {
    docker-compose up -d frontend
    Write-Success "Frontend iniciado"
}
catch {
    Write-Error-Custom "Error al iniciar frontend"
    exit 1
}

# Esperar a que el contenedor esté listo
Write-Info "Esperando a que el frontend esté listo..."
Start-Sleep -Seconds 10

# Paso 8: Verificar estado
Write-Info "Paso 8/10: Verificando estado de contenedores..."
docker-compose ps

# Paso 9: Verificar logs
Write-Info "Paso 9/10: Verificando logs del frontend..."
docker-compose logs --tail=50 frontend

# Paso 10: Pruebas de conectividad
if (-not $SkipTests) {
    Write-Info "Paso 10/10: Realizando pruebas de conectividad..."
    
    # Verificar frontend
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Success "Frontend responde en http://localhost:3000"
        }
    }
    catch {
        Write-Warning "Frontend no responde en http://localhost:3000"
        Write-Warning "Esto puede ser normal si usas un reverse proxy"
    }
    
    # Verificar backend
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Success "Backend responde en http://localhost:8000/api/"
        }
    }
    catch {
        Write-Warning "Backend no responde. Verifica que esté corriendo."
    }
}

# Resumen final
Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " DEPLOY COMPLETADO" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Success "Frontend Nuxt 3 desplegado exitosamente"
Write-Host ""
Write-Host "Pasos siguientes:"
Write-Host "  1. Verifica la aplicación en tu navegador"
Write-Host "  2. Prueba hacer login"
Write-Host "  3. Verifica que todas las páginas funcionan"
Write-Host "  4. Monitorea los logs: docker-compose logs -f frontend"
Write-Host ""
Write-Host "En caso de problemas:"
Write-Host "  - Ver logs: docker-compose logs frontend"
if ($BackupTag) {
    Write-Host "  - Rollback: docker tag $BackupTag vozipomni-frontend:latest"
}
Write-Host "  - Consulta: DEPLOY_FRONTEND_NUXT3.md"
Write-Host ""

if (-not $SkipBackup) {
    Write-Info "Backups creados:"
    if ($BackupTag) { Write-Host "  - Imagen: $BackupTag" }
    if ($BackupDir) { Write-Host "  - Archivos: $BackupDir" }
    Write-Host "  - Config: docker-compose.yml.backup"
    Write-Host ""
}

# Preguntar si desea ver logs en tiempo real
$ViewLogs = Read-Host "¿Deseas ver los logs en tiempo real? (s/n)"
if ($ViewLogs -eq "s" -or $ViewLogs -eq "S") {
    Write-Info "Mostrando logs en tiempo real (Ctrl+C para salir)..."
    docker-compose logs -f frontend
}

Write-Host ""
Write-Success "Deploy completado exitosamente!"
