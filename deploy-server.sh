#!/bin/bash
################################################################################
# VoziPOmni Contact Center — Script de Actualización Rápida en Servidor
#
# Uso (desde el directorio de instalación /opt/vozipomni):
#   sudo bash deploy-server.sh
#
# Equivalente a:
#   sudo bash deploy.sh --update <IP>
# pero sin reinstalar Docker ni el sistema operativo.
#
# Qué hace este script:
#   1. git pull      — descarga el código más reciente
#   2. docker build  — reconstruye imágenes con el nuevo código
#   3. docker up -d  — reinicia contenedores cambiados
#   4. migrate       — aplica migraciones de base de datos pendientes
#   5. collectstatic — actualiza archivos estáticos
#   6. PJSIP reload  — recarga configuración de troncales SIP
#   7. dtmf_mode fix — corrige rfc2833 → rfc4733 en troncales existentes
#
# Qué NO hace:
#   - No toca los volúmenes de datos (PostgreSQL, grabaciones, configuraciones)
#   - No regenera credenciales ni .env
#   - No reinstala Docker ni el sistema operativo
################################################################################

set -Eeuo pipefail

# ─── Colores ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ─── Manejo de errores ───────────────────────────────────────────────────────
on_error() {
    local code=$? line=${BASH_LINENO[0]}
    echo ""
    log_error "Falló en la línea $line (código: $code)"
    echo ""
    echo "Para diagnóstico ejecute:"
    echo "  $COMPOSE_CMD -f docker-compose.prod.yml logs --tail=50 backend"
    echo "  $COMPOSE_CMD -f docker-compose.prod.yml ps"
    exit $code
}
trap on_error ERR

# ─── Detectar directorio de instalación ─────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$SCRIPT_DIR}"

# Si se ejecuta desde otro lugar, intentar /opt/vozipomni
if [ ! -f "$INSTALL_DIR/docker-compose.prod.yml" ]; then
    INSTALL_DIR="/opt/vozipomni"
fi

if [ ! -f "$INSTALL_DIR/docker-compose.prod.yml" ]; then
    log_error "No se encontró docker-compose.prod.yml en $INSTALL_DIR"
    log_error "Ejecuta desde el directorio de instalación:"
    log_error "  cd /opt/vozipomni && sudo bash deploy-server.sh"
    exit 1
fi

cd "$INSTALL_DIR"

# ─── Detectar docker compose ─────────────────────────────────────────────────
COMPOSE_CMD=""
if docker compose version &>/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
else
    log_error "docker compose no encontrado. Instala Docker primero."
    exit 1
fi

# Silenciar mensajes del kernel (veth/bridge en consola)
if [ -w /proc/sys/kernel/printk ]; then
    echo "1 4 1 7" > /proc/sys/kernel/printk 2>/dev/null || true
fi

# ─── Banner ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        VoziPOmni — Actualización Rápida en Servidor        ║${NC}"
echo -e "${BLUE}║   Los datos (BD, grabaciones, .env) NO se modifican        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "Directorio: $INSTALL_DIR"
log_info "Compose:    $COMPOSE_CMD"
echo ""

# ─── Verificar root ──────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    log_error "Ejecuta con sudo: sudo bash deploy-server.sh"
    exit 1
fi

# ─── PASO 1: Actualizar código desde GitHub ──────────────────────────────────
echo -e "${YELLOW}▶  Paso 1/7 — Descargando código más reciente...${NC}"

# Guardar cambios locales sin perderlos (y recordar si había algo)
STASH_RESULT=$(git stash 2>&1 || true)
STASHED=false
if echo "$STASH_RESULT" | grep -q "Saved working directory"; then
    STASHED=true
    log_info "Cambios locales guardados en stash (se restaurarán al final)"
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
git fetch origin
git pull origin "$BRANCH"
COMMIT=$(git log --oneline -1 2>/dev/null || echo "desconocido")
log_ok "Código actualizado → $COMMIT"

# Restaurar cambios locales si había stash
if [ "$STASHED" = true ]; then
    git stash pop 2>/dev/null || log_warn "No se pudo restaurar stash (puede haber conflictos con el nuevo código)"
fi

# ─── PASO 2: Reconstruir imágenes con el nuevo código ────────────────────────
echo ""
echo -e "${YELLOW}▶  Paso 2/7 — Reconstruyendo imágenes Docker...${NC}"
log_info "Reconstruyendo: backend, daphne, celery_worker, celery_beat, dialer_engine, websocket_server, frontend, nginx"

$COMPOSE_CMD -f docker-compose.prod.yml build \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    backend daphne celery_worker celery_beat dialer_engine websocket_server frontend nginx 2>&1

log_ok "Imágenes reconstruidas"

# ─── PASO 3: Reiniciar servicios con nuevas imágenes ─────────────────────────
echo ""
echo -e "${YELLOW}▶  Paso 3/7 — Reiniciando servicios...${NC}"
log_info "up -d aplica solo los contenedores cuya imagen cambió"

$COMPOSE_CMD -f docker-compose.prod.yml up -d --remove-orphans 2>&1

# Esperar que el backend esté healthy (hasta 3 minutos)
log_info "Esperando que el backend esté listo..."
elapsed=0
timeout=180
while [ $elapsed -lt $timeout ]; do
    health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' \
             vozipomni_backend 2>/dev/null || echo "not-found")
    case "$health" in
        healthy|no-healthcheck)
            echo ""
            log_ok "Backend listo (${elapsed}s)"
            break
            ;;
        *)
            printf "  [%3ds/%ds] backend: %s\r" "$elapsed" "$timeout" "$health"
            ;;
    esac
    sleep 5
    elapsed=$((elapsed + 5))
