#!/bin/bash

# ============================================================================
# Script de Deploy Automatizado - Frontend Nuxt 3
# VozipOmni Contact Center
# ============================================================================

set -e  # Detener si hay errores

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de utilidad
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo ""
echo "=============================================="
echo " VozipOmni - Deploy Frontend Nuxt 3"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    log_error "No se encontró docker-compose.yml"
    log_error "Por favor ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

# Paso 1: Backup
log_info "Paso 1/10: Creando backup..."

# Backup de imagen Docker
log_info "Creando backup de imagen Docker..."
BACKUP_TAG="vozipomni-frontend:backup-$(date +%Y%m%d-%H%M%S)"
if docker ps -q -f name=vozipomni-frontend > /dev/null 2>&1; then
    docker commit vozipomni-frontend $BACKUP_TAG || true
    log_success "Backup de imagen creado: $BACKUP_TAG"
else
    log_warning "Contenedor frontend no encontrado, saltando backup de imagen"
fi

# Backup de archivos
log_info "Creando backup de archivos..."
if [ -d "frontend" ]; then
    BACKUP_DIR="frontend.backup.$(date +%Y%m%d-%H%M%S)"
    cp -r frontend $BACKUP_DIR
    log_success "Backup de archivos creado: $BACKUP_DIR"
fi

# Backup de docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    cp docker-compose.yml docker-compose.yml.backup
    log_success "Backup de docker-compose.yml creado"
fi

# Paso 2: Actualizar código
log_info "Paso 2/10: Actualizando código desde Git..."
git fetch origin
git pull origin main || git pull origin master || log_warning "No se pudo hacer pull, continuando..."

# Paso 3: Verificar archivos
log_info "Paso 3/10: Verificando archivos de Nuxt 3..."
if [ ! -f "frontend/nuxt.config.ts" ]; then
    log_error "No se encontró frontend/nuxt.config.ts"
    log_error "Asegúrate de que el nuevo frontend está en el repositorio"
    exit 1
fi
log_success "Archivos de Nuxt 3 encontrados"

# Paso 4: Configurar variables de entorno
log_info "Paso 4/10: Configurando variables de entorno..."
if [ ! -f "frontend/.env" ]; then
    log_warning "No se encontró frontend/.env"
    read -p "¿Deseas crear uno desde .env.example? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        if [ -f "frontend/.env.example" ]; then
            cp frontend/.env.example frontend/.env
            log_info "Archivo .env creado. Por favor edítalo con tus valores:"
            log_info "nano frontend/.env"
            read -p "Presiona Enter cuando hayas configurado el .env..."
        fi
    fi
else
    log_success "Archivo .env encontrado"
fi

# Paso 5: Detener servicios
log_info "Paso 5/10: Deteniendo servicios..."
docker-compose stop frontend || log_warning "No se pudo detener frontend"
log_success "Frontend detenido"

# Paso 6: Construir nueva imagen
log_info "Paso 6/10: Construyendo nueva imagen del frontend..."
log_info "Esto puede tomar varios minutos..."

docker-compose build --no-cache frontend

if [ $? -eq 0 ]; then
    log_success "Imagen construida exitosamente"
else
    log_error "Error al construir la imagen"
    log_error "Revisa los logs arriba para más detalles"
    exit 1
fi

# Paso 7: Iniciar servicios
log_info "Paso 7/10: Iniciando servicios..."
docker-compose up -d frontend

if [ $? -eq 0 ]; then
    log_success "Frontend iniciado"
else
    log_error "Error al iniciar frontend"
    exit 1
fi

# Esperar a que el contenedor esté listo
log_info "Esperando a que el frontend esté listo..."
sleep 10

# Paso 8: Verificar estado
log_info "Paso 8/10: Verificando estado de contenedores..."
docker-compose ps

# Paso 9: Verificar logs
log_info "Paso 9/10: Verificando logs del frontend..."
docker-compose logs --tail=50 frontend

# Paso 10: Pruebas de conectividad
log_info "Paso 10/10: Realizando pruebas de conectividad..."

# Verificar frontend
if curl -f -s http://localhost:3000 > /dev/null 2>&1; then
    log_success "Frontend responde en http://localhost:3000"
else
    log_warning "Frontend no responde en http://localhost:3000"
    log_warning "Esto puede ser normal si usas un reverse proxy"
fi

# Verificar backend
if curl -f -s http://localhost:8000/api/ > /dev/null 2>&1; then
    log_success "Backend responde en http://localhost:8000/api/"
else
    log_warning "Backend no responde. Verifica que esté corriendo."
fi

# Resumen final
echo ""
echo "=============================================="
echo " DEPLOY COMPLETADO"
echo "=============================================="
echo ""
log_success "Frontend Nuxt 3 desplegado exitosamente"
echo ""
echo "Pasos siguientes:"
echo "  1. Verifica la aplicación en tu navegador"
echo "  2. Prueba hacer login"
echo "  3. Verifica que todas las páginas funcionan"
echo "  4. Monitorea los logs: docker-compose logs -f frontend"
echo ""
echo "En caso de problemas:"
echo "  - Ver logs: docker-compose logs frontend"
echo "  - Rollback: docker tag $BACKUP_TAG vozipomni-frontend:latest"
echo "  - Consulta: DEPLOY_FRONTEND_NUXT3.md"
echo ""
log_info "Backups creados:"
[ ! -z "$BACKUP_TAG" ] && echo "  - Imagen: $BACKUP_TAG"
[ ! -z "$BACKUP_DIR" ] && echo "  - Archivos: $BACKUP_DIR"
echo "  - Config: docker-compose.yml.backup"
echo ""

# Preguntar si desea ver logs en tiempo real
read -p "¿Deseas ver los logs en tiempo real? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    log_info "Mostrando logs en tiempo real (Ctrl+C para salir)..."
    docker-compose logs -f frontend
fi
