#!/bin/bash

################################################################################
# VoziPOmni Contact Center - Installation Script
# Version: 2.0.0
# Compatible with: Any Linux distribution (Ubuntu, Debian, CentOS, Rocky,
#                   RHEL, Fedora, openSUSE, Arch, Amazon Linux, Alpine...)
#
# Estilo OmniLeads: pipefail, trap ERR, wait_for_env HTTP polling,
#   network_mode: host en producción, healthcheck-based depends_on
################################################################################

set -Eeuo pipefail

# ─── Manejo de errores estilo OmniLeads ──────────────────────────────────────
on_error() {
    local exit_code=$?
    local line_no=${BASH_LINENO[0]}
    echo ""
    echo -e "\033[0;31m╔════════════════════════════════════════════════════════════╗\033[0m"
    echo -e "\033[0;31m║  ERROR: El script falló en la línea $line_no (código: $exit_code)  ║\033[0m"
    echo -e "\033[0;31m║  Revise los logs arriba para más detalles.               ║\033[0m"
    echo -e "\033[0;31m╚════════════════════════════════════════════════════════════╝\033[0m"
    echo ""
    echo -e "\033[1;33mSugerencias:\033[0m"
    echo "  1. Verifique su conexión a internet"
    echo "  2. Revise los logs: cd $INSTALL_DIR && $COMPOSE_CMD -f docker-compose.prod.yml logs"
    echo "  3. Reintente: sudo bash install.sh"
    echo ""
    exit $exit_code
}
trap on_error ERR

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation directory
INSTALL_DIR="/opt/vozipomni"
BACKUP_DIR="/opt/vozipomni/backups"
COMPOSE_CMD=""
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Check if script is run as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Este script debe ejecutarse como root o con sudo${NC}"
   exit 1
fi

################################################################################
# Functions
################################################################################

# ─── Detectar comando docker compose ─────────────────────────────────────────
detect_compose_cmd() {
    if docker compose version &>/dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        log_error "No se encontró 'docker compose' ni 'docker-compose'"
        log_error "Instale Docker Compose e intente de nuevo"
        exit 1
    fi
    log_info "Usando compose: $COMPOSE_CMD"
}

print_header() {
    clear
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}║          VoziPOmni Contact Center Installer v2.0          ║${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}║          Sistema de Contact Center Omnicanal              ║${NC}"
    echo -e "${BLUE}║          Powered by Django, Nuxt 3 & Asterisk             ║${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[ADVERTENCIA]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        OS_NAME=$NAME
    elif [ -f /etc/redhat-release ]; then
        OS="rhel"
        OS_VERSION="unknown"
        OS_NAME="Red Hat / CentOS"
    elif [ -f /etc/debian_version ]; then
        OS="debian"
        OS_VERSION=$(cat /etc/debian_version)
        OS_NAME="Debian"
    elif [ -f /etc/arch-release ]; then
        OS="arch"
        OS_VERSION="rolling"
        OS_NAME="Arch Linux"
    else
        log_warning "No se pudo detectar el sistema operativo, intentando continuar..."
        OS="unknown"
        OS_VERSION="unknown"
        OS_NAME="Linux desconocido"
    fi
    
    log_info "Sistema operativo detectado: $OS_NAME $OS_VERSION"
}

