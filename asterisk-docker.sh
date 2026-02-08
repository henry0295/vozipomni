#!/bin/bash
# Script de gestión de Asterisk en Docker para VoziPOmni
# Autor: VoziPOmni Team

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Funciones de utilidad
print_header() {
    echo -e "\n${CYAN}================================================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Función para verificar estado del contenedor
check_container() {
    print_header "VERIFICANDO ESTADO DEL CONTENEDOR ASTERISK"
    
    if docker ps --format '{{.Names}}' | grep -q "vozipomni_asterisk"; then
        print_success "Contenedor Asterisk está ejecutándose"
        docker ps --filter "name=vozipomni_asterisk" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        return 0
    else
        print_error "Contenedor Asterisk NO está ejecutándose"
        
        if docker ps -a --format '{{.Names}}' | grep -q "vozipomni_asterisk"; then
            print_warning "El contenedor existe pero está detenido"
            docker ps -a --filter "name=vozipomni_asterisk" --format "table {{.Names}}\t{{.Status}}"
        else
            print_error "El contenedor no existe"
        fi
        return 1
    fi
}

# Función para verificar proceso de Asterisk dentro del contenedor
check_asterisk_process() {
    print_header "VERIFICANDO PROCESO DE ASTERISK"
    
    if ! docker ps --format '{{.Names}}' | grep -q "vozipomni_asterisk"; then
        print_error "Contenedor no está ejecutándose"
        return 1
    fi
    
    echo -e "${BLUE}Procesos de Asterisk dentro del contenedor:${NC}"
    docker compose exec asterisk ps aux | grep -E '(asterisk|PID)' | grep -v grep
    
    if docker compose exec asterisk pgrep asterisk > /dev/null; then
        print_success "Proceso de Asterisk está ejecutándose"
        return 0
    else
        print_error "Proceso de Asterisk NO está ejecutándose dentro del contenedor"
        return 1
    fi
}

# Función para verificar socket de control
check_control_socket() {
    print_header "VERIFICANDO SOCKET DE CONTROL"
    
    echo -e "${BLUE}Buscando archivo asterisk.ctl:${NC}"
    docker compose exec asterisk ls -la /var/run/asterisk/ || print_error "Directorio /var/run/asterisk no existe"
    
    if docker compose exec asterisk test -S /var/run/asterisk/asterisk.ctl; then
        print_success "Socket de control existe"
        return 0
    else
        print_error "Socket de control NO existe"
        print_info "Esto indica que Asterisk no se inició correctamente"
        return 1
    fi
}

# Función para ver logs de Asterisk
show_logs() {
    print_header "LOGS DEL CONTENEDOR ASTERISK"
    
    echo -e "${BLUE}Últimas 50 líneas del log:${NC}\n"
    docker compose logs --tail=50 asterisk
    
    echo -e "\n${YELLOW}Para seguir los logs en tiempo real ejecuta:${NC}"
    echo -e "${CYAN}docker compose logs -f asterisk${NC}\n"
}

# Función para reiniciar Asterisk
restart_asterisk() {
    print_header "REINICIANDO CONTENEDOR ASTERISK"
    
    print_info "Deteniendo contenedor..."
    docker compose stop asterisk
    
    print_info "Iniciando contenedor..."
    docker compose up -d asterisk
    
    print_info "Esperando 5 segundos para que inicie..."
    sleep 5
    
    check_container
    check_asterisk_process
    check_control_socket
}

# Función para acceder a la consola CLI
asterisk_cli() {
    print_header "ACCEDIENDO A CONSOLA ASTERISK CLI"
    
    if ! docker ps --format '{{.Names}}' | grep -q "vozipomni_asterisk"; then
        print_error "Contenedor Asterisk no está ejecutándose"
        echo -e "\n${YELLOW}¿Deseas iniciarlo? (s/n):${NC} "
        read -r response
        if [[ "$response" =~ ^[SsYy]$ ]]; then
            docker compose up -d asterisk
            sleep 5
        else
            return 1
        fi
    fi
    
    if ! check_asterisk_process > /dev/null 2>&1; then
        print_error "Asterisk no está ejecutándose dentro del contenedor"
        print_warning "Intentando reiniciar..."
        restart_asterisk
        sleep 3
    fi
    
    print_info "Conectando a la consola CLI..."
    print_info "Usa 'exit' o Ctrl+C para salir\n"
    sleep 1
    
    docker compose exec asterisk asterisk -rvvvv
}

# Función para ejecutar comando Asterisk
run_asterisk_command() {
    if [ -z "$1" ]; then
        print_error "Debes especificar un comando"
        echo "Uso: $0 cmd 'core show version'"
        return 1
    fi
    
    print_header "EJECUTANDO COMANDO ASTERISK"
    echo -e "${BLUE}Comando: ${NC}$1\n"
    
    docker compose exec asterisk asterisk -rx "$1"
}

# Función para verificar configuración
check_config() {
    print_header "VERIFICANDO ARCHIVOS DE CONFIGURACIÓN"
    
    echo -e "${BLUE}Archivos de configuración en ./docker/asterisk/configs/:${NC}"
    ls -lh ./docker/asterisk/configs/
    
    echo -e "\n${BLUE}Verificando asterisk.conf:${NC}"
    grep -E "(alwaysfork|nofork)" ./docker/asterisk/configs/asterisk.conf
    
    echo -e "\n${BLUE}Verificando manager.conf (AMI):${NC}"
    if [ -f "./docker/asterisk/configs/manager.conf" ]; then
        grep -E "^\[general\]|^enabled|^bindaddr|^port" ./docker/asterisk/configs/manager.conf | head -10
    else
        print_warning "manager.conf no encontrado"
    fi
}

# Función para mostrar información del sistema
system_info() {
    print_header "INFORMACIÓN DEL SISTEMA ASTERISK"
    
    if ! docker ps --format '{{.Names}}' | grep -q "vozipomni_asterisk"; then
        print_error "Contenedor no está ejecutándose"
        return 1
    fi
    
    echo -e "${BLUE}Versión de Asterisk:${NC}"
    docker compose exec asterisk asterisk -rx "core show version"
    
    echo -e "\n${BLUE}Estado del sistema:${NC}"
    docker compose exec asterisk asterisk -rx "core show uptime"
    
    echo -e "\n${BLUE}Canales activos:${NC}"
    docker compose exec asterisk asterisk -rx "core show channels"
    
    echo -e "\n${BLUE}Endpoints PJSIP:${NC}"
    docker compose exec asterisk asterisk -rx "pjsip show endpoints"
    
    echo -e "\n${BLUE}Conexiones AMI:${NC}"
    docker compose exec asterisk asterisk -rx "manager show connected"
}

# Función para rebuild del contenedor
rebuild_container() {
    print_header "RECONSTRUYENDO CONTENEDOR ASTERISK"
    
    print_warning "Esto detendrá y reconstruirá completamente el contenedor"
    echo -e "${YELLOW}¿Estás seguro? (s/n):${NC} "
    read -r response
    
    if [[ ! "$response" =~ ^[SsYy]$ ]]; then
        print_info "Operación cancelada"
        return 0
    fi
    
    print_info "Deteniendo contenedor..."
    docker compose stop asterisk
    
    print_info "Eliminando contenedor..."
    docker compose rm -f asterisk
    
    print_info "Reconstruyendo imagen..."
    docker compose build --no-cache asterisk
    
    print_info "Iniciando contenedor..."
    docker compose up -d asterisk
    
    print_info "Esperando 10 segundos para que inicie..."
    sleep 10
    
    check_container
    check_asterisk_process
    check_control_socket
}

# Menú principal
show_menu() {
    clear
    print_header "GESTOR DE ASTERISK - VoziPOmni"
    
    echo -e "${YELLOW}1.${NC} Verificar estado completo"
    echo -e "${YELLOW}2.${NC} Acceder a consola CLI (asterisk -r)"
    echo -e "${YELLOW}3.${NC} Ver logs del contenedor"
    echo -e "${YELLOW}4.${NC} Reiniciar contenedor Asterisk"
    echo -e "${YELLOW}5.${NC} Ejecutar comando Asterisk"
    echo -e "${YELLOW}6.${NC} Ver información del sistema"
    echo -e "${YELLOW}7.${NC} Verificar configuración"
    echo -e "${YELLOW}8.${NC} Reconstruir contenedor (full rebuild)"
    echo -e "${RED}0.${NC} Salir"
    echo ""
}

# Main
if [ "$1" = "status" ]; then
    check_container
    check_asterisk_process
    check_control_socket
elif [ "$1" = "cli" ]; then
    asterisk_cli
elif [ "$1" = "cmd" ]; then
    run_asterisk_command "$2"
elif [ "$1" = "logs" ]; then
    show_logs
elif [ "$1" = "restart" ]; then
    restart_asterisk
elif [ "$1" = "info" ]; then
    system_info
elif [ "$1" = "config" ]; then
    check_config
elif [ "$1" = "rebuild" ]; then
    rebuild_container
elif [ "$1" = "menu" ] || [ -z "$1" ]; then
    while true; do
        show_menu
        read -p "Selecciona una opción: " choice
        
        case $choice in
            1)
                check_container
                check_asterisk_process
                check_control_socket
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            2)
                asterisk_cli
                ;;
            3)
                show_logs
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            4)
                restart_asterisk
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            5)
                echo -e "\n${BLUE}Ingresa el comando Asterisk:${NC} "
                read -r cmd
                run_asterisk_command "$cmd"
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            6)
                system_info
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            7)
                check_config
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            8)
                rebuild_container
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            0)
                print_info "¡Hasta luego!"
                exit 0
                ;;
            *)
                print_error "Opción inválida"
                sleep 2
                ;;
        esac
    done
else
    echo "Uso: $0 [opción]"
    echo ""
    echo "Opciones:"
    echo "  status   - Verificar estado completo"
    echo "  cli      - Acceder a consola CLI"
    echo "  cmd      - Ejecutar comando Asterisk"
    echo "  logs     - Ver logs del contenedor"
    echo "  restart  - Reiniciar contenedor"
    echo "  info     - Ver información del sistema"
    echo "  config   - Verificar configuración"
    echo "  rebuild  - Reconstruir contenedor"
    echo "  menu     - Mostrar menú interactivo (por defecto)"
    echo ""
    echo "Ejemplos:"
    echo "  $0 cli"
    echo "  $0 cmd 'core show version'"
    echo "  $0 status"
fi
