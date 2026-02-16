#!/bin/bash

################################################################################
# Script de Corrección Rápida - Servidor de Producción
# Ejecutar después de hacer git pull para aplicar correcciones de Nginx y backend
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
echo -e "${CYAN}  VoziPOmni - Corrección Rápida de Nginx${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: Directorio $INSTALL_DIR no existe${NC}"
    exit 1
fi

cd $INSTALL_DIR

echo -e "${BLUE}Paso 1/5: Verificando estado de contenedores...${NC}"
docker compose ps
echo ""

echo -e "${BLUE}Paso 2/5: Actualizando código desde repositorio...${NC}"
git pull origin main
echo -e "${GREEN}✓ Código actualizado${NC}"
echo ""

echo -e "${BLUE}Paso 3/5: Reconstruyendo nginx con nueva configuración...${NC}"
docker compose build nginx
echo -e "${GREEN}✓ Nginx reconstruido${NC}"
echo ""

echo -e "${BLUE}Paso 4/5: Reiniciando servicios...${NC}"
docker compose down
docker compose up -d
echo -e "${GREEN}✓ Servicios reiniciados${NC}"
echo ""

echo -e "${YELLOW}Esperando 15 segundos para que los servicios estén listos...${NC}"
for i in {15..1}; do
    echo -ne "\rTiempo restante: $i segundos "
    sleep 1
done
echo ""
echo ""

echo -e "${BLUE}Paso 5/5: Verificando estado de servicios...${NC}"
docker compose ps
echo ""

# Verificar que nginx está sirviendo
echo -e "${BLUE}Verificando Nginx...${NC}"
HEALTH_CHECK=$(curl -s http://localhost/health || echo "ERROR")
if [ "$HEALTH_CHECK" = "healthy" ]; then
    echo -e "${GREEN}✓ Nginx está funcionando correctamente${NC}"
else
    echo -e "${RED}✗ Nginx no está respondiendo correctamente${NC}"
fi
echo ""

# Verificar backend
echo -e "${BLUE}Verificando Backend...${NC}"
BACKEND_LOGS=$(docker compose logs backend | grep -i "error" | tail -5 || echo "")
if [ -z "$BACKEND_LOGS" ]; then
    echo -e "${GREEN}✓ Backend sin errores recientes${NC}"
else
    echo -e "${YELLOW}⚠ Algunos errores en backend:${NC}"
    echo "$BACKEND_LOGS"
fi
echo ""

# Verificar frontend
echo -e "${BLUE}Verificando Frontend...${NC}"
FRONTEND_STATUS=$(docker compose logs frontend | grep "Listening" | tail -1 || echo "")
if [ -n "$FRONTEND_STATUS" ]; then
    echo -e "${GREEN}✓ Frontend activo: $FRONTEND_STATUS${NC}"
else
    echo -e "${YELLOW}⚠ Frontend puede estar iniciando${NC}"
fi
echo ""

# IP del servidor
SERVER_IP=$(hostname -I | awk '{print $1}')

echo -e "${CYAN}================================================${NC}"
echo -e "${GREEN}Accede a tu aplicación en:${NC}"
echo -e "${CYAN}  → http://$SERVER_IP${NC}"
echo -e "${CYAN}  → http://$SERVER_IP/admin (Django Admin)${NC}"
echo -e "${CYAN}  → http://$SERVER_IP/health (Health Check)${NC}"
echo ""

echo -e "${YELLOW}Comandos útiles:${NC}"
echo -e "  Ver logs backend:   ${CYAN}docker compose logs -f backend${NC}"
echo -e "  Ver logs frontend:  ${CYAN}docker compose logs -f frontend${NC}"
echo -e "  Ver logs nginx:     ${CYAN}docker compose logs -f nginx${NC}"
echo -e "  Reiniciar todo:     ${CYAN}docker compose restart${NC}"
echo ""

echo -e "${GREEN}¡Corrección aplicada exitosamente!${NC}"
echo ""
