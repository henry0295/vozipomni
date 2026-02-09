#!/bin/bash
# Script de diagnóstico: Verificar estado de registros PJSIP
# Uso: ./check-trunk-registration.sh

echo "=========================================="
echo "  DIAGNÓSTICO DE REGISTROS PJSIP"
echo "=========================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

# Verificar que los contenedores estén corriendo
if ! docker compose ps | grep -q "asterisk"; then
    echo "❌ El contenedor de Asterisk no está corriendo"
    echo "   Ejecuta: docker compose up -d asterisk"
    exit 1
fi

echo "✓ Contenedores de VoziPOmni están corriendo"
echo ""

# 1. Verificar troncales en la base de datos
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TRONCALES EN BASE DE DATOS (Django)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose exec backend python manage.py shell << 'PYEOF'
from apps.telephony.models import SIPTrunk
trunks = SIPTrunk.objects.all()
if not trunks:
    print("⚠️  No hay troncales configuradas en la base de datos")
else:
    print(f"Total de troncales: {trunks.count()}\n")
    for trunk in trunks:
        print(f"  • {trunk.name}")
        print(f"    Host: {trunk.host}:{trunk.port}")
        print(f"    Usuario: {trunk.username}")
        print(f"    Protocolo: {trunk.protocol}")
        print(f"    Estado: {'Activo' if trunk.is_active else 'Inactivo'}")
        print("")
PYEOF

echo ""

# 2. Verificar registros PJSIP en Asterisk
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 REGISTROS PJSIP EN ASTERISK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
REGISTRATIONS=$(docker compose exec -T asterisk asterisk -rx "pjsip show registrations" 2>/dev/null)

if echo "$REGISTRATIONS" | grep -q "No objects found"; then
    echo "⚠️  No hay objetos de tipo [registration] configurados en Asterisk"
    echo ""
    echo "Esto significa que las troncales no tienen configurado el componente"
    echo "de REGISTRO en /etc/asterisk/pjsip.conf"
    echo ""
    echo "Para configurar un registro, agrega en pjsip.conf:"
    echo ""
    echo "  [nombre_troncal-reg]"
    echo "  type=registration"
    echo "  transport=transport-udp"
    echo "  outbound_auth=nombre_troncal-auth"
    echo "  server_uri=sip:proveedor.com"
    echo "  client_uri=sip:usuario@proveedor.com"
    echo "  retry_interval=60"
    echo ""
else
    echo "$REGISTRATIONS"
    echo ""
    
    # Contar registros activos
    REGISTERED_COUNT=$(echo "$REGISTRATIONS" | grep -c "Registered" || true)
    TOTAL_COUNT=$(echo "$REGISTRATIONS" | grep -E "^\s+\S+/sip:" | wc -l)
    
    if [ "$REGISTERED_COUNT" -gt 0 ]; then
        echo "✅ Registros activos: $REGISTERED_COUNT de $TOTAL_COUNT"
    else
        echo "⚠️  Ningún registro activo (0 de $TOTAL_COUNT)"
    fi
fi

echo ""

# 3. Verificar endpoints PJSIP
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📞 ENDPOINTS PJSIP EN ASTERISK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ENDPOINTS=$(docker compose exec -T asterisk asterisk -rx "pjsip show endpoints" 2>/dev/null)

if echo "$ENDPOINTS" | grep -q "No objects found"; then
    echo "❌ No hay endpoints configurados en Asterisk"
else
    echo "$ENDPOINTS" | head -20
    ENDPOINT_COUNT=$(echo "$ENDPOINTS" | grep -cE "^\s+\S+/\S+" || true)
    echo ""
    echo "Total de endpoints: $ENDPOINT_COUNT"
fi

echo ""

# 4. Verificar estado detallado de cada troncal
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 ESTADO DETALLADO POR TRONCAL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Obtener nombres de troncales desde Django
TRUNK_NAMES=$(docker compose exec -T backend python manage.py shell << 'PYEOF'
from apps.telephony.models import SIPTrunk
for trunk in SIPTrunk.objects.all():
    print(trunk.name)
PYEOF
)

