#!/bin/bash

################################################################################
# Script de Actualización Post-Fix de Migraciones
# Ejecutar en servidor de producción después de hacer push desde desarrollo
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

INSTALL_DIR="/opt/vozipomni"

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}  VoziPOmni - Actualización de Migraciones${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: Directorio $INSTALL_DIR no existe${NC}"
    echo -e "${YELLOW}¿VoziPOmni está instalado?${NC}"
    exit 1
fi

cd $INSTALL_DIR

echo -e "${YELLOW}Directorio actual:${NC} $INSTALL_DIR"
echo ""

# Verificar que hay conexión con el repositorio
echo -e "${BLUE}Verificando conexión con repositorio...${NC}"
if ! git remote -v | grep -q "vozipomni"; then
    echo -e "${RED}Error: No se detectó el repositorio remoto${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Repositorio conectado${NC}"
echo ""

# Mostrar rama actual
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${YELLOW}Rama actual:${NC} $CURRENT_BRANCH"
echo ""

# Preguntar confirmación
read -p "¿Desea actualizar desde origin/main? (s/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${YELLOW}Actualización cancelada${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Paso 1/7: Guardando cambios locales (si existen)...${NC}"
git stash || true
echo -e "${GREEN}✓ Cambios guardados${NC}"
echo ""

echo -e "${BLUE}Paso 2/7: Actualizando código desde repositorio...${NC}"
git fetch origin
git pull origin main
echo -e "${GREEN}✓ Código actualizado${NC}"
echo ""

echo -e "${BLUE}Paso 3/7: Verificando nuevas migraciones...${NC}"
NEW_MIGRATIONS=$(find backend/apps/*/migrations -name "0001_initial.py" -o -name "0002_*.py" | wc -l)
echo -e "${CYAN}Migraciones encontradas: $NEW_MIGRATIONS${NC}"
echo ""

echo -e "${BLUE}Paso 4/7: Reconstruyendo frontend (sin caché)...${NC}"
docker compose build --no-cache frontend
echo -e "${GREEN}✓ Frontend reconstruido${NC}"
echo ""

echo -e "${BLUE}Paso 5/7: Deteniendo servicios...${NC}"
docker compose down
echo -e "${GREEN}✓ Servicios detenidos${NC}"
echo ""

echo -e "${BLUE}Paso 6/7: Iniciando servicios...${NC}"
docker compose up -d
echo -e "${GREEN}✓ Servicios iniciados${NC}"
echo ""

echo -e "${YELLOW}Esperando 20 segundos para que los servicios estén listos...${NC}"
for i in {20..1}; do
    echo -ne "\rTiempo restante: $i segundos "
    sleep 1
done
echo ""
echo ""

echo -e "${BLUE}Paso 7/7: Aplicando migraciones...${NC}"
docker compose exec -T backend python manage.py migrate --noinput

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Migraciones aplicadas correctamente${NC}"
else
    echo -e "${RED}✗ Error al aplicar migraciones${NC}"
    echo ""
    echo -e "${YELLOW}Ver logs para más información:${NC}"
    echo -e "${CYAN}docker compose logs backend${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}  ✅ ACTUALIZACIÓN COMPLETADA${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# Verificar migraciones aplicadas
echo -e "${BLUE}Migraciones aplicadas:${NC}"
docker compose exec -T backend python manage.py showmigrations | grep -E "^\[X\]|^[a-z]" | head -20
echo ""

# Verificar estado de servicios
echo -e "${BLUE}Estado de servicios:${NC}"
docker compose ps
echo ""

# Verificar que el frontend está sirviendo
echo -e "${BLUE}Verificando frontend...${NC}"
FRONTEND_LOGS=$(docker compose logs frontend | grep -i "listening" | tail -1)
if [ -n "$FRONTEND_LOGS" ]; then
    echo -e "${GREEN}✓ Frontend activo: $FRONTEND_LOGS${NC}"
else
    echo -e "${YELLOW}⚠ Frontend puede estar iniciando aún${NC}"
fi
echo ""

# IP del servidor
SERVER_IP=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}Accede a tu aplicación en:${NC}"
echo -e "${CYAN}  → http://$SERVER_IP${NC}"
echo ""

echo -e "${YELLOW}Comandos útiles:${NC}"
echo -e "  Ver logs backend:       ${CYAN}docker compose logs -f backend${NC}"
echo -e "  Ver logs frontend:      ${CYAN}docker compose logs -f frontend${NC}"
echo -e "  Ver todas las migraciones: ${CYAN}docker compose exec backend python manage.py showmigrations${NC}"
echo -e "  Reiniciar servicios:    ${CYAN}docker compose restart${NC}"
echo ""

echo -e "${GREEN}¡Actualización exitosa!${NC}"
echo ""
