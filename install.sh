#!/bin/bash

################################################################################
# VoziPOmni Contact Center - Installation Script
# Version: 1.0.0
# Compatible with: Ubuntu 20.04+, Debian 11+, CentOS 8+, Rocky Linux 8+, RHEL 8+
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation directory
INSTALL_DIR="/opt/vozipomni"
BACKUP_DIR="/opt/vozipomni/backups"

# Check if script is run as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Este script debe ejecutarse como root o con sudo${NC}"
   exit 1
fi

################################################################################
# Functions
################################################################################

print_header() {
    clear
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}║          VoziPOmni Contact Center Installer v1.0          ║${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}║          Sistema de Contact Center Omnicanal              ║${NC}"
    echo -e "${BLUE}║          Powered by Django, React & Asterisk               ║${NC}"
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
    else
        log_error "No se pudo detectar el sistema operativo"
        exit 1
    fi
    
    log_info "Sistema operativo detectado: $OS_NAME $OS_VERSION"
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
        ubuntu|debian)
            apt-get update
            apt-get install -y git curl openssl ca-certificates
            ;;
        centos|rhel|rocky|almalinux)
            yum install -y git curl openssl ca-certificates
            ;;
        *)
            log_warning "No se instalaron dependencias: sistema no soportado"
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
            
        centos|rhel|rocky|almalinux)
            # Install prerequisites
            yum install -y yum-utils
            
            # Add Docker repository
            yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            
            # Install Docker Engine
            yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            
            # Start Docker
            systemctl start docker
            systemctl enable docker
            ;;
            
        *)
            log_error "Sistema operativo no soportado: $OS"
            exit 1
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
    
    case $OS in
        ubuntu|debian)
            if command -v ufw &> /dev/null; then
                # Allow SSH
                ufw allow 22/tcp
                # Allow HTTP/HTTPS
                ufw allow 80/tcp
                ufw allow 443/tcp
                # Allow SIP
                ufw allow 5060/tcp
                ufw allow 5060/udp
                ufw allow 5061/tcp
                # Allow SIP Trunks
                ufw allow 5161/udp
                ufw allow 5162/udp
                # Allow AMI (solo red interna)
                ufw allow 5038/tcp
                # Allow RTP media
                ufw allow 10000:20000/udp
                # Allow WebSocket
                ufw allow 8089/tcp
                
                # Enable firewall if not active
                ufw --force enable
                log_success "Firewall UFW configurado"
            else
                log_warning "UFW no está instalado"
            fi
            ;;
            
        centos|rhel|rocky|almalinux)
            if command -v firewall-cmd &> /dev/null; then
                # Allow services
                firewall-cmd --permanent --add-service=http
                firewall-cmd --permanent --add-service=https
                firewall-cmd --permanent --add-service=ssh
                # Allow SIP
                firewall-cmd --permanent --add-port=5060/tcp
                firewall-cmd --permanent --add-port=5060/udp
                firewall-cmd --permanent --add-port=5061/tcp
                # Allow SIP Trunks
                firewall-cmd --permanent --add-port=5161/udp
                firewall-cmd --permanent --add-port=5162/udp
                # Allow AMI
                firewall-cmd --permanent --add-port=5038/tcp
                # Allow RTP
                firewall-cmd --permanent --add-port=10000-20000/udp
                # Allow WebSocket
                firewall-cmd --permanent --add-port=8089/tcp
                
                firewall-cmd --reload
                log_success "Firewall configurado"
            else
                log_warning "firewalld no está instalado"
            fi
            ;;
    esac
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
    log_info "Creando archivo de configuración..."
    
    cat > $INSTALL_DIR/backend/.env <<EOF
# Django Settings
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$SERVER_IP,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://$SERVER_IP,https://$SERVER_IP

# Database
DB_NAME=vozipomni
DB_USER=vozipomni
DB_PASSWORD=$DB_PASSWORD
DB_HOST=postgres
DB_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD

# Asterisk
ASTERISK_HOST=asterisk
ASTERISK_AMI_USER=admin
ASTERISK_AMI_PASSWORD=vozipomni_ami_2026
ASTERISK_CONFIG_DIR=/etc/asterisk
ASTERISK_PUBLIC_IP=$SERVER_IP

# Celery
CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@redis:6379/0
CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@redis:6379/0

# Email (opcional - configurar después)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EOF

    log_success "Archivo de configuración creado"
}