if [ -z "$TRUNK_NAMES" ]; then
    echo "⚠️  No hay troncales en la base de datos"
else
    for TRUNK_NAME in $TRUNK_NAMES; do
        echo ""
        echo "  📌 Troncal: $TRUNK_NAME"
        echo "  ─────────────────────────────────────"
        
        # Verificar endpoint
        ENDPOINT_INFO=$(docker compose exec -T asterisk asterisk -rx "pjsip show endpoint $TRUNK_NAME" 2>/dev/null)
        if echo "$ENDPOINT_INFO" | grep -q "Unable to find object"; then
            echo "    ❌ Endpoint [$TRUNK_NAME] NO existe en Asterisk"
        else
            echo "    ✅ Endpoint [$TRUNK_NAME] existe"
        fi
        
        # Verificar registro
        REG_INFO=$(docker compose exec -T asterisk asterisk -rx "pjsip show registration ${TRUNK_NAME}-reg" 2>/dev/null)
        if echo "$REG_INFO" | grep -q "Unable to find object"; then
            echo "    ℹ️  Registro [${TRUNK_NAME}-reg] NO configurado"
            echo "       → Estado: Sin Configurar (Peer sin registro)"
        else
            # Extraer estado del registro
            REG_STATE=$(echo "$REG_INFO" | grep "Status" | awk '{print $NF}')
            if [ -n "$REG_STATE" ]; then
                echo "    ✅ Registro [${TRUNK_NAME}-reg] existe"
                echo "       → Estado: $REG_STATE"
            else
                echo "    ⚠️  Registro [${TRUNK_NAME}-reg] existe pero estado desconocido"
            fi
        fi
        
        # Verificar estado desde Django/AMI
        REG_STATUS=$(docker compose exec -T backend python manage.py shell << PYEOF
from apps.telephony.models import SIPTrunk
from apps.telephony.asterisk_ami import AsteriskAMI
trunk = SIPTrunk.objects.filter(name='$TRUNK_NAME').first()
if trunk:
    ami = AsteriskAMI()
    if ami.connect():
        status = ami.get_trunk_registration_status('$TRUNK_NAME')
        ami.disconnect()
        print(status)
PYEOF
)
        
        if [ -n "$REG_STATUS" ]; then
            echo "    🔧 Estado AMI: $REG_STATUS"
        fi
    done
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 RESUMEN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Contar troncales en Django
DJANGO_TRUNKS=$(docker compose exec -T backend python manage.py shell << 'PYEOF'
from apps.telephony.models import SIPTrunk
print(SIPTrunk.objects.count())
PYEOF
)

# Contar registros en Asterisk
ASTERISK_REGS=$(docker compose exec -T asterisk asterisk -rx "pjsip show registrations" 2>/dev/null | grep -cE "^\s+\S+/sip:" || echo "0")

echo ""
echo "  • Troncales en Base de Datos: $DJANGO_TRUNKS"
echo "  • Registros en Asterisk: $ASTERISK_REGS"
echo ""

if [ "$DJANGO_TRUNKS" -gt 0 ] && [ "$ASTERISK_REGS" -eq 0 ]; then
    echo "⚠️  ATENCIÓN:"
    echo "   Tienes troncales en la base de datos pero ningún registro"
    echo "   configurado en Asterisk PJSIP."
    echo ""
    echo "   Si tus troncales requieren registro, configúralos en:"
    echo "   docker/asterisk/configs/pjsip.conf"
    echo ""
    echo "   Luego ejecuta:"
    echo "   docker compose exec asterisk asterisk -rx 'pjsip reload'"
elif [ "$ASTERISK_REGS" -gt 0 ]; then
    echo "✅ Hay registros configurados en Asterisk"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Para más información, consulta:"
echo "  • EXPLICACION_SIN_CONFIGURAR.md"
echo "  • GUIA_PJSIP.md"
echo "  • CONFIGURAR_TRONCALES_REGISTRO.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
