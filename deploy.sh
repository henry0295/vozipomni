#!/bin/bash
################################################################################
# VoziPOmni Contact Center — Deploy Script (estilo OmniLeads)
# Version: 2.0.0
#
# Uso rápido (una línea):
#   export VOZIPOMNI_IPV4=X.X.X.X && curl -sL https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh | bash
#
# Uso manual:
#   export VOZIPOMNI_IPV4=192.168.1.100
#   bash deploy.sh
#
# Variables opcionales:
#   VOZIPOMNI_IPV4  — IP pública/privada del servidor (REQUERIDO)
#   NAT_IPV4        — IP pública si el servidor está detrás de NAT
#   TZ              — Zona horaria (default: America/Bogota)
#   INSTALL_DIR     — Directorio de instalación (default: /opt/vozipomni)
#   BRANCH          — Rama Git a desplegar (default: main)
#
################################################################################

set -Eeuo pipefail

# ─── Manejo de errores ───────────────────────────────────────────────────────
on_error() {
    local exit_code=$?
    local line_no=${BASH_LINENO[0]}
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  ERROR: deploy.sh falló en la línea $line_no (código: $exit_code)"
    echo "║  Revise los logs arriba para más detalles.               ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Sugerencias:"
    echo "  1. Verifique que VOZIPOMNI_IPV4 esté configurado correctamente"
    echo "  2. Verifique su conexión a internet"
    echo "  3. Revise: $COMPOSE_CMD -f docker-compose.prod.yml logs"
    echo "  4. Reintente: sudo bash deploy.sh"
    echo ""
    exit $exit_code
}
trap on_error ERR

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Variables ───────────────────────────────────────────────────────────────
INSTALL_DIR="${INSTALL_DIR:-/opt/vozipomni}"
BRANCH="${BRANCH:-main}"
TZ="${TZ:-America/Bogota}"
COMPOSE_CMD=""
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ─── Funciones ───────────────────────────────────────────────────────────────
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

