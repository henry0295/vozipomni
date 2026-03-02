#!/bin/bash
#============================================================================
# Herramientas de Debugging VoIP para VoziPOmni
#============================================================================
# Proporciona comandos útiles para debugging de llamadas SIP/RTP
# Uso: ./voip-debug.sh [comando]
#============================================================================

COMPOSE_FILE="docker-compose.prod.yml"
INSTALL_DIR="/opt/vozipomni"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  $1"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
}

function print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

function print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

function print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

function print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function show_help() {
    cat << EOF
╔════════════════════════════════════════════════════════════╗
║         VoziPOmni - Herramientas de Debugging VoIP        ║
╚════════════════════════════════════════════════════════════╝

USO: $0 [comando] [opciones]

COMANDOS PRINCIPALES:
  sngrep              Captura SIP en tiempo real (interfaz visual)
  sngrep-kamailio     sngrep específico para Kamailio
  sngrep-asterisk     sngrep específico para Asterisk
  
  rtp                 Captura tráfico RTP (puertos 23000-23100)
  sip                 Captura tráfico SIP (puertos 5060, 5080, 5161, 5162)
  
  rtpengine-stats     Estadísticas de RTPEngine
  rtpengine-sessions  Sesiones activas de RTPEngine
  
  calls-active        Llamadas activas en Asterisk
  channels            Canales activos en Asterisk
  pjsip-endpoints     Endpoints PJSIP registrados
  pjsip-contacts      Contactos PJSIP
  
  kamailio-status     Estado de Kamailio
  kamailio-stats      Estadísticas de Kamailio
  
  logs [servicio]     Ver logs de un servicio
  logs-follow         Seguir logs en tiempo real
  
  network-test        Probar conectividad de red
  port-test           Verificar puertos abiertos

EJEMPLOS:
  $0 sngrep                    # Captura SIP visual
  $0 rtp                       # Ver tráfico RTP
  $0 rtpengine-stats          # Estadísticas RTPEngine
  $0 calls-active             # Llamadas en curso
  $0 logs kamailio            # Ver logs de Kamailio

Para salir de las capturas interactivas, presiona Ctrl+C o Q

EOF
}

function sngrep_kamailio() {
    print_header "SNGREP - Kamailio (puerto 5060)"
    print_info "Capturando tráfico SIP en Kamailio..."
    print_warning "Presiona 'Q' o Ctrl+C para salir"
    echo ""
    docker compose -f "$COMPOSE_FILE" exec kamailio sngrep -d lo -d eth0 port 5060
}

function sngrep_asterisk() {
    print_header "SNGREP - Asterisk (puerto 5080)"
    print_info "Capturando tráfico SIP en Asterisk..."
    print_warning "Presiona 'Q' o Ctrl+C para salir"
    echo ""
    docker compose -f "$COMPOSE_FILE" exec asterisk sngrep -d lo -d eth0 port 5080
}

function sngrep_all() {
    print_header "SNGREP - Todos los puertos SIP"
    print_info "Capturando SIP: 5060, 5080, 5161, 5162..."
    print_warning "Presiona 'Q' o Ctrl+C para salir"
    echo ""
    docker compose -f "$COMPOSE_FILE" exec kamailio sngrep -d lo -d eth0 'port 5060 or port 5080 or port 5161 or port 5162'
}

function capture_rtp() {
    print_header "Captura de Tráfico RTP"
    print_info "Capturando RTP en puertos 23000-23100 (RTPEngine)..."
    print_warning "Presiona Ctrl+C para detener"
    echo ""
    docker compose -f "$COMPOSE_FILE" exec rtpengine tcpdump -i any -n 'udp portrange 23000-23100' -v
}

function capture_sip() {
    print_header "Captura de Tráfico SIP (texto)"
    print_info "Capturando todos los puertos SIP..."
    print_warning "Presiona Ctrl+C para detener"
    echo ""
    docker compose -f "$COMPOSE_FILE" exec kamailio ngrep -W byline -d any port 5060 or port 5080 or port 5161 or port 5162
}

function rtpengine_stats() {
    print_header "Estadísticas de RTPEngine"
    docker compose -f "$COMPOSE_FILE" exec rtpengine rtpengine-ctl list numsessions || {
        print_warning "rtpengine-ctl no disponible, intentando alternativa..."
        docker compose -f "$COMPOSE_FILE" logs rtpengine | tail -20
    }
}

function rtpengine_sessions() {
    print_header "Sesiones Activas de RTPEngine"
    docker compose -f "$COMPOSE_FILE" exec rtpengine rtpengine-ctl list || {
        print_warning "rtpengine-ctl no disponible"
    }
}

function calls_active() {
    print_header "Llamadas Activas en Asterisk"
    docker compose -f "$COMPOSE_FILE" exec asterisk asterisk -rx "core show calls"
}

function channels_active() {
    print_header "Canales Activos en Asterisk"
    docker compose -f "$COMPOSE_FILE" exec asterisk asterisk -rx "core show channels"
}

