#!/bin/bash

set -e

echo "=== Deploy Frontend Producción ==="
echo ""

# 1. Git pull
echo "1. Actualizando código desde GitHub..."
git pull origin main

# 2. Detener servicios frontend anteriores
echo ""
echo "2. Deteniendo servicios frontend anteriores..."
docker-compose stop frontend_dev frontend 2>/dev/null || true
docker-compose rm -f frontend_dev frontend 2>/dev/null || true

# 3. Construir frontend de producción
echo ""
echo "3. Construyendo frontend de producción..."
docker-compose build frontend

# 4. Levantar frontend
echo ""
echo "4. Levantando frontend de producción..."
docker-compose up -d frontend

# 5. Esperar a que inicie
echo ""
echo "5. Esperando 10 segundos para que inicie..."
sleep 10

# 6. Reiniciar nginx
echo ""
echo "6. Reiniciando nginx..."
docker-compose restart nginx

# 7. Verificar estado
echo ""
echo "7. Estado de los servicios:"
docker-compose ps frontend nginx

echo ""
echo "8. Logs del frontend (últimas 20 líneas):"
docker-compose logs --tail=20 frontend

echo ""
echo "============================================"
echo "✓ Deploy completado"
echo "============================================"
echo ""
echo "Accede a la aplicación en:"
echo "  http://$(hostname -I | awk '{print $1}')"
echo ""
echo "Para ver los logs en tiempo real:"
echo "  docker-compose logs -f frontend"
echo ""
