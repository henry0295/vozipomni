#!/bin/bash
#============================================================================
# Script para corregir el problema de audio en llamadas (RTP)
#============================================================================
# Problema: Las llamadas conectan pero no hay audio y se cortan a los 10 seg
# Causa: RTPEngine no se estaba invocando para todas las llamadas
# Solución: Modificar Kamailio para usar RTPEngine siempre en INVITE
#============================================================================

set -e

INSTALL_DIR="/opt/vozipomni"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Corrección de Audio RTP en Llamadas (RTPEngine)      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "$INSTALL_DIR/docker-compose.prod.yml" ]; then
    echo "❌ Error: No se encuentra docker-compose.prod.yml en $INSTALL_DIR"
    exit 1
fi

cd "$INSTALL_DIR"

echo "[INFO] Repositorio actual:"
git remote -v | head -1
echo ""

echo "[1/6] Obteniendo última versión del código..."
git pull origin main || {
    echo "❌ Error al hacer git pull. Verifica la conectividad."
    exit 1
}

echo ""
echo "[2/6] Verificando cambios en configuración de Kamailio..."
if grep -q "rtpengine_manage.*INVITE" docker/kamailio/kamailio.cfg; then
    echo "✓ Kamailio actualizado para invocar RTPEngine en todos los INVITE"
else
    echo "❌ Error: kamailio.cfg no está actualizado."
    echo "   Verifica que ejecutaste 'git pull' correctamente."
    exit 1
fi

echo ""
echo "[3/6] Deteniendo contenedores afectados..."
docker compose -f docker-compose.prod.yml stop kamailio rtpengine || true
docker compose -f docker-compose.prod.yml rm -f kamailio rtpengine || true

echo ""
echo "[4/6] Reconstruyendo imágenes..."
docker compose -f docker-compose.prod.yml build kamailio rtpengine

echo ""
echo "[5/6] Iniciando contenedores actualizados..."
docker compose -f docker-compose.prod.yml up -d kamailio rtpengine

echo ""
echo "[6/6] Esperando 20 segundos para verificar estado..."
sleep 20

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Estado de los servicios:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose -f docker-compose.prod.yml ps kamailio rtpengine asterisk

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Últimos logs de Kamailio (verificar RTPEngine):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose -f docker-compose.prod.yml logs --tail=30 kamailio | grep -i "rtpengine\|listening" || true

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✓ Corrección Aplicada Exitosamente           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 PRUEBA DE AUDIO:"
echo "   1. Realiza una llamada de prueba desde un softphone"
echo "   2. Deberías escuchar audio en ambas direcciones"
echo "   3. La llamada NO debe cortarse a los 10 segundos"
echo ""
echo "📊 VERIFICACIÓN DE RTP:"
echo "   Ver logs en tiempo real:"
echo "   → docker compose -f docker-compose.prod.yml logs -f kamailio | grep -i rtpengine"
echo ""
echo "   Ver estadísticas RTPEngine:"
echo "   → docker compose -f docker-compose.prod.yml exec rtpengine rtpengine-ctl list"
echo ""
echo "🔍 DEBUGGING (si persiste el problema):"
echo "   Ver logs completos de Kamailio:"
echo "   → docker compose -f docker-compose.prod.yml logs -f kamailio"
echo ""
echo "   Ver logs de RTPEngine:"
echo "   → docker compose -f docker-compose.prod.yml logs -f rtpengine"
echo ""
echo "   Ver SDP en Asterisk:"
echo "   → docker compose -f docker-compose.prod.yml exec asterisk asterisk -rx 'pjsip set logger on'"
echo ""
