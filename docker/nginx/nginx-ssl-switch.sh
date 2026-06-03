#!/bin/sh
# Selecciona automáticamente la configuración HTTPS si existen certificados SSL.
# Este script es ejecutado por el entrypoint de nginx (docker-entrypoint.d/).

SSL_CERT="/etc/nginx/ssl/vozipomni.crt"
SSL_KEY="/etc/nginx/ssl/vozipomni.key"
HTTPS_CONF="/etc/nginx/conf.d/default.https.conf.bak"
ACTIVE_CONF="/etc/nginx/conf.d/default.conf"

if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
    echo "[SSL-switch] Certificados encontrados → activando configuración HTTPS"
    cp "$HTTPS_CONF" "$ACTIVE_CONF"
else
    echo "[SSL-switch] Sin certificados → usando configuración HTTP"
fi
