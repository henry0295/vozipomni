#!/bin/bash
# Script de verificación PJSIP para VoziPOmni
# Autor: VoziPOmni Team

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

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

# Función para ejecutar comando Asterisk
run_ast_cmd() {
    docker compose exec asterisk asterisk -rx "$1" 2>/dev/null
}

# Verificar que el contenedor esté ejecutándose
check_container() {
    if ! docker ps --format '{{.Names}}' | grep -q "vozipomni_asterisk"; then
        print_error "Contenedor Asterisk no está ejecutándose"
        echo -e "\n${YELLOW}Ejecuta: docker compose up -d asterisk${NC}\n"
        exit 1
    fi
}

# Verificar módulos PJSIP
check_modules() {
    print_header "VERIFICANDO MÓDULOS PJSIP"
    
    local modules=(
        "chan_pjsip.so"
        "res_pjsip.so"
        "res_pjsip_session.so"
        "res_pjsip_endpoint_identifier_user.so"
    )
    
    for module in "${modules[@]}"; do
        if run_ast_cmd "module show like $module" | grep -q "Running"; then
            print_success "$module está cargado"
        else
            print_error "$module NO está cargado"
        fi
    done
}

# Verificar transportes
check_transports() {
    print_header "VERIFICANDO TRANSPORTES PJSIP"
    
    echo -e "${BLUE}Transportes configurados:${NC}\n"
    run_ast_cmd "pjsip show transports"
    
    echo ""
    
    if run_ast_cmd "pjsip show transports" | grep -q "transport-udp"; then
        print_success "Transport UDP configurado"
    else
        print_warning "Transport UDP no encontrado"
    fi
    
    if run_ast_cmd "pjsip show transports" | grep -q "transport-tcp"; then
        print_success "Transport TCP configurado"
    else
        print_warning "Transport TCP no encontrado"
    fi
    
    if run_ast_cmd "pjsip show transports" | grep -q "transport-wss"; then
        print_success "Transport WSS (WebRTC) configurado"
    else
        print_warning "Transport WSS no encontrado (WebRTC no disponible)"
    fi
}

# Verificar endpoints
check_endpoints() {
    print_header "VERIFICANDO ENDPOINTS (EXTENSIONES)"
    
    echo -e "${BLUE}Endpoints configurados:${NC}\n"
    local endpoints_output=$(run_ast_cmd "pjsip show endpoints")
    echo "$endpoints_output"
    
    echo ""
    
    local endpoint_count=$(echo "$endpoints_output" | grep -c "Endpoint:")
    
    if [ "$endpoint_count" -gt 0 ]; then
        print_success "Se encontraron $endpoint_count endpoints configurados"
    else
        print_warning "No se encontraron endpoints configurados"
        echo -e "\n${YELLOW}Agrega endpoints en: /etc/asterisk/pjsip.conf${NC}"
    fi
}

# Verificar contactos (extensiones registradas)
check_contacts() {
    print_header "VERIFICANDO EXTENSIONES REGISTRADAS"
    
    echo -e "${BLUE}Contactos activos (extensiones registradas):${NC}\n"
    local contacts_output=$(run_ast_cmd "pjsip show contacts")
    echo "$contacts_output"
    
    echo ""
    
    local contact_count=$(echo "$contacts_output" | grep -c "Avail")
    
    if [ "$contact_count" -gt 0 ]; then
        print_success "$contact_count extensiones registradas y disponibles"
    else
        print_warning "No hay extensiones registradas"
        echo -e "\n${YELLOW}Las extensiones deben registrarse desde softphones/teléfonos IP${NC}"
    fi
}

# Verificar canales activos
check_channels() {
    print_header "VERIFICANDO CANALES ACTIVOS"
    
    echo -e "${BLUE}Canales PJSIP activos:${NC}\n"
    local channels_output=$(run_ast_cmd "pjsip show channels")
    echo "$channels_output"
    
    echo ""
    
    if echo "$channels_output" | grep -q "PJSIP"; then
        print_info "Hay llamadas activas en curso"
    else
        print_info "No hay llamadas activas"
    fi
}

# Verificar configuración de archivos
check_config_files() {
    print_header "VERIFICANDO ARCHIVOS DE CONFIGURACIÓN"
    
    echo -e "${BLUE}Verificando pjsip.conf:${NC}"
    if docker compose exec asterisk test -f /etc/asterisk/pjsip.conf; then
        print_success "/etc/asterisk/pjsip.conf existe"
        
        # Contar endpoints definidos
        local endpoint_defs=$(docker compose exec asterisk grep -c "^\[.*\].*endpoint" /etc/asterisk/pjsip.conf 2>/dev/null || echo "0")
        echo -e "${BLUE}   Endpoints definidos en archivo: $endpoint_defs${NC}"
    else
        print_error "/etc/asterisk/pjsip.conf no existe"
    fi
    
    echo -e "\n${BLUE}Verificando extensions.conf:${NC}"
    if docker compose exec asterisk test -f /etc/asterisk/extensions.conf; then
        print_success "/etc/asterisk/extensions.conf existe"
        
        # Verificar si usa PJSIP en dialplan
        if docker compose exec asterisk grep -q "PJSIP" /etc/asterisk/extensions.conf; then
            print_success "Dialplan usa PJSIP (correcto)"
        else
            print_warning "Dialplan no parece usar PJSIP"
        fi
    else
        print_error "/etc/asterisk/extensions.conf no existe"
    fi
}