create_root_env_file() {
    log_info "Creando archivo .env raíz para Docker Compose..."

    cat > $INSTALL_DIR/.env <<EOF
# Docker Compose environment variables
# Generado por install.sh - $(date)

# IP pública del servidor (usada por trunk-nat-transport)
VOZIPOMNI_IPV4=$SERVER_IP

# Credenciales base de datos
POSTGRES_DB=vozipomni_db
POSTGRES_USER=vozipomni_user
POSTGRES_PASSWORD=$DB_PASSWORD

# Redis
REDIS_PASSWORD=$REDIS_PASSWORD

# Django
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=$SERVER_IP,localhost,127.0.0.1
CORS_ORIGINS=http://$SERVER_IP,https://$SERVER_IP

# Asterisk AMI
ASTERISK_AMI_USER=admin
ASTERISK_AMI_PASSWORD=vozipomni_ami_2026

# Frontend
NUXT_PUBLIC_API_BASE=/api
NUXT_PUBLIC_WS_BASE=/ws
EOF

    chmod 600 $INSTALL_DIR/.env
    log_success "Archivo .env raíz creado"
}

update_docker_compose() {
    log_info "Configuración de Docker Compose (producción)..."
    # Las credenciales se inyectan via .env raíz (create_root_env_file)
    # No es necesario sed sobre docker-compose.prod.yml
    log_success "Docker Compose configurado (usando docker-compose.prod.yml)"
}

start_services() {
    log_info "Iniciando servicios Docker..."
    
    cd $INSTALL_DIR
    
    # Detener servicios y eliminar volúmenes para instalación limpia
    log_info "Limpiando instalación anterior (si existe)..."
    docker compose -f docker-compose.prod.yml down -v 2>/dev/null || true
    
    # Iniciar servicios (producción)
    log_info "Construyendo e iniciando servicios (esto puede tardar unos minutos)..."
    docker compose -f docker-compose.prod.yml up -d --build
    
    log_info "Esperando a que los servicios estén listos..."
    sleep 30
    
    log_success "Servicios iniciados"
}

run_migrations() {
    log_info "Ejecutando migraciones de base de datos..."
    
    cd $INSTALL_DIR
    
    # Esperar a que PostgreSQL esté listo
    log_info "Esperando a que PostgreSQL esté disponible..."
    for i in {1..30}; do
        if docker compose -f docker-compose.prod.yml exec -T postgres pg_isready -U ${POSTGRES_USER:-vozipomni_user} -d ${POSTGRES_DB:-vozipomni} > /dev/null 2>&1; then
            log_success "PostgreSQL está listo"
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""
    
    # Ejecutar migraciones usando run en lugar de exec
    docker compose -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput
    
    log_success "Migraciones completadas"
}

create_superuser() {
    log_info "Creando usuario administrador..."
    
    cd $INSTALL_DIR
    docker compose -f docker-compose.prod.yml run --rm backend python manage.py shell <<EOF
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
  Contraseña: VoziPOmni2026!

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
    echo -e "  Ver logs:        ${GREEN}cd $INSTALL_DIR && docker compose -f docker-compose.prod.yml logs -f${NC}"
    echo -e "  Reiniciar:       ${GREEN}cd $INSTALL_DIR && docker compose -f docker-compose.prod.yml restart${NC}"
    echo -e "  Detener:         ${GREEN}cd $INSTALL_DIR && docker compose -f docker-compose.prod.yml down${NC}"
    echo -e "  Iniciar:         ${GREEN}cd $INSTALL_DIR && docker compose -f docker-compose.prod.yml up -d${NC}"
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
    
    log_info "Iniciando instalación de VoziPOmni Contact Center..."
    echo ""
    
    detect_os
    check_system_requirements
    install_system_dependencies
    echo ""
    
    # Check and install Docker
    if ! check_docker; then
        install_docker
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
    cd $INSTALL_DIR 2>/dev/null && docker compose -f docker-compose.prod.yml down -v
    
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
            cd $INSTALL_DIR && docker compose -f docker-compose.prod.yml logs -f
            ;;
        6)
            cd $INSTALL_DIR && docker compose -f docker-compose.prod.yml restart
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

# If VOZIPOMNI_IPV4 is set, go straight to installation
if [ -n "$VOZIPOMNI_IPV4" ]; then
    install_vozipomni
else
    show_menu
fi