done

if [ $elapsed -ge $timeout ]; then
    echo ""
    log_warn "Backend tardó más de ${timeout}s. Revisa los logs:"
    log_warn "  $COMPOSE_CMD -f docker-compose.prod.yml logs --tail=40 backend"
fi

log_ok "Servicios reiniciados"

# ─── PASO 4: Aplicar migraciones de base de datos ────────────────────────────
echo ""
echo -e "${YELLOW}▶  Paso 4/7 — Aplicando migraciones de base de datos...${NC}"

# Esperar que PostgreSQL esté listo
for i in $(seq 1 30); do
    if $COMPOSE_CMD -f docker-compose.prod.yml exec -T postgres \
        pg_isready -U vozipomni_user -d vozipomni > /dev/null 2>&1; then
        break
    fi
    sleep 2
done

$COMPOSE_CMD -f docker-compose.prod.yml exec -T backend \
    python manage.py migrate --noinput 2>&1 | grep -v '^$' || true

log_ok "Migraciones aplicadas"

# ─── PASO 5: Actualizar archivos estáticos ───────────────────────────────────
echo ""
echo -e "${YELLOW}▶  Paso 5/7 — Recolectando archivos estáticos...${NC}"

$COMPOSE_CMD -f docker-compose.prod.yml exec -T backend \
    python manage.py collectstatic --noinput --clear 2>&1 | tail -2 || true

log_ok "Archivos estáticos actualizados"

# ─── PASO 6: Corregir dtmf_mode y recargar PJSIP ────────────────────────────
echo ""
echo -e "${YELLOW}▶  Paso 6/7 — Verificando y recargando configuración PJSIP...${NC}"

# Corregir rfc2833 → rfc4733 (rfc2833 es nombre de chan_sip; PJSIP usa rfc4733)
$COMPOSE_CMD -f docker-compose.prod.yml exec -T backend \
    python manage.py shell <<'PYEOF' 2>/dev/null || true
from apps.telephony.models import SIPTrunk
updated = SIPTrunk.objects.filter(dtmf_mode='rfc2833').update(dtmf_mode='rfc4733')
if updated:
    print(f'[dtmf_mode] rfc2833 → rfc4733 corregido en {updated} troncal(es)')
else:
    print('[dtmf_mode] OK — todas las troncales usan rfc4733')
PYEOF

# Recargar configuración PJSIP (no fatal: AMI puede estar arrancando todavía)
PJSIP_OUT=$($COMPOSE_CMD -f docker-compose.prod.yml exec -T backend \
    python manage.py shell <<'PYEOF' 2>/dev/null || echo "ERROR: shell falló"
from apps.telephony.pjsip_config_generator import PJSIPConfigGenerator
ok, msg = PJSIPConfigGenerator().save_and_reload()
print(f'PJSIP: {"OK" if ok else "WARN"} — {msg}')
PYEOF
)

if echo "$PJSIP_OUT" | grep -q 'PJSIP: OK'; then
    log_ok "$(echo "$PJSIP_OUT" | tail -n 1)"
else
    log_warn "$(echo "$PJSIP_OUT" | tail -n 1)"
    log_warn "Si las troncales no aparecen registradas, recarga manualmente:"
    log_warn "  Troncales → botón 'Recargar PJSIP' en la interfaz web"
    log_warn "  o: $COMPOSE_CMD -f docker-compose.prod.yml exec backend"
    log_warn "     python manage.py shell -c"
    log_warn "     \"from apps.telephony.pjsip_config_generator import PJSIPConfigGenerator; PJSIPConfigGenerator().save_and_reload()\""
fi

# ─── PASO 7: Recargar dialplan de Asterisk ───────────────────────────────────
echo ""
echo -e "${YELLOW}▶  Paso 7/7 — Recargando dialplan de Asterisk...${NC}"

DIALPLAN_OK=false
for attempt in 1 2 3; do
    if $COMPOSE_CMD -f docker-compose.prod.yml exec -T asterisk \
        asterisk -rx 'dialplan reload' > /dev/null 2>&1; then
        DIALPLAN_OK=true
        break
    fi
    sleep 3
done

if [ "$DIALPLAN_OK" = true ]; then
    log_ok "Dialplan recargado"
else
    log_warn "No se pudo recargar el dialplan ahora (Asterisk puede estar iniciando)"
    log_warn "Se recargará automáticamente al reiniciar Asterisk"
fi

# ─── Limpieza de imágenes huérfanas ──────────────────────────────────────────
echo ""
log_info "Limpiando imágenes Docker sin usar..."
docker image prune -f > /dev/null 2>&1 || true

# ─── Resultado final ─────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ✅  Actualización completada                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Estado de los servicios:${NC}"
$COMPOSE_CMD -f docker-compose.prod.yml ps --format 'table {{.Name}}\t{{.Status}}' 2>/dev/null || \
$COMPOSE_CMD -f docker-compose.prod.yml ps
echo ""
echo -e "${BLUE}Commit desplegado:${NC} ${GREEN}$COMMIT${NC}"
echo ""
echo -e "${BLUE}Comandos útiles:${NC}"
echo -e "  Logs backend:  ${GREEN}$COMPOSE_CMD -f docker-compose.prod.yml logs -f backend${NC}"
echo -e "  Logs todos:    ${GREEN}$COMPOSE_CMD -f docker-compose.prod.yml logs -f${NC}"
echo -e "  Estado:        ${GREEN}$COMPOSE_CMD -f docker-compose.prod.yml ps${NC}"
echo ""