prepare_system() {
    log_info "Preparando sistema para instalación limpia..."

    # ── 1. Silenciar mensajes del kernel (problema de logs veth/bridge) ──
    log_info "Silenciando mensajes del kernel en consola..."
    if [ -f /proc/sys/kernel/printk ]; then
        echo "1 4 1 7" > /proc/sys/kernel/printk
    else
        dmesg -n 1 2>/dev/null || true
    fi

    # Persistir configuración
    cat > /etc/sysctl.d/10-vozipomni-silence.conf <<'SYSCTL'
# VoziPOmni: Silenciar mensajes del kernel en consola
kernel.printk = 1 4 1 7
SYSCTL
    log_success "Mensajes del kernel silenciados"

    # ── 2. Optimizaciones de red para VoIP y Docker ──
    log_info "Aplicando optimizaciones del kernel para VoIP..."
    cat > /etc/sysctl.d/20-vozipomni-optimize.conf <<'SYSCTL'
# VoziPOmni - Optimizaciones para VoIP y Docker
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.rmem_default = 262144
net.core.wmem_default = 262144
net.core.netdev_max_backlog = 5000
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
vm.swappiness = 10
vm.overcommit_memory = 1
vm.max_map_count = 262144
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
SYSCTL

    # Cargar módulo bridge para Docker
    modprobe br_netfilter 2>/dev/null || true

    # Aplicar sysctl (ignorar errores de parámetros no soportados)
    sysctl -p /etc/sysctl.d/10-vozipomni-silence.conf 2>/dev/null || true
    sysctl -p /etc/sysctl.d/20-vozipomni-optimize.conf 2>/dev/null || true
    log_success "Optimizaciones del kernel aplicadas"

    # ── 3. Configurar límites del sistema ──
    cat > /etc/security/limits.d/99-vozipomni.conf <<'LIMITS'
* soft nofile 65536
* hard nofile 65536
* soft nproc  65536
* hard nproc  65536
root soft nofile 65536
root hard nofile 65536
LIMITS
    log_success "Límites del sistema configurados"

    # ── 4. Configurar Docker daemon optimizado ──
    mkdir -p /etc/docker
    if [ ! -f /etc/docker/daemon.json ]; then
        cat > /etc/docker/daemon.json <<'DAEMON'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  }
}
DAEMON
        log_success "Docker daemon configurado"
    else
        log_info "Docker daemon.json ya existe, respetando configuración actual"
    fi

    # ── 5. SELinux a permissive si está en enforcing (RHEL/CentOS/Rocky) ──
    if command -v getenforce &>/dev/null; then
        if [ "$(getenforce 2>/dev/null)" = "Enforcing" ]; then
            setenforce 0 2>/dev/null || true
            sed -i 's/^SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config 2>/dev/null || true
            log_success "SELinux configurado a Permissive"
        fi
    fi

    log_success "Sistema preparado correctamente para la instalación"
}

check_system_requirements() {
    log_info "Verificando requisitos del sistema..."
    
    # Check RAM
    TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
    if [ $TOTAL_RAM -lt 4 ]; then
        log_warning "RAM insuficiente. Mínimo 4GB, detectado: ${TOTAL_RAM}GB"
        read -p "¿Desea continuar de todos modos? (s/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            exit 1
        fi
    else
        log_success "RAM: ${TOTAL_RAM}GB"
    fi
    
    # Check disk space
    AVAILABLE_SPACE=$(df / | awk 'NR==2 {print int($4/1024/1024)}')
    if [ $AVAILABLE_SPACE -lt 40 ]; then
        log_error "Espacio en disco insuficiente. Mínimo 40GB, disponible: ${AVAILABLE_SPACE}GB"
        exit 1
    else
        log_success "Espacio en disco: ${AVAILABLE_SPACE}GB disponibles"
    fi
    
    # Check CPU cores
    CPU_CORES=$(nproc)
    if [ $CPU_CORES -lt 2 ]; then
        log_warning "Se recomiendan al menos 2 cores de CPU, detectado: ${CPU_CORES}"
    else
        log_success "CPU cores: ${CPU_CORES}"
    fi
}

