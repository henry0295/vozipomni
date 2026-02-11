#!/bin/bash

echo "=== Limpiando contenedores frontend ==="
docker-compose stop frontend_dev frontend 2>/dev/null
docker-compose rm -f frontend_dev frontend 2>/dev/null

echo -e "\n=== Construyendo frontend de producción ==="
docker-compose build frontend

echo -e "\n=== Iniciando frontend de producción ==="
docker-compose up -d frontend

echo -e "\n=== Esperando 5 segundos ==="
sleep 5

echo -e "\n=== Logs del frontend ==="
docker-compose logs --tail=50 frontend

echo -e "\n=== Estado de contenedores ==="
docker-compose ps

echo -e "\n✓ Frontend desplegado en http://localhost:3000"
