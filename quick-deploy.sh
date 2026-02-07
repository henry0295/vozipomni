#!/bin/bash

################################################################################
# Script de Deploy Rápido - VoziPOmni
# Usa imagen pre-compilada de Asterisk para deploy instantáneo
################################################################################

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     VoziPOmni - Deploy Rápido con Asterisk Pre-built     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

# Hacer backup del Dockerfile actual
echo "📦 Creando backup del Dockerfile actual..."
if [ -f "docker/asterisk/Dockerfile" ]; then
    cp docker/asterisk/Dockerfile docker/asterisk/Dockerfile.backup
fi

# Usar el Dockerfile pre-compilado
echo "🚀 Cambiando a Dockerfile pre-compilado (rápido)..."
if [ -f "docker/asterisk/Dockerfile.prebuilt" ]; then
    cp docker/asterisk/Dockerfile.prebuilt docker/asterisk/Dockerfile
    echo "✓ Dockerfile actualizado"
else
    echo "❌ No se encontró Dockerfile.prebuilt"
    echo "Descargando..."
    
    # Si no existe, crear uno básico
    cat > docker/asterisk/Dockerfile <<'EOF'
FROM andrius/asterisk:21-alpine

USER root

RUN apk add --no-cache tzdata curl wget && \
    mkdir -p /var/log/asterisk /var/spool/asterisk/monitor /etc/asterisk && \
    ln -sf /usr/share/zoneinfo/America/Bogota /etc/localtime

COPY configs/*.conf /etc/asterisk/

RUN adduser -D -H asterisk 2>/dev/null || true && \
    chown -R asterisk:asterisk /var/lib/asterisk /var/spool/asterisk /var/log/asterisk /etc/asterisk 2>/dev/null || true

EXPOSE 5060/udp 5060/tcp 5061/tcp 8088 8089 10000-20000/udp

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD asterisk -rx "core show version" || exit 1

VOLUME ["/var/lib/asterisk", "/var/spool/asterisk", "/var/log/asterisk"]

CMD ["asterisk", "-f", "-vvv", "-g"]
EOF
    echo "✓ Dockerfile creado"
fi

# Detener servicios actuales
echo ""
echo "🛑 Deteniendo servicios actuales..."
docker-compose down 2>/dev/null || true

# Limpiar imágenes antiguas de Asterisk
echo ""
echo "🧹 Limpiando imágenes antiguas..."
docker rmi vozipomni-asterisk 2>/dev/null || true

# Construir solo Asterisk
echo ""
echo "🔨 Construyendo Asterisk (imagen pre-compilada - rápido)..."
docker-compose build asterisk

# Construir resto de servicios
echo ""
echo "🔨 Construyendo servicios restantes..."
docker-compose build

# Levantar servicios
echo ""
echo "🚀 Levantando servicios..."
docker-compose up -d

# Esperar a que Asterisk esté listo
echo ""
echo "⏳ Esperando a que Asterisk inicie..."
sleep 10

# Verificar estado
echo ""
echo "📊 Estado de servicios:"
docker-compose ps

# Verificar Asterisk
echo ""
echo "🔍 Verificando Asterisk..."
docker-compose exec -T asterisk asterisk -rx "core show version" || echo "⚠️  Asterisk aún está iniciando..."

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✓ Deploy completado exitosamente             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Comandos útiles:"
echo "  Ver logs Asterisk:     docker-compose logs -f asterisk"
echo "  CLI de Asterisk:       docker-compose exec asterisk asterisk -rvvv"
echo "  Ver todos los logs:    docker-compose logs -f"
echo "  Reiniciar servicios:   docker-compose restart"
echo ""
echo "Accede al sistema en: http://$(hostname -I | awk '{print $1}')"
echo ""

# Mostrar credenciales si existen
if [ -f "credentials.txt" ]; then
    echo "📋 Credenciales en: credentials.txt"
fi
