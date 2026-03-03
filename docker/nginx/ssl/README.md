# Certificados SSL

Esta carpeta almacena los certificados SSL para HTTPS.

## Archivos necesarios:
- `vozipomni.crt` - Certificado SSL
- `vozipomni.key` - Clave privada

## Generar certificados:

### Opción 1: Script automático (recomendado)
```bash
# Desde Windows
.\setup-https.ps1

# Desde Linux
./setup-https.sh
```

### Opción 2: Manual con OpenSSL
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout vozipomni.key \
  -out vozipomni.crt \
  -subj "/C=CO/ST=Bogota/L=Bogota/O=VozipOmni/CN=192.168.101.228"
```

## Permisos correctos:
```bash
chmod 644 vozipomni.crt
chmod 600 vozipomni.key
```

⚠️ **IMPORTANTE:** Los archivos `.crt` y `.key` NO se suben a Git por seguridad.

Ver [CONFIGURACION_HTTPS.md](../../CONFIGURACION_HTTPS.md) para más información.