install_system_dependencies() {
    log_info "Instalando dependencias del sistema (git, curl, openssl)..."

    case $OS in
        ubuntu|debian|linuxmint|pop|elementary|zorin|kali)
            apt-get update
            apt-get install -y git curl openssl ca-certificates gnupg lsb-release
            ;;
        centos|rhel|rocky|almalinux|ol|oracle|scientific)
            if command -v dnf &>/dev/null; then
                dnf install -y git curl openssl ca-certificates
            else
                yum install -y git curl openssl ca-certificates
            fi
            ;;
        fedora)
            dnf install -y git curl openssl ca-certificates
            ;;
        opensuse*|sles|suse)
            zypper install -y git curl openssl ca-certificates
            ;;
        arch|manjaro|endeavouros)
            pacman -Sy --noconfirm git curl openssl ca-certificates
            ;;
        amzn|amazon)
            yum install -y git curl openssl ca-certificates
            ;;
        *)
            log_warning "Distribución '$OS' no reconocida. Intentando con gestor de paquetes disponible..."
            if command -v apt-get &>/dev/null; then
                apt-get update && apt-get install -y git curl openssl ca-certificates
            elif command -v dnf &>/dev/null; then
                dnf install -y git curl openssl ca-certificates
            elif command -v yum &>/dev/null; then
                yum install -y git curl openssl ca-certificates
            elif command -v pacman &>/dev/null; then
                pacman -Sy --noconfirm git curl openssl ca-certificates
            elif command -v zypper &>/dev/null; then
                zypper install -y git curl openssl ca-certificates
            else
                log_warning "No se pudo instalar dependencias automáticamente"
            fi
            ;;
    esac

    log_success "Dependencias del sistema instaladas"
}

check_docker() {
    if command -v docker &> /dev/null; then
        log_success "Docker ya está instalado: $(docker --version)"
        return 0
    else
        log_warning "Docker no está instalado"
        return 1
    fi
}

install_docker() {
    log_info "Instalando Docker..."
    
    case $OS in
        ubuntu|debian)
            # Update package index
            apt-get update
            
            # Install prerequisites
            apt-get install -y \
                ca-certificates \
                curl \
                gnupg \
                lsb-release
            
            # Add Docker's official GPG key
            install -m 0755 -d /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            chmod a+r /etc/apt/keyrings/docker.gpg
            
            # Set up the repository
            echo \
              "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
              $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # Install Docker Engine
            apt-get update
            apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
            
        centos|rhel|rocky|almalinux|ol|oracle|scientific)
            # Install prerequisites
            if command -v dnf &>/dev/null; then
                dnf install -y dnf-plugins-core || yum install -y yum-utils
            else
                yum install -y yum-utils
            fi
            
            # Add Docker repository
            yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo 2>/dev/null || true
            
            # Install Docker Engine
            if command -v dnf &>/dev/null; then
                dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            else
                yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            fi
            
            # Start Docker
            systemctl start docker
            systemctl enable docker
            ;;

        fedora)
            dnf install -y dnf-plugins-core
            dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
            dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            systemctl start docker
            systemctl enable docker
            ;;

        opensuse*|sles|suse)
            zypper install -y docker docker-compose
            systemctl start docker
            systemctl enable docker
            ;;

        arch|manjaro|endeavouros)
            pacman -Sy --noconfirm docker docker-compose
            systemctl start docker
            systemctl enable docker
            ;;

        amzn|amazon)
            yum install -y docker
            systemctl start docker
            systemctl enable docker
            # Docker Compose via pip
            if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
                curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
                chmod +x /usr/local/bin/docker-compose
            fi
            ;;
            
        *)
            log_warning "Distribución '$OS' no reconocida. Intentando instalación universal de Docker..."
            if curl -fsSL https://get.docker.com | sh; then
                systemctl start docker 2>/dev/null || true
                systemctl enable docker 2>/dev/null || true
                log_success "Docker instalado via get.docker.com"
            else
                log_error "No se pudo instalar Docker automáticamente en: $OS"
                log_error "Instale Docker manualmente y vuelva a ejecutar este script."
                exit 1
            fi
            ;;
    esac
    
    log_success "Docker instalado correctamente"
}

