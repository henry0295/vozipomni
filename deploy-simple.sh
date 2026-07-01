#!/bin/bash
################################################################################
# VoziPOmni Contact Center — Deploy Script v3.0.0
# Similar a OmniLeads: https://docs.omnileads.net
#
# 📦 INSTALACIÓN (primera vez):
#   curl -o deploy.sh -L https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh && chmod +x deploy.sh
#   export DOCKER_ENGINE_IPV4=X.X.X.X && ./deploy.sh -i
#
# 🔄 ACTUALIZACIÓN:
#   ./deploy.sh -u
#
# 🌐 Con NAT (servidor con IP privada detrás de router con IP pública):
#   export DOCKER_ENGINE_IPV4=192.168.1.100 NAT_IPV4=190.159.139.176 && ./deploy.sh -i
#
# 🗑️ REINSTALAR (borra todo y reinstala):
#   ./deploy.sh -c
#
################################################################################

set -Eeuo pipefail

# ─── Colores ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Funciones de logging ────────────────────────────────────────────────────
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ─── Banner ──────────────────────────────────────────────────────────────────
show_banner() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║        VoziPOmni Contact Center — Deploy v3.0.0           ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║   Django · Nuxt 3 · Asterisk · Kamailio · RTPEngine      ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ─── Detectar modo ───────────────────────────────────────────────────────────
MODE="install"
while [ $# -gt 0 ]; do
    case "$1" in
        -i|--install) MODE="install"; shift ;;
        -u|--update)  MODE="update"; shift ;;
        -c|--clean)   MODE="clean"; shift ;;
        -h|--help)
            echo "VoziPOmni Deploy Script v3.0.0"
            echo ""
            echo "Uso:"
            echo "  ./deploy.sh -i          Instalación inicial"
            echo "  ./deploy.sh -u          Actualización"
            echo "  ./deploy.sh -c          Reinstalación (borra todo)"
            echo ""
            echo "Variables de entorno requeridas:"
            echo "  DOCKER_ENGINE_IPV4      IP del servidor (obligatorio)"
            echo "  NAT_IPV4                IP pública si está detrás de NAT (opcional)"
            echo "  TZ                      Zona horaria (default: America/Bogota)"
            echo ""
            echo "Ejemplo instalación:"
            echo "  export DOCKER_ENGINE_IPV4=192.168.1.100 && ./deploy.sh -i"
            echo ""
            echo "Ejemplo con NAT:"
            echo "  export DOCKER_ENGINE_IPV4=192.168.1.100 NAT_IPV4=190.159.139.176 && ./deploy.sh -i"
            echo ""
            exit 0
            ;;
        *) shift ;;
    esac
done

show_banner

# ─── Variables de entorno ────────────────────────────────────────────────────
DOCKER_ENGINE_IPV4="${DOCKER_ENGINE_IPV4:-}"
NAT_IPV4="${NAT_IPV4:-}"
TZ="${TZ:-America/Bogota}"
INSTALL_DIR="${INSTALL_DIR:-/opt/vozipomni}"
BRANCH="${BRANCH:-main}"
REPO_URL="https://github.com/henry0295/vozipomni.git"

# Validar IP obligatoria
if [ -z "$DOCKER_ENGINE_IPV4" ]; then
    log_error "DOCKER_ENGINE_IPV4 no está configurado"
    echo ""
    echo "Configure la IP del servidor y ejecute nuevamente:"
    echo -e "${GREEN}export DOCKER_ENGINE_IPV4=X.X.X.X && ./deploy.sh -i${NC}"
    echo ""
    exit 1
fi

log_info "Verificando prerequisitos..."
log_success "IP del servidor: $DOCKER_ENGINE_IPV4"
[ -n "$NAT_IPV4" ] && log_success "IP pública (NAT): $NAT_IPV4"
log_success "Zona horaria: $TZ"

# ─── Detectar Docker Compose ─────────────────────────────────────────────────
if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
else
    log_error "Docker Compose no encontrado"
    echo "Instale Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
log_success "Usando: $COMPOSE_CMD"

