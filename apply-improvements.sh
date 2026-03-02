#!/bin/bash

# Script para aplicar las mejoras a VoziPOmni
# Ejecuta migraciones y regenera configuración de Asterisk

set -e  # Salir si hay error

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  VoziPOmni - Script de Mejoras y Configuración Automática       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Este script debe ejecutarse desde el directorio raíz del proyecto"
    exit 1
fi

echo "📦 Paso 1: Aplicando migraciones..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec vozipomni_backend python manage.py migrate telephony
echo ""

echo "🔧 Paso 2: Generando configuración de Asterisk..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec vozipomni_backend python manage.py generate_asterisk_config
echo ""

echo "📋 Paso 3: Verificando sistema..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec vozipomni_backend python manage.py shell <<EOF
from apps.telephony.models import Extension

total = Extension.objects.count()
print(f"\n📊 Estado del sistema:")
print("=" * 60)
print(f"  Total de extensiones: {total}")

if total > 0:
    print("\n  Extensiones registradas:")
    for ext in Extension.objects.all().order_by('extension')[:10]:
        status = "🟢" if ext.is_active else "🔴"
        print(f"    {status} {ext.extension:6s} | {ext.name:20s} | {ext.extension_type:8s}")
    
    if total > 10:
        print(f"\n  ... y {total - 10} más")
else:
    print("\n  ℹ️  No hay extensiones creadas")
    print('  👉 Crea extensiones desde la web: http://IP-SERVIDOR/extensions')

print("")
EOF
echo ""

echo "📞 Paso 4: Verificando estado PJSIP en Asterisk..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Endpoints PJSIP:"
docker exec vozipomni_asterisk asterisk -rx "pjsip show endpoints" | grep -E "Endpoint:|200|201|202|203|204|205|206|207|208|209" || echo "⚠️  No se encontraron endpoints"
echo ""

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  ✅ Configuración completada exitosamente                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 Próximos pasos:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1. Accede al panel web: http://IP-SERVIDOR/extensions"
echo "  2. Crea tus primeras extensiones desde la interfaz"
echo "  3. Las extensiones se sincronizarán automáticamente con Asterisk"
echo "  4. Configura tus softphones con las credenciales creadas"
echo ""
echo "📱 Para ver credenciales de extensiones existentes:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  docker exec vozipomni_backend python manage.py shell <<< \""
echo "  from apps.telephony.models import Extension"
echo "  for ext in Extension.objects.all().order_by('extension'):"
echo "      print(f'{ext.extension}: {ext.secret}')"
echo "  \""
echo ""