get_server_ip() {
    # Check if VOZIPOMNI_IPV4 is already set
    if [ -n "$VOZIPOMNI_IPV4" ]; then
        SERVER_IP=$VOZIPOMNI_IPV4
        log_info "Usando IP de variable de entorno: $SERVER_IP"
    else
        # Try to detect public IP
        SERVER_IP=$(curl -s https://api.ipify.org 2>/dev/null || curl -s https://icanhazip.com 2>/dev/null || echo "")
        
        if [ -z "$SERVER_IP" ]; then
            # Fallback to local IP
            SERVER_IP=$(hostname -I | awk '{print $1}')
        fi
        
        echo -e "${YELLOW}Dirección IP detectada: $SERVER_IP${NC}"
        read -p "¿Es correcta esta IP? (s/n): " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            read -p "Ingrese la dirección IP pública del servidor: " SERVER_IP
        fi
    fi
    
    # Validate IP format
    if ! [[ $SERVER_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        log_error "Formato de IP inválido: $SERVER_IP"
        exit 1
    fi
    
    log_success "IP del servidor configurada: $SERVER_IP"
}

generate_credentials() {
    log_info "Generando credenciales seguras..."
    
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    SECRET_KEY=$(openssl rand -base64 50 | tr -d "=+/")
    ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-12)
    
    log_success "Credenciales generadas"
}

configure_firewall() {
    log_info "Configurando firewall..."
    
    # Intentar configurar firewall según lo que esté disponible en el sistema
    if command -v ufw &> /dev/null; then
        # UFW (Ubuntu, Debian y derivados)
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw allow 5060/tcp
        ufw allow 5060/udp
        ufw allow 5061/tcp
        ufw allow 5161/udp
        ufw allow 5162/udp
        ufw allow 5038/tcp
        ufw allow 10000:20000/udp
        ufw allow 8089/tcp
        ufw --force enable
        log_success "Firewall UFW configurado"
    elif command -v firewall-cmd &> /dev/null; then
        # firewalld (RHEL, CentOS, Rocky, Fedora, openSUSE)
        firewall-cmd --permanent --add-service=http 2>/dev/null || true
        firewall-cmd --permanent --add-service=https 2>/dev/null || true
        firewall-cmd --permanent --add-service=ssh 2>/dev/null || true
        firewall-cmd --permanent --add-port=5060/tcp 2>/dev/null || true
        firewall-cmd --permanent --add-port=5060/udp 2>/dev/null || true
        firewall-cmd --permanent --add-port=5061/tcp 2>/dev/null || true
        firewall-cmd --permanent --add-port=5161/udp 2>/dev/null || true
        firewall-cmd --permanent --add-port=5162/udp 2>/dev/null || true
        firewall-cmd --permanent --add-port=5038/tcp 2>/dev/null || true
        firewall-cmd --permanent --add-port=10000-20000/udp 2>/dev/null || true
        firewall-cmd --permanent --add-port=8089/tcp 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
        log_success "Firewall firewalld configurado"
    elif command -v iptables &> /dev/null; then
        # iptables directo (cualquier Linux)
        iptables -A INPUT -p tcp --dport 22 -j ACCEPT 2>/dev/null || true
        iptables -A INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
        iptables -A INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || true
        iptables -A INPUT -p tcp --dport 5060 -j ACCEPT 2>/dev/null || true
        iptables -A INPUT -p udp --dport 5060 -j ACCEPT 2>/dev/null || true
        iptables -A INPUT -p tcp --dport 5061 -j ACCEPT 2>/dev/null || true
        iptables -A INPUT -p udp --dport 5161 -j ACCEPT 2>/dev/null || true
        iptables -A INPUT -p udp --dport 5162 -j ACCEPT 2>/dev/null || true
        iptables -A INPUT -p tcp --dport 5038 -j ACCEPT 2>/dev/null || true
        iptables -A INPUT -p udp --dport 10000:20000 -j ACCEPT 2>/dev/null || true
        iptables -A INPUT -p tcp --dport 8089 -j ACCEPT 2>/dev/null || true
        log_success "Firewall iptables configurado"
    else
        log_warning "No se detectó firewall (ufw, firewalld, iptables). Configure manualmente."
    fi
}

clone_or_update_repo() {
    if [ -d "$INSTALL_DIR" ]; then
        log_info "Actualizando repositorio existente..."
        cd $INSTALL_DIR
        git fetch origin
        git pull origin main
    else
        log_info "Clonando repositorio..."
        mkdir -p /opt
        git clone https://github.com/henry0295/vozipomni.git $INSTALL_DIR
        cd $INSTALL_DIR
    fi
    
    log_success "Repositorio actualizado"
}

create_env_file() {
    log_info "Creando archivo de configuración del backend..."
    
    cat > $INSTALL_DIR/backend/.env <<EOF
# Django Settings — VoziPOmni (Generado: $(date))
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$SERVER_IP,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://$SERVER_IP,https://$SERVER_IP

# Database (network_mode: host → usa IP del servidor)
DB_NAME=vozipomni
DB_USER=vozipomni_user
DB_PASSWORD=$DB_PASSWORD
DB_HOST=$SERVER_IP
DB_PORT=5432

# Redis (network_mode: host → usa IP del servidor)
REDIS_HOST=$SERVER_IP
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD

# Asterisk (network_mode: host → usa IP del servidor)
ASTERISK_HOST=$SERVER_IP
ASTERISK_AMI_USER=admin
ASTERISK_AMI_PASSWORD=vozipomni_ami_2026
ASTERISK_CONFIG_DIR=/var/lib/asterisk/dynamic
ASTERISK_PUBLIC_IP=$SERVER_IP

# Celery
CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@$SERVER_IP:6379/0
CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@$SERVER_IP:6379/1

# Email (configurar después)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EOF

    log_success "Archivo de configuración del backend creado"
}

create_root_env_file() {
    log_info "Creando archivo .env raíz para Docker Compose (network_mode: host)..."

    cat > $INSTALL_DIR/.env <<EOF
# ============================================================================
# VoziPOmni — Docker Compose Environment (Producción)
# Generado automáticamente por install.sh — $(date)
# ============================================================================
# IMPORTANTE: En producción todos los servicios usan network_mode: host
#   por eso DB_HOST, REDIS_HOST, ASTERISK_HOST usan la IP del servidor.
# ============================================================================

# === SERVIDOR ===
VOZIPOMNI_IPV4=$SERVER_IP
NAT_IPV4=
TZ=America/Bogota

# === POSTGRESQL ===
POSTGRES_DB=vozipomni
POSTGRES_USER=vozipomni_user
POSTGRES_PASSWORD=$DB_PASSWORD

# === REDIS ===
REDIS_PASSWORD=$REDIS_PASSWORD

# === DJANGO / BACKEND ===
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$SERVER_IP,localhost,127.0.0.1
CORS_ORIGINS=http://$SERVER_IP,https://$SERVER_IP
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=120

# === CELERY ===
CELERY_LOG_LEVEL=info
CELERY_CONCURRENCY=4

# === ASTERISK ===
ASTERISK_AMI_USER=admin
ASTERISK_AMI_PASSWORD=vozipomni_ami_2026

# === FRONTEND (Nuxt 3) ===
NUXT_PUBLIC_API_BASE=/api
NUXT_PUBLIC_WS_BASE=/ws
NUXT_PUBLIC_APP_NAME=VozipOmni

# === WEBSOCKET ===
WS_PORT=8765

# === NGINX ===
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# === EMAIL (configurar después si se necesita) ===
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EOF

    chmod 600 $INSTALL_DIR/.env
    log_success "Archivo .env raíz creado"
}

update_docker_compose() {
    log_info "Configuración de Docker Compose (producción con network_mode: host)..."
    # Las credenciales se inyectan via .env raíz (create_root_env_file)
    # Los servicios usan network_mode: host y healthchecks
    log_success "Docker Compose configurado (docker-compose.prod.yml)"
}

# ─── wait_for_env — Polling HTTP estilo OmniLeads ──────────────────────────
# Espera a que el backend responda HTTP antes de continuar,
# en lugar de un sleep fijo. Máximo WAIT_TIMEOUT segundos.
# ────────────────────────────────────────────────────────────────────────────
wait_for_env() {
    local url="http://localhost:8000/api/"
    local WAIT_TIMEOUT=${1:-600}  # 10 minutos por defecto
    local WAIT_INTERVAL=10
    local elapsed=0

    log_info "Esperando a que VoziPOmni esté listo (máx ${WAIT_TIMEOUT}s)..."
    log_info "Monitoreando: $url"
    echo ""

    while [ $elapsed -lt $WAIT_TIMEOUT ]; do
        local http_code
        http_code=$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>/dev/null || echo "000")

        case $http_code in
            200|301|302|403)
                echo ""
                log_success "VoziPOmni está respondiendo (HTTP $http_code) después de ${elapsed}s"
                return 0
                ;;
            000)
                printf "  [%3ds/%ds] Esperando conexión...\\r" "$elapsed" "$WAIT_TIMEOUT"
                ;;
            *)
                printf "  [%3ds/%ds] HTTP %s — esperando...\\r" "$elapsed" "$WAIT_TIMEOUT" "$http_code"
                ;;
        esac

        sleep $WAIT_INTERVAL
        elapsed=$((elapsed + WAIT_INTERVAL))
    done

    echo ""
    log_warning "Timeout de ${WAIT_TIMEOUT}s alcanzado esperando el backend"
    log_warning "El sistema puede necesitar más tiempo para iniciar"
    log_info "Verifique manualmente: $COMPOSE_CMD -f docker-compose.prod.yml logs backend"
    return 1
}