# ─── Función: Generar contraseñas seguras ────────────────────────────────────
generate_password() {
    openssl rand -base64 24 | tr -d '\n' | head -c 32
}

generate_secret_key() {
    openssl rand -base64 50 | tr -d '\n' | head -c 50
}

# ─── Función: Crear archivo .env ─────────────────────────────────────────────
create_env_file() {
    log_info "Generando archivo de configuración (.env)..."
    
    # Generar contraseñas si no existen
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        SECRET_KEY=$(generate_secret_key)
        DB_PASS=$(generate_password)
        REDIS_PASS=$(generate_password)
        AMI_PASS=$(generate_password)
        ADMIN_PASS=$(generate_password)
    else
        # Preservar contraseñas existentes
        source "$INSTALL_DIR/.env"
        SECRET_KEY="${SECRET_KEY:-$(generate_secret_key)}"
        DB_PASS="${POSTGRES_PASSWORD:-$(generate_password)}"
        REDIS_PASS="${REDIS_PASSWORD:-$(generate_password)}"
        AMI_PASS="${ASTERISK_AMI_PASSWORD:-$(generate_password)}"
        ADMIN_PASS="${ADMIN_PASSWORD:-$(generate_password)}"
    fi
    
    cat > "$INSTALL_DIR/.env" << EOF
# VoziPOmni Environment - Generado automáticamente $(date)
TZ=$TZ
SUBNET=172.25.0.0/16

# === SEGURIDAD - GENERADO AUTOMÁTICAMENTE ===
SECRET_KEY=$SECRET_KEY
POSTGRES_PASSWORD=$DB_PASS
REDIS_PASSWORD=$REDIS_PASS
ASTERISK_AMI_PASSWORD=$AMI_PASS
ADMIN_PASSWORD=$ADMIN_PASS

# === SERVIDOR ===
VOZIPOMNI_IPV4=$DOCKER_ENGINE_IPV4
NAT_IPV4=$NAT_IPV4

# === PostgreSQL ===
POSTGRES_DB=vozipomni
POSTGRES_USER=vozipomni_user
POSTGRES_PORT=5432
DB_HOST=postgres
DB_NAME=vozipomni
DB_USER=vozipomni_user
DB_PORT=5432

# === Redis ===
REDIS_PORT=6379
REDIS_HOST=redis

# === Django ===
DEBUG=False
ALLOWED_HOSTS=$DOCKER_ENGINE_IPV4,localhost,127.0.0.1
CORS_ORIGINS=http://$DOCKER_ENGINE_IPV4,https://$DOCKER_ENGINE_IPV4
CORS_ALLOW_ALL=False
DJANGO_LOG_LEVEL=INFO
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=120

# === Celery ===
CELERY_CONCURRENCY=4
CELERY_LOG_LEVEL=info

# === Asterisk ===
ASTERISK_AMI_USER=admin
ASTERISK_LOG_LEVEL=3
ASTERISK_HOST=127.0.0.1
ASTERISK_AMI_PORT=5038
ACD_RTP_PORT_MIN=10000
ACD_RTP_PORT_MAX=10299

# === Kamailio ===
KAMAILIO_HOST=127.0.0.1
KAMAILIO_SIP_PORT=5060
KAMAILIO_TLS_PORT=5061
KAMAILIO_HTTPS_PORT=8080

# === RTPEngine ===
RTPENGINE_PORT=22222
RTPENGINE_RTP_PORT_MIN=23000
RTPENGINE_RTP_PORT_MAX=23300

# === Nginx ===
HTTP_PORT=80
HTTPS_PORT=443

# === WebSocket ===
WEBSOCKET_PORT=8765
WEBSOCKET_HOST=0.0.0.0

# === Monitoreo ===
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
EOF

    log_success "Archivo .env creado/actualizado"
}

