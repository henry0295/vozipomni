#!/bin/bash

################################################################################
# VoziPOmni Quick Start Script
# Para desarrollo local con Docker Desktop
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════${NC}"
echo -e "${BLUE}   VoziPOmni Contact Center - Quick Start${NC}"
echo -e "${BLUE}════════════════════════════════════════════${NC}"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker no está instalado"
    echo "Instala Docker Desktop desde: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# ── Preparar sistema (silenciar mensajes del kernel) ──
echo "Preparando sistema..."
if [ -w /proc/sys/kernel/printk ] 2>/dev/null; then
    echo "1 4 1 7" > /proc/sys/kernel/printk 2>/dev/null || true
elif command -v dmesg &>/dev/null; then
    dmesg -n 1 2>/dev/null || true
fi
# Persistir
if [ -w /etc/sysctl.d/ ] 2>/dev/null; then
    echo "kernel.printk = 1 4 1 7" > /etc/sysctl.d/10-vozipomni-silence.conf 2>/dev/null || true
    sysctl -p /etc/sysctl.d/10-vozipomni-silence.conf 2>/dev/null || true
fi
modprobe br_netfilter 2>/dev/null || true
echo -e "${GREEN}✓ Sistema preparado${NC}"

# Create .env if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo "Creando archivo .env..."
    cat > backend/.env <<EOF
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost

DB_NAME=vozipomni
DB_USER=vozipomni
DB_PASSWORD=vozipomni2026
DB_HOST=postgres
DB_PORT=5432

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis2026

ASTERISK_HOST=asterisk
ASTERISK_AMI_USER=admin
ASTERISK_AMI_PASSWORD=VoziPOmni2026!
ASTERISK_PUBLIC_IP=127.0.0.1

CELERY_BROKER_URL=redis://:redis2026@redis:6379/0
CELERY_RESULT_BACKEND=redis://:redis2026@redis:6379/0

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EOF
fi

echo "Iniciando servicios Docker..."
docker compose up -d

echo ""
echo "Esperando a que los servicios estén listos..."
echo "Verificando PostgreSQL..."
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U vozipomni -d vozipomni > /dev/null 2>&1; then
        echo "✓ PostgreSQL listo"
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

echo ""
echo "Ejecutando migraciones..."
docker compose run --rm backend python manage.py migrate

echo ""
echo "Creando superusuario..."
docker compose run --rm backend python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@vozipomni.local', 'admin123')
    print('Superuser created: admin / admin123')
else:
    print('Superuser already exists')
EOF

echo ""
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ¡Listo! VoziPOmni está corriendo${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo -e "Accede a: ${GREEN}http://localhost${NC}"
echo -e "Usuario: ${GREEN}admin${NC}"
echo -e "Contraseña: ${GREEN}admin123${NC}"
echo ""
echo "Comandos útiles:"
echo "  docker compose logs -f        # Ver logs"
echo "  docker compose restart        # Reiniciar"
echo "  docker compose down           # Detener"
echo ""