start_services() {
    log_info "Iniciando servicios Docker..."
    
    cd $INSTALL_DIR

    # Detectar comando compose
    detect_compose_cmd
    
    # Detener servicios anteriores (si existen)
    log_info "Limpiando instalación anterior (si existe)..."
    $COMPOSE_CMD -f docker-compose.prod.yml down 2>/dev/null || true
    
    # Construir e iniciar en modo detached
    log_info "Construyendo e iniciando servicios (esto puede tardar varios minutos)..."
    $COMPOSE_CMD -f docker-compose.prod.yml up -d --build 2>&1

    # Polling HTTP en lugar de sleep fijo
    echo ""
    if wait_for_env 600; then
        log_success "Todos los servicios están operativos"
    else
        log_warning "Continuando sin confirmación del backend..."
    fi
    
    # Mostrar estado de los contenedores
    echo ""
    log_info "Estado de los servicios:"
    $COMPOSE_CMD -f docker-compose.prod.yml ps 2>/dev/null || true
    echo ""
    
    log_success "Servicios iniciados"
}

run_migrations() {
    log_info "Ejecutando migraciones de base de datos..."
    
    cd $INSTALL_DIR
    
    # Esperar a que PostgreSQL esté listo via healthcheck
    log_info "Esperando a que PostgreSQL esté disponible..."
    for i in {1..60}; do
        if $COMPOSE_CMD -f docker-compose.prod.yml exec -T postgres pg_isready -U ${POSTGRES_USER:-vozipomni_user} -d ${POSTGRES_DB:-vozipomni} > /dev/null 2>&1; then
            log_success "PostgreSQL está listo"
            break
        fi
        if [ $i -eq 60 ]; then
            log_warning "Timeout esperando PostgreSQL, intentando migraciones de todas formas..."
        fi
        printf "  Esperando PostgreSQL... (%ds)\r" "$((i*2))"
        sleep 2
    done
    echo ""
    
    # Ejecutar migraciones
    $COMPOSE_CMD -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput
    
    log_success "Migraciones completadas"
}

