#!/bin/bash
################################################################################
# VoziPOmni Contact Center — Deploy Script
# Version: 2.0.0
#
# Uso rápido (una línea, recomendado):
#   curl -sL https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh | sudo bash -s -- X.X.X.X
#
# Reinstalar desde cero (borra volúmenes, .env, credenciales):
#   curl -sL https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh | sudo bash -s -- --clean X.X.X.X
#
# Alternativas:
#   export VOZIPOMNI_IPV4=X.X.X.X
#   curl -sL https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh | sudo -E bash
#
#   sudo VOZIPOMNI_IPV4=X.X.X.X bash deploy.sh
#   sudo bash deploy.sh --clean X.X.X.X
#
# Variables opcionales:
#   VOZIPOMNI_IPV4  — IP pública/privada del servidor (REQUERIDO, o pasar como argumento $1)
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

# ─── Parsear argumentos (--clean, IP) ────────────────────────────────────────
CLEAN_INSTALL=false
for arg in "$@"; do
    case "$arg" in
        --clean|-c)
            CLEAN_INSTALL=true
            ;;
        --help|-h)
            echo "Uso: deploy.sh [--clean] <IP>"
            echo ""
            echo "  IP          IP del servidor (requerido)"
            echo "  --clean     Borrar instalación existente (volúmenes, .env, credenciales)"
            echo "  --help      Mostrar esta ayuda"
            exit 0
            ;;
        *)
            # Si parece una IP, usarla
            if [[ "$arg" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
                export VOZIPOMNI_IPV4="$arg"
            fi
            ;;
    esac
done

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

# ─── Limpiar instalación existente ───────────────────────────────────────────
clean_existing() {
    if [ "$CLEAN_INSTALL" != true ]; then
        return 0
    fi

    log_warning "══════════════════════════════════════════════════════"
    log_warning "  MODO LIMPIO: Se borrará toda la instalación"
    log_warning "  - Contenedores y volúmenes Docker"
    log_warning "  - Archivos .env y credenciales"
    log_warning "  - Base de datos, grabaciones, archivos media"
    log_warning "══════════════════════════════════════════════════════"
    echo ""

    # Si es interactivo, pedir confirmación
    if [ -t 0 ]; then
        read -r -p "¿Está seguro? Esto es IRREVERSIBLE [s/N]: " confirm
        if [[ ! "$confirm" =~ ^[sS]$ ]]; then
            log_info "Cancelado por el usuario"
            exit 0
        fi
    else
        log_info "Modo no-interactivo detectado, continuando limpieza..."
    fi

    cd "$INSTALL_DIR" 2>/dev/null || true

    # Detectar compose antes de usarlo
    local COMPOSE=""
    if docker compose version &>/dev/null; then
        COMPOSE="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE="docker-compose"
    fi

    # Parar y borrar contenedores + volúmenes
    if [ -n "$COMPOSE" ] && [ -f "$INSTALL_DIR/docker-compose.prod.yml" ]; then
        log_info "Deteniendo servicios y borrando volúmenes..."
        $COMPOSE -f "$INSTALL_DIR/docker-compose.prod.yml" down -v --remove-orphans 2>/dev/null || true
    fi

    # Borrar imágenes del proyecto
    log_info "Borrando imágenes Docker del proyecto..."
    docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -i vozipomni | xargs -r docker rmi -f 2>/dev/null || true

    # Borrar archivos de configuración
    if [ -d "$INSTALL_DIR" ]; then
        log_info "Limpiando archivos de configuración..."
        rm -f "$INSTALL_DIR/.env" \
              "$INSTALL_DIR/.env.backup_"* \
              "$INSTALL_DIR/backend/.env" \
              "$INSTALL_DIR/credentials.txt"
        rm -rf "$INSTALL_DIR/logs/"* 2>/dev/null || true
    fi

    log_success "Instalación anterior eliminada completamente"
    echo ""
}

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
        echo "Uso (recomendado):"
        echo "  curl -sL https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh | sudo bash -s -- X.X.X.X"
        echo ""
        echo "Alternativas:"
        echo "  export VOZIPOMNI_IPV4=X.X.X.X"
        echo "  curl -sL .../deploy.sh | sudo -E bash"
        echo ""
        echo "  sudo VOZIPOMNI_IPV4=X.X.X.X bash deploy.sh"
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

# ─── 3. Instalar Docker (soporte universal de distribuciones) ────────────────
install_docker() {
    if command -v docker &>/dev/null; then
        log_success "Docker ya instalado: $(docker --version 2>/dev/null | head -1)"
    else
        log_info "Instalando Docker..."

        # Detectar distribución
        local DISTRO_ID="unknown" DISTRO_LIKE=""
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO_ID="${ID:-unknown}"
            DISTRO_LIKE="${ID_LIKE:-}"
        fi

        case "$DISTRO_ID" in
            rocky|almalinux|centos|ol)
                log_info "Distribución detectada: $DISTRO_ID — Usando repositorio CentOS Docker"
                dnf remove -y docker docker-client docker-client-latest docker-common \
                    docker-latest docker-latest-logrotate docker-logrotate docker-engine 2>/dev/null || true
                dnf install -y yum-utils
                yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
                dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;
            rhel)
                log_info "Distribución detectada: RHEL"
                dnf remove -y docker docker-client docker-client-latest docker-common \
                    docker-latest docker-latest-logrotate docker-logrotate docker-engine 2>/dev/null || true
                dnf install -y yum-utils
                yum-config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo 2>/dev/null || \
                    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
                dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;
            fedora)
                log_info "Distribución detectada: Fedora"
                dnf remove -y docker docker-client docker-client-latest docker-common \
                    docker-latest docker-latest-logrotate docker-logrotate docker-engine 2>/dev/null || true
                dnf install -y dnf-plugins-core
                dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
                dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;
            ubuntu|linuxmint|pop)
                log_info "Distribución detectada: $DISTRO_ID — Usando repositorio Ubuntu Docker"
                apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
                apt-get update -y
                apt-get install -y ca-certificates curl gnupg lsb-release
                install -m 0755 -d /etc/apt/keyrings
                curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
                chmod a+r /etc/apt/keyrings/docker.gpg
                local UBUNTU_CODENAME_VAL
                if [ "$DISTRO_ID" = "ubuntu" ]; then
                    UBUNTU_CODENAME_VAL="${VERSION_CODENAME:-$(lsb_release -cs 2>/dev/null || echo focal)}"
                else
                    UBUNTU_CODENAME_VAL="${UBUNTU_CODENAME:-$(grep UBUNTU_CODENAME /etc/os-release 2>/dev/null | cut -d= -f2 || echo focal)}"
                fi
                echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $UBUNTU_CODENAME_VAL stable" | \
                    tee /etc/apt/sources.list.d/docker.list > /dev/null
                apt-get update -y
                apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;
            debian)
                log_info "Distribución detectada: Debian"
                apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
                apt-get update -y
                apt-get install -y ca-certificates curl gnupg lsb-release
                install -m 0755 -d /etc/apt/keyrings
                curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
                chmod a+r /etc/apt/keyrings/docker.gpg
                echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian ${VERSION_CODENAME:-bullseye} stable" | \
                    tee /etc/apt/sources.list.d/docker.list > /dev/null
                apt-get update -y
                apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;
            amzn)
                log_info "Distribución detectada: Amazon Linux"
                yum remove -y docker docker-client docker-client-latest docker-common \
                    docker-latest docker-latest-logrotate docker-logrotate docker-engine 2>/dev/null || true
                amazon-linux-extras install docker -y 2>/dev/null || yum install -y docker
                ;;
            opensuse*|sles)
                log_info "Distribución detectada: openSUSE/SLES"
                zypper remove -y docker docker-client docker-client-latest 2>/dev/null || true
                zypper install -y docker docker-compose
                ;;
            arch|manjaro)
                log_info "Distribución detectada: Arch/Manjaro"
                pacman -Sy --noconfirm docker docker-compose
                ;;
            alpine)
                log_info "Distribución detectada: Alpine"
                apk add --no-cache docker docker-compose
                ;;
            *)
                # Fallback por ID_LIKE
                if echo "$DISTRO_LIKE" | grep -qiE "rhel|centos|fedora"; then
                    log_warning "Distribución '$DISTRO_ID' no reconocida pero basada en RHEL — Usando repositorio CentOS"
                    dnf install -y yum-utils 2>/dev/null || yum install -y yum-utils
                    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
                    dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin 2>/dev/null || \
                        yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                elif echo "$DISTRO_LIKE" | grep -qiE "debian|ubuntu"; then
                    log_warning "Distribución '$DISTRO_ID' no reconocida pero basada en Debian — Usando repositorio Ubuntu"
                    apt-get update -y
                    apt-get install -y ca-certificates curl gnupg
                    install -m 0755 -d /etc/apt/keyrings
                    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
                    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu focal stable" | \
                        tee /etc/apt/sources.list.d/docker.list > /dev/null
                    apt-get update -y
                    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                else
                    log_error "Distribución '$DISTRO_ID' no soportada. Instale Docker manualmente:"
                    echo "  https://docs.docker.com/engine/install/"
                    exit 1
                fi
                ;;
        esac

        log_success "Docker instalado correctamente"
    fi

    # Habilitar y arrancar Docker
    systemctl enable docker --now 2>/dev/null || true
    systemctl start docker 2>/dev/null || true

    # Reiniciar Docker con daemon.json optimizado
    systemctl restart docker 2>/dev/null || true

    # Verificar que Docker funciona
    if ! docker info &>/dev/null; then
        log_error "Docker no se pudo iniciar correctamente"
        exit 1
    fi

    log_success "Docker listo: $(docker --version)"

    # Detectar compose
    if docker compose version &>/dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        # Instalar docker-compose standalone como fallback
        log_warning "docker compose plugin no encontrado, instalando docker-compose standalone..."
        curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
            -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        COMPOSE_CMD="docker-compose"
    fi
    log_info "Usando: $COMPOSE_CMD ($($COMPOSE_CMD version 2>/dev/null || echo 'versión desconocida'))"
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
    # Si ya existe .env, reutilizar credenciales existentes (volúmenes de DB/Redis persisten)
    if [ -f "$INSTALL_DIR/.env" ]; then
        log_info "Archivo .env existente encontrado, reutilizando credenciales..."
        # Extraer credenciales del .env existente
        source "$INSTALL_DIR/.env" 2>/dev/null || true
        local DB_PASSWORD="${POSTGRES_PASSWORD:-}"
        local REDIS_PASSWORD="${REDIS_PASSWORD:-}"
        local SECRET_KEY="${SECRET_KEY:-}"

        # Si faltan credenciales críticas, regenerar
        if [ -z "$DB_PASSWORD" ] || [ -z "$SECRET_KEY" ]; then
            log_warning "Credenciales incompletas en .env existente, regenerando..."
            cp "$INSTALL_DIR/.env" "$INSTALL_DIR/.env.backup_${TIMESTAMP}"
        else
            # Solo actualizar la IP si cambió
            sed -i "s|^VOZIPOMNI_IPV4=.*|VOZIPOMNI_IPV4=$VOZIPOMNI_IPV4|" "$INSTALL_DIR/.env"
            sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=$VOZIPOMNI_IPV4,localhost,127.0.0.1|" "$INSTALL_DIR/.env"
            sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=http://$VOZIPOMNI_IPV4,https://$VOZIPOMNI_IPV4|" "$INSTALL_DIR/.env"

            # Actualizar backend/.env con credenciales existentes y nueva IP
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

            # Exportar para post_deploy
            export ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
            export DB_PASSWORD
            export REDIS_PASSWORD

            log_success "Credenciales existentes reutilizadas (IP actualizada: $VOZIPOMNI_IPV4)"
            return 0
        fi
    fi

    # === Primera instalación: generar credenciales nuevas ===
    log_info "Generando credenciales nuevas..."

    local DB_PASSWORD REDIS_PASSWORD SECRET_KEY ADMIN_PASSWORD
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    SECRET_KEY=$(openssl rand -base64 50 | tr -d "=+/")
    ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-12)

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

    # Build
    log_info "Construyendo imágenes Docker (esto puede tardar varios minutos)..."
    $COMPOSE_CMD -f docker-compose.prod.yml build 2>&1

    # Levantar data stores primero y esperar que estén healthy
    log_info "Iniciando PostgreSQL y Redis..."
    $COMPOSE_CMD -f docker-compose.prod.yml up -d postgres redis 2>&1

    log_info "Esperando que PostgreSQL y Redis estén healthy..."
    local db_ready=false
    for i in $(seq 1 60); do
        if $COMPOSE_CMD -f docker-compose.prod.yml exec -T postgres pg_isready -U vozipomni_user -d vozipomni -q 2>/dev/null; then
            db_ready=true
            break
        fi
        printf "  Intento %d/60 — esperando PostgreSQL...\\r" "$i"
        sleep 3
    done

    if [ "$db_ready" = false ]; then
        log_error "PostgreSQL no respondió después de 3 minutos"
        log_info "Logs de PostgreSQL:"
        $COMPOSE_CMD -f docker-compose.prod.yml logs --tail=20 postgres
        exit 1
    fi
    log_success "PostgreSQL listo"

    # Levantar backend
    log_info "Iniciando backend..."
    $COMPOSE_CMD -f docker-compose.prod.yml up -d backend 2>&1

    # Verificar que el backend no crasheó (esperar 20s y revisar)
    sleep 20
    if ! $COMPOSE_CMD -f docker-compose.prod.yml ps backend 2>/dev/null | grep -qiE "up|running"; then
        log_error "El backend no arrancó correctamente"
        log_info "Logs del backend:"
        $COMPOSE_CMD -f docker-compose.prod.yml logs --tail=50 backend
        echo ""
        log_info "Reintentando backend..."
        $COMPOSE_CMD -f docker-compose.prod.yml up -d backend 2>&1
        sleep 15
    fi

    # Levantar el resto de servicios
    log_info "Iniciando todos los servicios restantes..."
    $COMPOSE_CMD -f docker-compose.prod.yml up -d 2>&1

    log_success "Servicios iniciados"
}

# ─── 8. wait_for_env — Polling HTTP ──────────────────────
wait_for_env() {
    local url="http://localhost:8000/api/health/"
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
    clean_existing
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
