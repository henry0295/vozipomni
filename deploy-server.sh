# Script de Deployment para VoziPOmni
# Ejecutar en el SERVIDOR (Linux)

#!/bin/bash

echo "========================================================"
echo "  ACTUALIZANDO VoziPOmni - Servidor Producción"
echo "========================================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: No estás en el directorio del proyecto${NC}"
    echo "Ejecuta: cd /opt/vozipomni"
    exit 1
fi

# Silenciar mensajes del kernel (evita logs de veth/bridge en consola)
if [ -w /proc/sys/kernel/printk ] 2>/dev/null; then
    echo "1 4 1 7" > /proc/sys/kernel/printk 2>/dev/null || true
elif command -v dmesg &>/dev/null; then
    dmesg -n 1 2>/dev/null || true
fi

echo -e "${YELLOW}📋 Paso 1: Guardando cambios locales (stash)...${NC}"
git stash

echo ""
echo -e "${YELLOW}📥 Paso 2: Descargando últimos cambios...${NC}"
git pull origin main

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al hacer git pull${NC}"
    echo "Resolviendo conflictos..."
    git stash pop
    exit 1
fi

echo ""
echo -e "${YELLOW}📦 Paso 3: Reconstruyendo contenedores...${NC}"
docker compose build backend

echo ""
echo -e "${YELLOW}🔄 Paso 4: Reiniciando servicios...${NC}"

# Reiniciar backend para aplicar cambios Python
docker compose restart backend

# Reiniciar celery workers
docker compose restart celery_worker celery_beat

echo ""
echo -e "${YELLOW}🧹 Paso 5: Limpiando...${NC}"
docker system prune -f

echo ""
echo -e "${GREEN}✅ DEPLOYMENT COMPLETADO${NC}"
echo ""
echo "Verificaciones:"
echo "  1. Backend: docker compose logs backend -f"
echo "  2. Estado: docker compose ps"
echo "  3. Verificar en navegador: http://TU_IP:8000/api/telephony/trunks/"
echo ""