function pjsip_endpoints() {
    print_header "Endpoints PJSIP Registrados"
    docker compose -f "$COMPOSE_FILE" exec asterisk asterisk -rx "pjsip show endpoints"
}

function pjsip_contacts() {
    print_header "Contactos PJSIP"
    docker compose -f "$COMPOSE_FILE" exec asterisk asterisk -rx "pjsip show contacts"
}

function kamailio_status() {
    print_header "Estado de Kamailio"
    docker compose -f "$COMPOSE_FILE" exec kamailio kamcmd stats.get_statistics all 2>/dev/null || {
        print_warning "kamcmd no disponible, mostrando logs..."
        docker compose -f "$COMPOSE_FILE" logs kamailio | tail -20
    }
}

function kamailio_stats() {
    print_header "Estadísticas de Kamailio"
    docker compose -f "$COMPOSE_FILE" exec kamailio kamcmd core.uptime 2>/dev/null || {
        print_info "Estado del proceso:"
        docker compose -f "$COMPOSE_FILE" ps kamailio
    }
}

function show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        print_error "Especifica un servicio: kamailio, asterisk, rtpengine, backend, etc."
        return 1
    fi
    print_header "Logs de $service"
    docker compose -f "$COMPOSE_FILE" logs --tail=100 "$service"
}

function logs_follow() {
    print_header "Logs en Tiempo Real (todos los servicios)"
    print_warning "Presiona Ctrl+C para detener"
    echo ""
    docker compose -f "$COMPOSE_FILE" logs -f
}

function network_test() {
    print_header "Prueba de Conectividad de Red"
    
    print_info "Probando conectividad entre servicios..."
    echo ""
    
    echo -e "${YELLOW}Kamailio → Asterisk (5080):${NC}"
    docker compose -f "$COMPOSE_FILE" exec kamailio nc -zv 127.0.0.1 5080 2>&1 || echo "FAIL"
    
    echo -e "${YELLOW}Kamailio → RTPEngine (22222):${NC}"
    docker compose -f "$COMPOSE_FILE" exec kamailio nc -zuv 127.0.0.1 22222 2>&1 || echo "FAIL"
    
    echo -e "${YELLOW}Backend → Asterisk AMI (5038):${NC}"
    docker compose -f "$COMPOSE_FILE" exec backend nc -zv 127.0.0.1 5038 2>&1 || echo "FAIL"
    
    echo ""
    print_info "Verificando puertos en uso:"
    docker compose -f "$COMPOSE_FILE" exec asterisk ss -tulpn | grep -E ":(5060|5080|5161|5162|5038)" || true
}

function port_test() {
    print_header "Verificación de Puertos"
    
    print_info "Puertos SIP/VoIP esperados:"
    echo ""
    echo -e "${CYAN}Puerto    Protocolo  Servicio         Estado${NC}"
    echo "─────────────────────────────────────────────────────"
    
    check_port 5060 "UDP/TCP" "Kamailio SIP"
    check_port 5080 "UDP/TCP" "Asterisk SIP interno"
    check_port 5161 "UDP" "Asterisk trunk sin NAT"
    check_port 5162 "UDP" "Asterisk trunk con NAT"
    check_port 5038 "TCP" "Asterisk AMI"
    check_port 22222 "UDP" "RTPEngine control"
    check_port 8080 "TCP" "WebSocket"
    check_port 8000 "TCP" "Backend Django"
}

function check_port() {
    local port=$1
    local proto=$2
    local desc=$3
    local status=$(ss -tulpn | grep ":$port " > /dev/null 2>&1 && echo -e "${GREEN}✓ ABIERTO${NC}" || echo -e "${RED}✗ CERRADO${NC}")
    printf "%-9s %-10s %-20s %s\n" "$port" "$proto" "$desc" "$status"
}

# Main script
cd "$INSTALL_DIR" 2>/dev/null || {
    print_error "No se encuentra el directorio $INSTALL_DIR"
    exit 1
}

case "${1:-help}" in
    sngrep)
        sngrep_all
        ;;
    sngrep-kamailio)
        sngrep_kamailio
        ;;
    sngrep-asterisk)
        sngrep_asterisk
        ;;
    rtp)
        capture_rtp
        ;;
    sip)
        capture_sip
        ;;
    rtpengine-stats)
        rtpengine_stats
        ;;
    rtpengine-sessions)
        rtpengine_sessions
        ;;
    calls-active)
        calls_active
        ;;
    channels)
        channels_active
        ;;
    pjsip-endpoints)
        pjsip_endpoints
        ;;
    pjsip-contacts)
        pjsip_contacts
        ;;
    kamailio-status)
        kamailio_status
        ;;
    kamailio-stats)
        kamailio_stats
        ;;
    logs)
        show_logs "$2"
        ;;
    logs-follow)
        logs_follow
        ;;
    network-test)
        network_test
        ;;
    port-test)
        port_test
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Comando desconocido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