create_superuser() {
    log_info "Creando usuario administrador..."
    
    cd $INSTALL_DIR
    $COMPOSE_CMD -f docker-compose.prod.yml run --rm backend python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@vozipomni.local', '$ADMIN_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
EOF
    
    log_success "Usuario administrador creado"
}

save_credentials() {
    log_info "Guardando credenciales..."
    
    cat > $INSTALL_DIR/credentials.txt <<EOF
════════════════════════════════════════════════════════════
         VoziPOmni Contact Center - Credenciales
════════════════════════════════════════════════════════════

ACCESO WEB:
  URL: http://$SERVER_IP
  URL Segura: https://$SERVER_IP (configurar SSL primero)
  
ADMINISTRADOR:
  Usuario: admin
  Contraseña: $ADMIN_PASSWORD
  
ADMIN DJANGO:
  URL: http://$SERVER_IP/admin
  Usuario: admin
  Contraseña: $ADMIN_PASSWORD

API REST:
  URL: http://$SERVER_IP/api
  Token: Usar autenticación JWT
  
BASE DE DATOS:
  Host: localhost (desde el servidor)
  Puerto: 5432
  Base de datos: vozipomni
  Usuario: vozipomni
  Contraseña: $DB_PASSWORD
  
REDIS:
  Host: localhost (desde el servidor)
  Puerto: 6379
  Contraseña: $REDIS_PASSWORD

ASTERISK AMI:
  Host: localhost (desde el servidor)
  Puerto: 5038
  Usuario: admin
  Contraseña: vozipomni_ami_2026

════════════════════════════════════════════════════════════
IMPORTANTE: Guarda este archivo en un lugar seguro.
Fecha de instalación: $(date)
════════════════════════════════════════════════════════════
EOF
    
    chmod 600 $INSTALL_DIR/credentials.txt
    
    log_success "Credenciales guardadas en: $INSTALL_DIR/credentials.txt"
}

