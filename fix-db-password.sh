#!/bin/bash
# =============================================================================
# Fix PostgreSQL Password Mismatch
# =============================================================================
# Este script sincroniza la contraseña de PostgreSQL cuando hay conflicto
# entre la BD inicializada y las variables de entorno
# =============================================================================

set -e

echo "═════════════════════════════════════════════════"
echo "  Fix PostgreSQL Password - VoziPOmni v3.0.0"
echo "═════════════════════════════════════════════════"
echo ""

# Verificar que estamos en el directorio correcto
if [[ ! -f "docker-compose.prod.yml" ]]; then
    echo "❌ ERROR: docker-compose.prod.yml no encontrado"
    echo "   Ejecute este script desde /opt/vozipomni"
    exit 1
fi

# Cargar variables del .env
if [[ -f ".env" ]]; then
    set -a
    source .env
    set +a
    echo "✅ Variables cargadas desde .env"
else
    echo "❌ ERROR: archivo .env no encontrado"
    exit 1
fi

# Mostrar contraseña actual en .env
CURRENT_PG_PASS="${POSTGRES_PASSWORD:-vozipomni_db_2026}"
echo ""
echo "Contraseña en .env: $CURRENT_PG_PASS"
echo ""

# Opciones
echo "Opciones de corrección:"
echo ""
echo "1) Cambiar contraseña de PostgreSQL para que coincida con .env"
echo "2) Actualizar .env con la contraseña que usa PostgreSQL"
echo "3) Ver logs del backend para diagnóstico"
echo ""
read -p "Seleccione opción [1-3]: " OPCION

case $OPCION in
    1)
        echo ""
        echo "🔄 Cambiando contraseña de PostgreSQL a: $CURRENT_PG_PASS"
        echo ""
        
        # Cambiar contraseña dentro del contenedor
        docker compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -c "ALTER USER vozipomni_user WITH PASSWORD '$CURRENT_PG_PASS';" || {
            echo "❌ Error cambiando contraseña"
            exit 1
        }
        
        echo "✅ Contraseña actualizada en PostgreSQL"
        echo ""
        echo "🔄 Reiniciando backend..."
        docker compose -f docker-compose.prod.yml restart backend celery_worker celery_beat
        echo ""
        echo "✅ Reinicio completado"
        echo ""
        echo "Verificar logs:"
        echo "  docker compose -f docker-compose.prod.yml logs -f backend"
        ;;
    
    2)
        echo ""
        read -p "Ingrese la contraseña que usa PostgreSQL: " NEW_PASS
        
        if [[ -z "$NEW_PASS" ]]; then
            echo "❌ Contraseña vacía no permitida"
            exit 1
        fi
        
        # Actualizar .env
        if grep -q "^POSTGRES_PASSWORD=" .env; then
            sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$NEW_PASS/" .env
        else
            echo "POSTGRES_PASSWORD=$NEW_PASS" >> .env
        fi
        
        echo "✅ .env actualizado"
        echo ""
        echo "🔄 Reiniciando servicios..."
        docker compose -f docker-compose.prod.yml down
        docker compose -f docker-compose.prod.yml up -d
        echo ""
        echo "✅ Servicios reiniciados con nueva contraseña"
        ;;
    
    3)
        echo ""
        echo "📋 Últimos logs del backend:"
        echo ""
        docker compose -f docker-compose.prod.yml logs --tail=50 backend
        ;;
    
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac

echo ""
echo "═════════════════════════════════════════════════"
