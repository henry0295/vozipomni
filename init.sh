#!/bin/bash

# Script de inicialización de VoziPOmni Contact Center

echo "================================================"
echo "  VoziPOmni Contact Center - Inicialización"
echo "================================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Verificar Docker
echo "Verificando prerequisitos..."
if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado"
    exit 1
fi
print_status "Docker instalado"

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose no está instalado"
    exit 1
fi
print_status "Docker Compose instalado"

# Crear directorios necesarios
echo ""
echo "Creando directorios..."
mkdir -p backend/static
mkdir -p backend/media
mkdir -p backend/recordings
print_status "Directorios creados"

# Construir imágenes
echo ""
echo "Construyendo imágenes Docker (esto puede tardar varios minutos)..."
docker-compose build

if [ $? -eq 0 ]; then
    print_status "Imágenes construidas exitosamente"
else
    print_error "Error al construir imágenes"
    exit 1
fi

# Iniciar servicios
echo ""
echo "Iniciando servicios..."
docker-compose up -d postgres redis

# Esperar a que PostgreSQL esté listo
echo "Esperando a que PostgreSQL esté listo..."
sleep 10

# Ejecutar migraciones
echo ""
echo "Ejecutando migraciones de base de datos..."
docker-compose run --rm backend python manage.py migrate

if [ $? -eq 0 ]; then
    print_status "Migraciones ejecutadas"
else
    print_error "Error en migraciones"
    exit 1
fi

# Crear superusuario automáticamente (solo para desarrollo)
echo ""
echo "Creando superusuario por defecto..."
docker-compose run --rm backend python manage.py shell << EOF
from apps.users.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@vozipomni.local', 'admin123')
    print('Superusuario creado: admin / admin123')
else:
    print('Superusuario ya existe')
EOF

# Crear datos de ejemplo
echo ""
echo "Creando datos de ejemplo..."
docker-compose run --rm backend python manage.py shell << EOF
from apps.queues.models import Queue
from apps.campaigns.models import Campaign, CampaignDisposition
from apps.contacts.models import ContactList
from django.utils import timezone
from datetime import timedelta

# Crear colas si no existen
if not Queue.objects.filter(name='Ventas').exists():
    Queue.objects.create(
        name='Ventas',
        extension='9001',
        description='Cola de ventas',
        strategy='ringall',
        timeout=30
    )
    print('Cola de Ventas creada')

if not Queue.objects.filter(name='Soporte').exists():
    Queue.objects.create(
        name='Soporte',
        extension='9002',
        description='Cola de soporte técnico',
        strategy='leastrecent',
        timeout=30
    )
    print('Cola de Soporte creada')

# Crear lista de contactos de ejemplo
if not ContactList.objects.filter(name='Lista Demo').exists():
    contact_list = ContactList.objects.create(
        name='Lista Demo',
        description='Lista de contactos de demostración',
        is_active=True
    )
    print('Lista de contactos creada')

print('Datos de ejemplo creados')
EOF

# Iniciar todos los servicios
echo ""
echo "Iniciando todos los servicios..."
docker-compose up -d

if [ $? -eq 0 ]; then
    print_status "Todos los servicios iniciados"
else
    print_error "Error al iniciar servicios"
    exit 1
fi

# Esperar a que los servicios estén listos
echo ""
echo "Esperando a que todos los servicios estén listos..."
sleep 15

# Mostrar información
echo ""
echo "================================================"
echo "  ¡VoziPOmni instalado exitosamente!"
echo "================================================"
echo ""
print_status "Frontend: http://localhost"
print_status "Frontend Dev: http://localhost:3000"
print_status "API REST: http://localhost/api"
print_status "Admin Django: http://localhost/admin"
print_status "Documentación API: http://localhost/api/docs"
echo ""
echo "Credenciales de administrador:"
echo "  Usuario: admin"
echo "  Contraseña: admin123"
echo ""
print_warning "¡IMPORTANTE! Cambia la contraseña del administrador en producción"
echo ""
echo "Ver logs:"
echo "  docker-compose logs -f"
echo ""
echo "Detener servicios:"
echo "  docker-compose down"
echo ""
echo "================================================"
