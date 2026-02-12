#!/bin/bash
# Script de verificación de configuración para producción
# Ejecutar antes de desplegar: ./verify-production.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

errors_found=0
warnings_found=0

echo -e "${CYAN}===========================================================${NC}"
echo -e "${CYAN}   VozipOmni - Verificación de Configuración de Producción${NC}"
echo -e "${CYAN}===========================================================${NC}"
echo ""

# Función para verificar archivos
check_file() {
    local file=$1
    local description=$2
    local critical=${3:-true}
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}[OK]${NC} $description"
        return 0
    else
        if [ "$critical" = true ]; then
            echo -e "${RED}[ERROR]${NC} $description - Archivo no encontrado: $file"
            ((errors_found++))
        else
            echo -e "${YELLOW}[WARN]${NC} $description - Archivo no encontrado: $file"
            ((warnings_found++))
        fi
        return 1
    fi
}

# Función para verificar contenido
check_content() {
    local file=$1
    local pattern=$2
    local description=$3
    local should_exist=${4:-true}
    
    if [ -f "$file" ]; then
        if grep -q "$pattern" "$file"; then
            found=true
        else
            found=false
        fi
        
        if [ "$should_exist" = "$found" ]; then
            echo -e "${GREEN}[OK]${NC} $description"
            return 0
        else
            echo -e "${RED}[ERROR]${NC} $description"
            ((errors_found++))
            return 1
        fi
    else
        echo -e "${RED}[ERROR]${NC} No se puede verificar '$description' - Archivo no encontrado: $file"
        ((errors_found++))
        return 1
    fi
}

echo -e "${YELLOW}1. Verificando archivos esenciales...${NC}"
echo ""

check_file ".env" "Archivo .env principal"
check_file "docker-compose.prod.yml" "Docker Compose de producción"
check_file "ssl/fullchain.pem" "Certificado SSL" false
check_file "ssl/privkey.pem" "Clave privada SSL" false

echo ""
echo -e "${YELLOW}2. Verificando configuración de seguridad...${NC}"
echo ""

if [ -f ".env" ]; then
    # Verificar DEBUG
    if grep -q "DEBUG=False" .env; then
        echo -e "${GREEN}[OK]${NC} DEBUG está en False (producción)"
    else
        echo -e "${RED}[ERROR]${NC} DEBUG debe estar en False para producción"
        ((errors_found++))
    fi
    
    # Verificar SECRET_KEY
    if grep -q "SECRET_KEY.*CHANGE" .env; then
        echo -e "${RED}[ERROR]${NC} SECRET_KEY no ha sido cambiada - CRÍTICO"
        ((errors_found++))
    else
        echo -e "${GREEN}[OK]${NC} SECRET_KEY ha sido configurada"
    fi
    
    # Verificar CORS_ALLOW_ALL
    if grep -q "CORS_ALLOW_ALL=False" .env; then
        echo -e "${GREEN}[OK]${NC} CORS_ALLOW_ALL está en False (seguro)"
    else
        echo -e "${YELLOW}[WARN]${NC} CORS_ALLOW_ALL debería estar en False para producción"
        ((warnings_found++))
    fi
    
    # Verificar CORS_ORIGINS
    if grep -q "CORS_ORIGINS=.*" .env; then
        echo -e "${GREEN}[OK]${NC} CORS_ORIGINS está configurado"
    else
        echo -e "${RED}[ERROR]${NC} CORS_ORIGINS debe estar configurado"
        ((errors_found++))
    fi
    
    # Verificar ALLOWED_HOSTS
    if grep -q "ALLOWED_HOSTS=.*" .env; then
        echo -e "${GREEN}[OK]${NC} ALLOWED_HOSTS está configurado"
    else
        echo -e "${RED}[ERROR]${NC} ALLOWED_HOSTS debe estar configurado"
        ((errors_found++))
    fi
    
    # Verificar contraseñas por defecto
    if grep -q "CHANGE_THIS" .env; then
        echo -e "${RED}[ERROR]${NC} Hay contraseñas sin cambiar (contienen 'CHANGE_THIS')"
        ((errors_found++))
    else
        echo -e "${GREEN}[OK]${NC} Las contraseñas parecen haber sido cambiadas"
    fi
fi

echo ""
echo -e "${YELLOW}3. Verificando configuración del frontend...${NC}"
echo ""

check_content "frontend/nuxt.config.ts" "serverBundle" "Configuración de iconos serverBundle"
check_content "frontend/middleware/auth.ts" "loadFromStorage" "Middleware de autenticación actualizado"

echo ""
echo -e "${YELLOW}4. Verificando configuración del backend...${NC}"
echo ""

check_file "backend/apps/api/auth_serializers.py" "Serializer personalizado de autenticación"
check_content "backend/apps/api/views.py" "CustomTokenObtainPairView" "Vista personalizada de login"
check_content "backend/config/settings.py" "CORS_ORIGIN_ALLOW_ALL.*default=False" "CORS seguro por defecto"

echo ""
echo -e "${YELLOW}5. Verificando estructura de directorios...${NC}"
echo ""

directories=("logs" "ssl" "backend/static" "backend/media")

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${BLUE}[CREATED]${NC} Directorio creado: $dir"
    else
        echo -e "${GREEN}[OK]${NC} Directorio existe: $dir"
    fi
done

echo ""
echo -e "${CYAN}===========================================================${NC}"
echo -e "${CYAN}   RESUMEN DE VERIFICACIÓN${NC}"
echo -e "${CYAN}===========================================================${NC}"
echo ""

if [ $errors_found -eq 0 ] && [ $warnings_found -eq 0 ]; then
    echo -e "${GREEN}✅ ÉXITO: No se encontraron errores ni advertencias${NC}"
    echo ""
    echo -e "${GREEN}El sistema está listo para producción.${NC}"
    echo ""
    echo -e "${CYAN}Próximos pasos:${NC}"
    echo -e "  ${NC}1. docker-compose -f docker-compose.prod.yml build"
    echo -e "  2. docker-compose -f docker-compose.prod.yml up -d"
    echo -e "  3. docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate"
    echo -e "  4. docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser${NC}"
    echo ""
    exit 0
else
    echo -e "${YELLOW}⚠️  ADVERTENCIA: Se encontraron problemas${NC}"
    echo ""
    echo -e "${RED}Errores críticos: $errors_found${NC}"
    echo -e "${YELLOW}Advertencias: $warnings_found${NC}"
    echo ""
    
    if [ $errors_found -gt 0 ]; then
        echo -e "${RED}❌ NO DESPLEGAR: Hay errores críticos que deben corregirse${NC}"
        echo ""
        echo -e "${CYAN}Pasos recomendados:${NC}"
        echo -e "  ${NC}1. Revisar los errores anteriores"
        echo -e "  2. Consultar PRODUCCION_CONFIG.md para más información"
        echo -e "  3. Corregir los problemas y ejecutar este script nuevamente${NC}"
        echo ""
        exit 1
    else
        echo -e "${YELLOW}⚠️  PRECAUCIÓN: Hay advertencias pero el sistema puede desplegarse${NC}"
        echo ""
        echo -e "${YELLOW}Se recomienda revisar las advertencias antes de continuar.${NC}"
        echo ""
        exit 0
    fi
fi