show_final_message() {
    print_header
    
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║       ¡Instalación completada exitosamente!              ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Accede a tu Contact Center en:${NC}"
    echo -e "  → ${GREEN}http://$SERVER_IP${NC}"
    echo ""
    echo -e "${BLUE}Credenciales del administrador:${NC}"
    echo -e "  Usuario: ${GREEN}admin${NC}"
    echo -e "  Contraseña: ${GREEN}$ADMIN_PASSWORD${NC}"
    echo ""
    echo -e "${YELLOW}Las credenciales completas están en:${NC}"
    echo -e "  ${GREEN}$INSTALL_DIR/credentials.txt${NC}"
    echo ""
    echo -e "${BLUE}Comandos útiles:${NC}"
    echo -e "  Ver logs:        ${GREEN}cd $INSTALL_DIR && $COMPOSE_CMD -f docker-compose.prod.yml logs -f${NC}"
    echo -e "  Reiniciar:       ${GREEN}cd $INSTALL_DIR && $COMPOSE_CMD -f docker-compose.prod.yml restart${NC}"
    echo -e "  Detener:         ${GREEN}cd $INSTALL_DIR && $COMPOSE_CMD -f docker-compose.prod.yml down${NC}"
    echo -e "  Iniciar:         ${GREEN}cd $INSTALL_DIR && $COMPOSE_CMD -f docker-compose.prod.yml up -d${NC}"
    echo ""
    echo -e "${BLUE}Próximos pasos:${NC}"
    echo -e "  1. Configurar SSL/TLS con certbot para HTTPS"
    echo -e "  2. Configurar trunks SIP para llamadas"
    echo -e "  3. Crear agentes y campañas"
    echo -e "  4. Configurar backups automáticos"
    echo ""
}