banner() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}║        VoziPOmni Contact Center — Deploy v2.0             ║${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}║   Django · Nuxt 3 · Asterisk · Kamailio · RTPEngine      ║${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ─── 1. Verificar prerequisitos ─────────────────────────────────────────────
check_prerequisites() {
    log_info "Verificando prerequisitos..."

    # Root
    if [[ $EUID -ne 0 ]]; then
        log_error "Este script debe ejecutarse como root o con sudo"
        exit 1
    fi

    # IP
    if [ -z "${VOZIPOMNI_IPV4:-}" ]; then
        log_error "Variable VOZIPOMNI_IPV4 no está configurada"
        echo ""
        echo "Uso:"
        echo "  export VOZIPOMNI_IPV4=X.X.X.X"
        echo "  bash deploy.sh"
        echo ""
        exit 1
    fi

    # Validar formato IP
    if ! [[ $VOZIPOMNI_IPV4 =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        log_error "Formato de IP inválido: $VOZIPOMNI_IPV4"
        exit 1
    fi

    log_success "IP del servidor: $VOZIPOMNI_IPV4"
    [ -n "${NAT_IPV4:-}" ] && log_info "NAT IP: $NAT_IPV4"
    log_success "Zona horaria: $TZ"
}

# ─── 2. Preparar sistema ────────────────────────────────────────────────────
prepare_system() {
    log_info "Preparando sistema operativo..."

    # Silenciar kernel (veth/bridge messages)
    if [ -f /proc/sys/kernel/printk ]; then
        echo "1 4 1 7" > /proc/sys/kernel/printk
    else
        dmesg -n 1 2>/dev/null || true
    fi

    # Persistir
    mkdir -p /etc/sysctl.d
    cat > /etc/sysctl.d/10-vozipomni.conf <<'SYSCTL'
# VoziPOmni: Silenciar kernel + optimizaciones VoIP
kernel.printk = 1 4 1 7
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.rmem_default = 262144
net.core.wmem_default = 262144
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
vm.swappiness = 10
vm.overcommit_memory = 1
fs.file-max = 2097152
SYSCTL
    sysctl -p /etc/sysctl.d/10-vozipomni.conf 2>/dev/null || true

    # Límites del sistema
    cat > /etc/security/limits.d/99-vozipomni.conf <<'LIMITS'
* soft nofile 65536
* hard nofile 65536
* soft nproc  65536
* hard nproc  65536
LIMITS

    # SELinux
    if command -v getenforce &>/dev/null; then
        if [ "$(getenforce 2>/dev/null)" = "Enforcing" ]; then
            setenforce 0 2>/dev/null || true
            sed -i 's/^SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config 2>/dev/null || true
            log_info "SELinux → Permissive"
        fi
    fi

    # Docker daemon
    mkdir -p /etc/docker
    if [ ! -f /etc/docker/daemon.json ]; then
        cat > /etc/docker/daemon.json <<'DAEMON'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" },
  "storage-driver": "overlay2",
  "live-restore": true,
  "default-ulimits": { "nofile": { "Name": "nofile", "Hard": 65536, "Soft": 65536 } }
}
DAEMON
    fi

    log_success "Sistema preparado"
}

# ─── 3. Instalar Docker ─────────────────────────────────────────────────────
install_docker() {
    if command -v docker &>/dev/null; then
        log_success "Docker ya instalado: $(docker --version 2>/dev/null | head -1)"
    else
        log_info "Instalando Docker..."
        
        # Instalar dependencias básicas
        if command -v apt-get &>/dev/null; then
            apt-get update -qq
            apt-get install -y -qq git curl ca-certificates gnupg >/dev/null 2>&1
        elif command -v dnf &>/dev/null; then
            dnf install -y -q git curl ca-certificates >/dev/null 2>&1
        elif command -v yum &>/dev/null; then
            yum install -y -q git curl ca-certificates >/dev/null 2>&1
        fi

        # Docker via get.docker.com (universal)
        curl -fsSL https://get.docker.com | sh
        
        systemctl start docker 2>/dev/null || true
        systemctl enable docker 2>/dev/null || true
        
        log_success "Docker instalado correctamente"
    fi

    # Reiniciar Docker con daemon.json optimizado
    systemctl restart docker 2>/dev/null || true

    # Detectar compose
    if docker compose version &>/dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        log_error "Docker Compose no encontrado"
        exit 1
    fi
    log_info "Usando: $COMPOSE_CMD"
}

# ─── 4. Clonar repositorio ──────────────────────────────────────────────────
clone_repo() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        log_info "Actualizando repositorio existente..."
        cd "$INSTALL_DIR"
        git fetch origin
        git checkout "$BRANCH" 2>/dev/null || true
        git pull origin "$BRANCH"
    else
        log_info "Clonando repositorio (rama: $BRANCH)..."
        mkdir -p /opt
        git clone -b "$BRANCH" https://github.com/henry0295/vozipomni.git "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    log_success "Repositorio listo en $INSTALL_DIR"
}

# ─── 5. Generar credenciales y .env ─────────────────────────────────────────
generate_env() {
    log_info "Generando credenciales y archivo .env..."

    local DB_PASSWORD REDIS_PASSWORD SECRET_KEY ADMIN_PASSWORD
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    SECRET_KEY=$(openssl rand -base64 50 | tr -d "=+/")
    ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-12)

    # Si ya existe .env, hacer backup
    if [ -f "$INSTALL_DIR/.env" ]; then
        cp "$INSTALL_DIR/.env" "$INSTALL_DIR/.env.backup_${TIMESTAMP}"
        log_info "Backup de .env existente creado"
    fi

    cat > "$INSTALL_DIR/.env" <<EOF
# VoziPOmni — Producción (Generado: $(date))
# network_mode: host → todos los hosts apuntan a VOZIPOMNI_IPV4

VOZIPOMNI_IPV4=$VOZIPOMNI_IPV4
NAT_IPV4=${NAT_IPV4:-}
TZ=$TZ

POSTGRES_DB=vozipomni
POSTGRES_USER=vozipomni_user
POSTGRES_PASSWORD=$DB_PASSWORD

REDIS_PASSWORD=$REDIS_PASSWORD

SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$VOZIPOMNI_IPV4,localhost,127.0.0.1
CORS_ORIGINS=http://$VOZIPOMNI_IPV4,https://$VOZIPOMNI_IPV4
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=120

CELERY_LOG_LEVEL=info
CELERY_CONCURRENCY=4

ASTERISK_AMI_USER=admin
ASTERISK_AMI_PASSWORD=vozipomni_ami_2026

NUXT_PUBLIC_API_BASE=/api
NUXT_PUBLIC_WS_BASE=/ws
NUXT_PUBLIC_APP_NAME=VozipOmni

WS_PORT=8765
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
EOF

    chmod 600 "$INSTALL_DIR/.env"

    # Backend .env
    cat > "$INSTALL_DIR/backend/.env" <<EOF
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$VOZIPOMNI_IPV4,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://$VOZIPOMNI_IPV4,https://$VOZIPOMNI_IPV4
DB_NAME=vozipomni
DB_USER=vozipomni_user
DB_PASSWORD=$DB_PASSWORD
DB_HOST=$VOZIPOMNI_IPV4
DB_PORT=5432
REDIS_HOST=$VOZIPOMNI_IPV4
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD
ASTERISK_HOST=$VOZIPOMNI_IPV4
ASTERISK_AMI_USER=admin
ASTERISK_AMI_PASSWORD=vozipomni_ami_2026
ASTERISK_CONFIG_DIR=/var/lib/asterisk/dynamic
ASTERISK_PUBLIC_IP=$VOZIPOMNI_IPV4
CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@$VOZIPOMNI_IPV4:6379/0
CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@$VOZIPOMNI_IPV4:6379/1
EOF

    # Guardar credenciales
    cat > "$INSTALL_DIR/credentials.txt" <<EOF
════════════════════════════════════════════════════════════
         VoziPOmni Contact Center — Credenciales
════════════════════════════════════════════════════════════
Fecha: $(date)
Servidor: $VOZIPOMNI_IPV4

WEB:          http://$VOZIPOMNI_IPV4
Admin Django: http://$VOZIPOMNI_IPV4/admin
API REST:     http://$VOZIPOMNI_IPV4/api

Usuario: admin
Password: $ADMIN_PASSWORD

PostgreSQL: vozipomni_user / $DB_PASSWORD (puerto 5432)
Redis:      $REDIS_PASSWORD (puerto 6379)
AMI:        admin / vozipomni_ami_2026 (puerto 5038)
════════════════════════════════════════════════════════════
EOF
    chmod 600 "$INSTALL_DIR/credentials.txt"

    # Exportar para uso posterior
    export ADMIN_PASSWORD
    export DB_PASSWORD
    export REDIS_PASSWORD

    log_success "Credenciales generadas y .env creado"
}