# Verificar puertos
check_ports() {
    print_header "VERIFICANDO PUERTOS DE RED"
    
    echo -e "${BLUE}Puertos expuestos por el contenedor:${NC}\n"
    docker ps --filter "name=vozipomni_asterisk" --format "table {{.Names}}\t{{.Ports}}" | grep -E "(5060|8089|10000)"
    
    echo -e "\n${BLUE}Verificando puertos dentro del contenedor:${NC}\n"
    
    # Verificar puerto SIP 5060
    if docker compose exec asterisk netstat -tuln 2>/dev/null | grep -q ":5060"; then
        print_success "Puerto 5060 (SIP) está escuchando"
    else
        print_warning "Puerto 5060 (SIP) no está escuchando"
    fi
    
    # Verificar puerto WebRTC 8089
    if docker compose exec asterisk netstat -tuln 2>/dev/null | grep -q ":8089"; then
        print_success "Puerto 8089 (WebRTC WSS) está escuchando"
    else
        print_warning "Puerto 8089 (WebRTC WSS) no está escuchando"
    fi
}

# Diagnóstico completo
full_diagnostic() {
    clear
    print_header "DIAGNÓSTICO COMPLETO PJSIP - VoziPOmni"
    
    check_container
    check_modules
    check_transports
    check_config_files
    check_endpoints
    check_contacts
    check_channels
    check_ports
    
    print_header "RESUMEN Y RECOMENDACIONES"
    
    local issues=0
    
    # Verificar problemas comunes
    if ! run_ast_cmd "module show like chan_pjsip.so" | grep -q "Running"; then
        print_error "Módulo chan_pjsip no está cargado"
        echo -e "   ${YELLOW}Solución: Verificar logs y reconstruir contenedor${NC}"
        ((issues++))
    fi
    
    if ! run_ast_cmd "pjsip show endpoints" | grep -q "Endpoint:"; then
        print_warning "No hay endpoints configurados"
        echo -e "   ${YELLOW}Solución: Agregar endpoints en pjsip.conf${NC}"
        ((issues++))
    fi
    
    if ! run_ast_cmd "pjsip show contacts" | grep -q "Avail"; then
        print_warning "No hay extensiones registradas"
        echo -e "   ${YELLOW}Solución: Registrar softphones con las credenciales de pjsip.conf${NC}"
        ((issues++))
    fi
    
    if [ $issues -eq 0 ]; then
        echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        print_success "Sistema PJSIP configurado correctamente"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    else
        echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        print_warning "Se encontraron $issues problemas/advertencias"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    fi
    
    echo -e "${BLUE}Comandos útiles:${NC}"
    echo -e "  ${CYAN}Ver endpoints:${NC}       docker compose exec asterisk asterisk -rx 'pjsip show endpoints'"
    echo -e "  ${CYAN}Ver registrados:${NC}     docker compose exec asterisk asterisk -rx 'pjsip show contacts'"
    echo -e "  ${CYAN}Recargar PJSIP:${NC}      docker compose exec asterisk asterisk -rx 'pjsip reload'"
    echo -e "  ${CYAN}Activar debug:${NC}       docker compose exec asterisk asterisk -rx 'pjsip set logger on'"
    echo ""
}

# Menú interactivo
show_menu() {
    clear
    print_header "VERIFICADOR PJSIP - VoziPOmni"
    
    echo -e "${YELLOW}1.${NC} Diagnóstico completo"
    echo -e "${YELLOW}2.${NC} Ver endpoints configurados"
    echo -e "${YELLOW}3.${NC} Ver extensiones registradas"
    echo -e "${YELLOW}4.${NC} Ver canales activos"
    echo -e "${YELLOW}5.${NC} Ver transportes"
    echo -e "${YELLOW}6.${NC} Verificar módulos"
    echo -e "${YELLOW}7.${NC} Activar logging PJSIP"
    echo -e "${YELLOW}8.${NC} Recargar configuración PJSIP"
    echo -e "${RED}0.${NC} Salir"
    echo ""
}

# Main
check_container

if [ "$1" = "full" ] || [ "$1" = "diagnostic" ]; then
    full_diagnostic
elif [ "$1" = "endpoints" ]; then
    check_endpoints
elif [ "$1" = "contacts" ]; then
    check_contacts
elif [ "$1" = "channels" ]; then
    check_channels
elif [ "$1" = "transports" ]; then
    check_transports
elif [ "$1" = "modules" ]; then
    check_modules
elif [ "$1" = "menu" ] || [ -z "$1" ]; then
    while true; do
        show_menu
        read -p "Selecciona una opción: " choice
        
        case $choice in
            1)
                full_diagnostic
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            2)
                check_endpoints
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            3)
                check_contacts
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            4)
                check_channels
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            5)
                check_transports
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            6)
                check_modules
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            7)
                print_info "Activando logging PJSIP..."
                run_ast_cmd "pjsip set logger on"
                print_success "Logging PJSIP activado"
                echo -e "${BLUE}Ver logs: docker compose logs -f asterisk${NC}"
                echo -e "\n${YELLOW}Presiona Enter para continuar...${NC}"
                read
                ;;
            8)
                print_info "Recargando configuración PJSIP..."
                run_ast_cmd "pjsip reload"
                print_success "Configuración PJSIP recargada"
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
    echo "  full       - Diagnóstico completo"
    echo "  endpoints  - Ver endpoints configurados"
    echo "  contacts   - Ver extensiones registradas"
    echo "  channels   - Ver canales activos"
    echo "  transports - Ver transportes"
    echo "  modules    - Verificar módulos"
    echo "  menu       - Mostrar menú interactivo (por defecto)"
    echo ""
    echo "Ejemplos:"
    echo "  $0 full"
    echo "  $0 endpoints"
fi