# ─── Función: Guardar credenciales ──────────────────────────────────────────
save_credentials() {
    source "$INSTALL_DIR/.env"
    
    cat > "$INSTALL_DIR/credentials.txt" << EOF
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        VoziPOmni Contact Center - Credenciales            ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

Fecha de instalación: $(date)
IP del servidor: $DOCKER_ENGINE_IPV4
$([ -n "$NAT_IPV4" ] && echo "IP pública (NAT): $NAT_IPV4")

═══════════════════════════════════════════════════════════
  ACCESO WEB
═══════════════════════════════════════════════════════════
URL:       http://$DOCKER_ENGINE_IPV4
Usuario:   admin
Password:  ${ADMIN_PASSWORD}

═══════════════════════════════════════════════════════════
  BASE DE DATOS (PostgreSQL)
═══════════════════════════════════════════════════════════
Host:      postgres (interno) / $DOCKER_ENGINE_IPV4:5432 (externo)
Database:  vozipomni
Usuario:   vozipomni_user
Password:  ${POSTGRES_PASSWORD}

═══════════════════════════════════════════════════════════
  REDIS
═══════════════════════════════════════════════════════════
Host:      redis (interno) / $DOCKER_ENGINE_IPV4:6379 (externo)
Password:  ${REDIS_PASSWORD}

═══════════════════════════════════════════════════════════
  ASTERISK AMI
═══════════════════════════════════════════════════════════
Host:      $DOCKER_ENGINE_IPV4:5038
Usuario:   admin
Password:  ${ASTERISK_AMI_PASSWORD}

═══════════════════════════════════════════════════════════
  GRAFANA (Métricas)
═══════════════════════════════════════════════════════════
URL:       http://$DOCKER_ENGINE_IPV4:3000
Usuario:   admin
Password:  admin

═══════════════════════════════════════════════════════════
  NOTAS IMPORTANTES
═══════════════════════════════════════════════════════════
⚠️  Guarde este archivo en un lugar seguro
⚠️  NO comparta estas credenciales
⚠️  Cambie las contraseñas en producción si es necesario

📝 Para ver este archivo nuevamente:
   cat $INSTALL_DIR/credentials.txt

🔐 Para habilitar HTTPS:
   cd $INSTALL_DIR && ./quick-https.sh $DOCKER_ENGINE_IPV4
EOF

    chmod 600 "$INSTALL_DIR/credentials.txt"
    log_success "Credenciales guardadas en: $INSTALL_DIR/credentials.txt"
}

# ─── MODO: CLEAN (Reinstalación) ────────────────────────────────────────────
if [ "$MODE" == "clean" ]; then
    log_warn "════════════════════════════════════════════════════════"
    log_warn "  MODO CLEAN — Se borrarán TODOS los datos"
    log_warn "  (Base de datos, grabaciones, configuraciones, .env)"
    log_warn "════════════════════════════════════════════════════════"
    read -p "¿Está seguro? (escriba 'yes' para confirmar): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Operación cancelada"
        exit 0
    fi
    
    log_info "Deteniendo servicios..."
    cd "$INSTALL_DIR" 2>/dev/null && $COMPOSE_CMD -f docker-compose.prod.yml down -v 2>/dev/null || true
    
    log_info "Eliminando directorio de instalación..."
    rm -rf "$INSTALL_DIR"
    
    log_success "Limpieza completada"
    MODE="install"
fi

# ─── MODO: INSTALL ───────────────────────────────────────────────────────────
if [ "$MODE" == "install" ]; then
    log_info "════════════════════════════════════════════════════════"
    log_info "  Modo INSTALACIÓN — Primera instalación"
    log_info "════════════════════════════════════════════════════════"
    
    # Crear directorio
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Clonar repositorio
    if [ -d ".git" ]; then
        log_info "Actualizando código existente..."
        git fetch origin
        git reset --hard origin/$BRANCH
    else
        log_info "Clonando repositorio..."
        git clone --branch $BRANCH $REPO_URL .
    fi
    
    # Crear .env
    create_env_file
    
    # Build images
    log_info "Construyendo imágenes Docker..."
    $COMPOSE_CMD -f docker-compose.prod.yml build
    
    # Iniciar servicios
    log_info "Iniciando servicios..."
    $COMPOSE_CMD -f docker-compose.prod.yml up -d
    
    # Esperar BD
    log_info "Esperando PostgreSQL..."
    sleep 10
    
    # Migraciones
    log_info "Aplicando migraciones..."
    $COMPOSE_CMD -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput
    
    # Crear superusuario
    log_info "Creando usuario administrador..."
    $COMPOSE_CMD -f docker-compose.prod.yml exec -T backend python manage.py shell <<PYEOF