# ─── 6. Configurar firewall ─────────────────────────────────────────────────
configure_firewall() {
    log_info "Configurando firewall..."

    local PORTS="22/tcp 80/tcp 443/tcp 5060/tcp 5060/udp 5061/tcp 5161/udp 5162/udp 5038/tcp 8080/tcp 8088/tcp 8089/tcp 8765/tcp 10000:23100/udp"

    if command -v ufw &>/dev/null; then
        for port in $PORTS; do
            ufw allow "$port" 2>/dev/null || true
        done
        ufw --force enable 2>/dev/null || true
        log_success "Firewall UFW configurado"
    elif command -v firewall-cmd &>/dev/null; then
        for port in $PORTS; do
            firewall-cmd --permanent --add-port="$port" 2>/dev/null || true
        done
        firewall-cmd --reload 2>/dev/null || true
        log_success "Firewall firewalld configurado"
    else
        log_warning "No se detectó firewall. Configure puertos manualmente."
    fi
}

# ─── 7. Build & Deploy ──────────────────────────────────────────────────────
deploy_services() {
    log_info "Desplegando servicios..."
    cd "$INSTALL_DIR"

    # Parar servicios anteriores si existen
    $COMPOSE_CMD -f docker-compose.prod.yml down 2>/dev/null || true

    # Build e iniciar
    log_info "Construyendo imágenes Docker (esto puede tardar varios minutos)..."
    $COMPOSE_CMD -f docker-compose.prod.yml build 2>&1

    log_info "Iniciando servicios..."
    $COMPOSE_CMD -f docker-compose.prod.yml up -d 2>&1

    log_success "Servicios iniciados en background"
}

