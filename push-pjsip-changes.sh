#!/bin/bash
# Script para subir cambios de migración PJSIP a Git
# VoziPOmni - Configuración PJSIP

echo "================================================================"
echo "  SUBIENDO CAMBIOS PJSIP A GIT - VoziPOmni"
echo "================================================================"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: No estás en el directorio raíz del proyecto"
    echo "   Ejecuta: cd /opt/vozipomni"
    exit 1
fi

# Ver estado actual
echo "📋 Estado actual del repositorio:"
echo ""
git status
echo ""

# Agregar archivos modificados y nuevos
echo "➕ Agregando archivos al staging..."
echo ""

# Archivos de configuración corregidos
git add docker/asterisk/configs/asterisk.conf

# Archivos Python actualizados
git add backend/apps/telephony/views.py
git add backend/apps/telephony/asterisk_config.py

# Scripts de ayuda
git add asterisk-docker.sh
git add check-pjsip.sh
git add asterisk-helper.ps1
git add test_asterisk_connection.py

# Documentación
git add DIAGNOSTICO_ASTERISK.md
git add SOLUCION_ASTERISK_CLI.md
git add GUIA_PJSIP.md
git add RESUMEN_PJSIP.md

# Archivo de entorno
git add .env

echo "✅ Archivos agregados"
echo ""

# Ver qué se va a commitear
echo "📦 Archivos que serán commiteados:"
echo ""
git status --short
echo ""

# Confirmar
read -p "¿Deseas continuar con el commit? (s/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
    echo "❌ Operación cancelada"
    exit 0
fi

# Crear commit
echo ""
echo "📝 Creando commit..."
git commit -m "fix: Migración completa a PJSIP y corrección de acceso CLI Asterisk

- Fix: Corregido error 'Unable to connect to remote asterisk'
  * Cambiado alwaysfork=no y nofork=yes en asterisk.conf
  * Ahora se puede acceder con: docker compose exec asterisk asterisk -r

- Migración SIP → PJSIP:
  * Actualizado views.py para recargar res_pjsip.so en lugar de chan_sip.so
  * Corregido asterisk_config.py para usar Dial(PJSIP/...) en lugar de Dial(SIP/...)
  * Sistema ahora 100% compatible con PJSIP (Asterisk 21)

- Scripts de ayuda añadidos:
  * asterisk-docker.sh - Gestión completa del contenedor Asterisk
  * check-pjsip.sh - Verificación y diagnóstico de PJSIP
  * asterisk-helper.ps1 - Helper para Windows PowerShell
  * test_asterisk_connection.py - Prueba de conexión AMI

- Documentación completa:
  * DIAGNOSTICO_ASTERISK.md - Guía de diagnóstico general
  * SOLUCION_ASTERISK_CLI.md - Solución específica error CLI
  * GUIA_PJSIP.md - Guía completa de uso de PJSIP
  * RESUMEN_PJSIP.md - Resumen ejecutivo de cambios

- Configuración:
  * Agregado archivo .env para configuración de entorno

Cambios probados y funcionando en Asterisk 21 con Docker.
chan_sip NO está disponible (deprecado) - usar PJSIP."

if [ $? -eq 0 ]; then
    echo "✅ Commit creado exitosamente"
    echo ""
    
    # Mostrar el commit
    echo "📄 Detalles del commit:"
    git log -1 --stat
    echo ""
    
    # Preguntar si desea hacer push
    read -p "¿Deseas hacer push al repositorio remoto? (s/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[SsYy]$ ]]; then
        echo ""
        echo "🚀 Haciendo push..."
        
        # Obtener rama actual
        BRANCH=$(git branch --show-current)
        
        # Hacer push
        git push origin $BRANCH
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "================================================================"
            echo "  ✅ CAMBIOS SUBIDOS EXITOSAMENTE A GIT"
            echo "================================================================"
            echo ""
            echo "Rama: $BRANCH"
            echo ""
            echo "📋 Siguiente paso en el servidor:"
            echo "   cd /opt/vozipomni"
            echo "   git pull origin $BRANCH"
            echo "   docker compose restart asterisk"
            echo ""
        else
            echo ""
            echo "❌ Error al hacer push"
            echo "   Verifica tu conexión y permisos del repositorio"
            echo ""
        fi
    else
        echo ""
        echo "ℹ️  Commit creado pero no se hizo push"
        echo "   Para hacer push manualmente:"
        echo "   git push origin $(git branch --show-current)"
        echo ""
    fi
else
    echo "❌ Error al crear commit"
    exit 1
fi