install_vozipomni() {
    print_header
    
    log_info "Iniciando instalación de VoziPOmni Contact Center v2.0..."
    echo ""
    
    detect_os
    check_system_requirements
    prepare_system
    install_system_dependencies
    echo ""
    
    # Check and install Docker
    if ! check_docker; then
        install_docker
    fi

    # Detectar compose
    detect_compose_cmd
    
    # Reiniciar Docker si daemon.json fue creado antes de instalar
    if systemctl is-active --quiet docker 2>/dev/null; then
        systemctl restart docker 2>/dev/null || true
    fi
    echo ""
    
    # Get server IP
    get_server_ip
    echo ""
    
    # Generate credentials
    generate_credentials
    echo ""
    
    # Configure firewall
    configure_firewall
    echo ""
    
    # Clone or update repository
    clone_or_update_repo
    echo ""
    
    # Create environment file
    create_env_file
    echo ""

    # Create root .env for Docker Compose
    create_root_env_file
    echo ""
    
    # Update docker-compose
    update_docker_compose
    echo ""
    
    # Start services
    start_services
    echo ""
    
    # Run migrations
    run_migrations
    echo ""
    
    # Create superuser
    create_superuser
    echo ""
    
    # Save credentials
    save_credentials
    echo ""
    
    # Show final message
    show_final_message
}

uninstall_vozipomni() {
    print_header
    
    log_warning "Esta acción eliminará VoziPOmni y todos sus datos"
    read -p "¿Está seguro? Escriba 'SI' para confirmar: " CONFIRM
    
    if [ "$CONFIRM" != "SI" ]; then
        log_info "Desinstalación cancelada"
        exit 0
    fi
    
    log_info "Deteniendo servicios..."
    cd $INSTALL_DIR 2>/dev/null && $COMPOSE_CMD -f docker-compose.prod.yml down -v
    
    log_info "Eliminando archivos..."
    rm -rf $INSTALL_DIR
    
    log_success "VoziPOmni ha sido desinstalado"
}

show_menu() {
    print_header
    
    echo -e "${BLUE}Seleccione una opción:${NC}"
    echo ""
    echo "  1) Instalar VoziPOmni"
    echo "  2) Actualizar VoziPOmni"
    echo "  3) Desinstalar VoziPOmni"
    echo "  4) Ver credenciales"
    echo "  5) Ver logs"
    echo "  6) Reiniciar servicios"
    echo "  7) Salir"
    echo ""
    read -p "Opción: " OPTION
    
    case $OPTION in
        1)
            install_vozipomni
            ;;
        2)
            log_info "Actualizando VoziPOmni..."
            detect_compose_cmd
            clone_or_update_repo
            start_services
            run_migrations
            log_success "Actualización completada"
            show_final_message
            ;;
        3)
            uninstall_vozipomni
            ;;
        4)
            if [ -f "$INSTALL_DIR/credentials.txt" ]; then
                cat $INSTALL_DIR/credentials.txt
            else
                log_error "No se encontró el archivo de credenciales"
            fi
            ;;
        5)
            cd $INSTALL_DIR && $COMPOSE_CMD -f docker-compose.prod.yml logs -f
            ;;
        6)
            cd $INSTALL_DIR && $COMPOSE_CMD -f docker-compose.prod.yml restart
            log_success "Servicios reiniciados"
            ;;
        7)
            exit 0
            ;;
        *)
            log_error "Opción inválida"
            show_menu
            ;;
    esac
}

################################################################################
# Main
################################################################################

# Detectar OS y compose al inicio para el menú
detect_os
if command -v docker &>/dev/null; then
    detect_compose_cmd 2>/dev/null || COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker compose"
fi

# If VOZIPOMNI_IPV4 is set, go straight to installation (estilo OmniLeads)
if [ -n "${VOZIPOMNI_IPV4:-}" ]; then
    install_vozipomni
else
    show_menu
fi