from django.contrib.auth import get_user_model
import os
User = get_user_model()
password = os.environ.get('ADMIN_PASSWORD', 'admin')
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@vozipomni.local', password, role='admin')
    print('Usuario admin creado')
else:
    print('Usuario admin ya existe')
PYEOF
    
    # Collectstatic
    log_info "Recolectando archivos estáticos..."
    $COMPOSE_CMD -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput --clear
    
    # Guardar credenciales
    save_credentials
    
    # Mostrar resultado
    echo ""
    log_success "════════════════════════════════════════════════════════"
    log_success "  ¡Instalación completada exitosamente!"
    log_success "════════════════════════════════════════════════════════"
    echo ""
    echo -e "${BLUE}Accede a tu Contact Center:${NC}"
    echo -e "  → ${GREEN}http://$DOCKER_ENGINE_IPV4${NC}"
    echo ""
    echo -e "${BLUE}Credenciales:${NC}"
    echo -e "  Usuario:    ${GREEN}admin${NC}"
    source "$INSTALL_DIR/.env"
    echo -e "  Contraseña: ${GREEN}${ADMIN_PASSWORD}${NC}"
    echo ""
    echo -e "${BLUE}Credenciales completas:${NC} ${GREEN}$INSTALL_DIR/credentials.txt${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  Guarde las credenciales en un lugar seguro${NC}"
    echo ""
fi

# ─── MODO: UPDATE ────────────────────────────────────────────────────────────
if [ "$MODE" == "update" ]; then
    log_info "════════════════════════════════════════════════════════"
    log_info "  Modo UPDATE — Actualizando instalación existente"
    log_info "  Los datos (BD, grabaciones, .env) NO se borran"
    log_info "════════════════════════════════════════════════════════"
    
    cd "$INSTALL_DIR"
    
    # Actualizar código
    log_info "Actualizando código desde GitHub..."
    git stash
    git fetch origin
    git checkout $BRANCH
    git pull origin $BRANCH
    
    # Rebuild images
    log_info "Reconstruyendo imágenes Docker..."
    $COMPOSE_CMD -f docker-compose.prod.yml build
    
    # Restart services
    log_info "Reiniciando servicios..."
    $COMPOSE_CMD -f docker-compose.prod.yml up -d
    
    # Migraciones
    log_info "Aplicando migraciones pendientes..."
    sleep 10
    $COMPOSE_CMD -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput
    
    # Collectstatic
    log_info "Recolectando archivos estáticos..."
    $COMPOSE_CMD -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput --clear
    
    # Reload Asterisk
    log_info "Recargando configuración de Asterisk..."
    timeout 10 $COMPOSE_CMD -f docker-compose.prod.yml exec -T asterisk asterisk -rx 'dialplan reload' 2>/dev/null || true
    timeout 10 $COMPOSE_CMD -f docker-compose.prod.yml exec -T backend python manage.py shell <<'PYEOF' 2>/dev/null || true
from apps.telephony.pjsip_config_generator import PJSIPConfigGenerator
gen = PJSIPConfigGenerator()
ok, msg = gen.save_and_reload()
print(f'PJSIP reload: {"OK" if ok else "ERROR"} — {msg}')
PYEOF
    
    echo ""
    log_success "════════════════════════════════════════════════════════"
    log_success "  ¡Actualización completada exitosamente!"
    log_success "════════════════════════════════════════════════════════"
    echo ""
    $COMPOSE_CMD -f docker-compose.prod.yml ps
fi

echo ""
log_success "VoziPOmni Deploy v3.0.0 - Listo ✨"
echo ""