# ─── 8. wait_for_env — Polling HTTP (estilo OmniLeads) ──────────────────────
wait_for_env() {
    local url="http://localhost:8000/api/"
    local WAIT_TIMEOUT=${1:-600}
    local WAIT_INTERVAL=10
    local elapsed=0

    log_info "Esperando que VoziPOmni esté listo (máx ${WAIT_TIMEOUT}s)..."
    echo ""

    while [ $elapsed -lt $WAIT_TIMEOUT ]; do
        local http_code
        http_code=$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>/dev/null || echo "000")

        case $http_code in
            200|301|302|403)
                echo ""
                log_success "Backend respondiendo (HTTP $http_code) — ${elapsed}s"
                return 0
                ;;
            *)
                printf "  [%3ds/%ds] HTTP %s — esperando...\\r" "$elapsed" "$WAIT_TIMEOUT" "$http_code"
                ;;
        esac

        sleep $WAIT_INTERVAL
        elapsed=$((elapsed + WAIT_INTERVAL))
    done

    echo ""
    log_warning "Timeout alcanzado. Verifique: $COMPOSE_CMD -f docker-compose.prod.yml logs backend"
    return 1
}

# ─── 9. Post-deploy ─────────────────────────────────────────────────────────
post_deploy() {
    log_info "Ejecutando migraciones..."
    cd "$INSTALL_DIR"

    # Esperar PostgreSQL
    for i in {1..60}; do
        if $COMPOSE_CMD -f docker-compose.prod.yml exec -T postgres pg_isready -U vozipomni_user -d vozipomni > /dev/null 2>&1; then
            break
        fi
        sleep 2
    done

    $COMPOSE_CMD -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput 2>/dev/null || \
    $COMPOSE_CMD -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput

    # Crear superusuario
    log_info "Creando usuario administrador..."
    $COMPOSE_CMD -f docker-compose.prod.yml exec -T backend python manage.py shell <<PYEOF 2>/dev/null || true
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@vozipomni.local', '${ADMIN_PASSWORD}')
    print('Superuser creado')
else:
    print('Superuser ya existe')
PYEOF

    log_success "Post-deploy completado"
}

# ─── 10. Mostrar resultado ──────────────────────────────────────────────────
show_result() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║       ¡Despliegue de VoziPOmni completado!               ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Accede a tu Contact Center:${NC}"
    echo -e "  → ${GREEN}http://$VOZIPOMNI_IPV4${NC}"
    echo ""
    echo -e "${BLUE}Credenciales:${NC}"
    echo -e "  Usuario:    ${GREEN}admin${NC}"
    echo -e "  Contraseña: ${GREEN}${ADMIN_PASSWORD}${NC}"
    echo ""
    echo -e "${BLUE}Credenciales completas:${NC} ${GREEN}$INSTALL_DIR/credentials.txt${NC}"
    echo ""
    echo -e "${BLUE}Comandos útiles:${NC}"
    echo -e "  Estado:    ${GREEN}cd $INSTALL_DIR && $COMPOSE_CMD -f docker-compose.prod.yml ps${NC}"
    echo -e "  Logs:      ${GREEN}cd $INSTALL_DIR && $COMPOSE_CMD -f docker-compose.prod.yml logs -f${NC}"
    echo -e "  Reiniciar: ${GREEN}cd $INSTALL_DIR && $COMPOSE_CMD -f docker-compose.prod.yml restart${NC}"
    echo -e "  Detener:   ${GREEN}cd $INSTALL_DIR && $COMPOSE_CMD -f docker-compose.prod.yml down${NC}"
    echo ""
    echo -e "${BLUE}Servicios:${NC}"
    $COMPOSE_CMD -f docker-compose.prod.yml ps 2>/dev/null || true
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================
main() {
    banner
    check_prerequisites
    echo ""
    prepare_system
    echo ""
    install_docker
    echo ""
    clone_repo
    echo ""
    generate_env
    echo ""
    configure_firewall
    echo ""
    deploy_services
    echo ""
    wait_for_env 600 || true
    echo ""
    post_deploy
    echo ""
    show_result
}

main "$@"
