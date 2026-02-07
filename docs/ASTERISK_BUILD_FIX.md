# Guía de Resolución de Problemas - Asterisk Build

## 🔴 Error: Asterisk 20.6.0 Not Found (404)

### Problema
```
404 Not Found
https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-20.6.0.tar.gz
```

Este error ocurre porque las versiones antiguas de Asterisk pueden ser removidas del servidor principal de descargas.

---

## ✅ Soluciones Disponibles

### **Solución 1: Actualizar a Asterisk 21 LTS (Recomendado)** ⭐

Asterisk 21 es la versión LTS (Long Term Support) actual y está disponible.

#### Opción A: Usar el Dockerfile actualizado

El archivo `docker/asterisk/Dockerfile` ya fue actualizado a Asterisk 21.2.0:

```bash
docker-compose build asterisk
docker-compose up -d asterisk
```

#### Opción B: Usar compilación desde Git (más confiable)

Usar `Dockerfile.source` que clona desde GitHub:

```bash
# Renombrar archivos
cd docker/asterisk
mv Dockerfile Dockerfile.old
mv Dockerfile.source Dockerfile

# Reconstruir
docker-compose build --no-cache asterisk
```

---

### **Solución 2: Usar Imagen Pre-compilada (Más Rápido)** 🚀

**Ventajas:**
- ✅ Build 10x más rápido (segundos vs minutos)
- ✅ No necesita compilación
- ✅ Imagen probada y estable
- ✅ Menor probabilidad de errores

#### Paso 1: Usar Dockerfile pre-compilado

```bash
cd docker/asterisk
mv Dockerfile Dockerfile.compile
mv Dockerfile.prebuilt Dockerfile
```

#### Paso 2: Reconstruir

```bash
docker-compose build --no-cache asterisk
docker-compose up -d
```

---

### **Solución 3: Versión Específica Disponible**

Si necesitas una versión específica, verifica qué versiones están disponibles:

1. **Visita:** https://downloads.asterisk.org/pub/telephony/asterisk/
2. **Busca versiones certificadas:** `certified-*` (más estables)
3. **Actualiza** el `ASTERISK_VERSION` en el Dockerfile

Ejemplo:
```dockerfile
ENV ASTERISK_VERSION=certified-21.0-cert1
```

---

## 🔧 Comparación de Opciones

| Método | Tiempo Build | Confiabilidad | Personalización | Tamaño Imagen |
|--------|--------------|---------------|-----------------|---------------|
| **Compilar 21 (Git)** | ~15-20 min | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ~500 MB |
| **Pre-compilado** | ~1-2 min | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ~300 MB |
| **Compilar 20** | ❌ No disponible | - | - | - |

---

## 📝 Cambios Necesarios en docker-compose.yml

Si usas Dockerfile pre-compilado, actualiza el build context:

```yaml
asterisk:
  build:
    context: ./docker/asterisk
    dockerfile: Dockerfile  # o Dockerfile.prebuilt
  image: vozipomni-asterisk:21
  # ... resto de configuración
```

---

## 🧪 Verificar la Instalación

Después de reconstruir:

```bash
# 1. Verificar que Asterisk esté corriendo
docker-compose ps asterisk

# 2. Ver logs
docker-compose logs asterisk

# 3. Conectar a CLI de Asterisk
docker-compose exec asterisk asterisk -rvvv

# 4. Verificar versión
asterisk*CLI> core show version

# 5. Verificar módulos PJSIP
asterisk*CLI> module show like pjsip

# 6. Verificar WebSocket
asterisk*CLI> http show status
```

---

## 🐛 Troubleshooting

### Build falla con "No space left on device"

```bash
# Limpiar imágenes antiguas
docker system prune -a

# Limpiar cache de build
docker builder prune -a
```

### Build muy lento

**Usar imagen pre-compilada:**
```bash
cd docker/asterisk
mv Dockerfile.prebuilt Dockerfile
docker-compose build asterisk
```

### Módulos PJSIP no cargan

```bash
# Verificar que estén habilitados
docker-compose exec asterisk asterisk -rx "module show like pjsip"

# Cargar manualmente si es necesario
docker-compose exec asterisk asterisk -rx "module load res_pjsip.so"
```

### WebRTC no funciona

```bash
# Verificar transport WebSocket
docker-compose exec asterisk asterisk -rx "pjsip show transports"

# Debería mostrar transport-wss en puerto 8089
```

---

## 🚀 Recomendación Final

### Para Desarrollo:
Usar **Dockerfile.prebuilt** (rápido, confiable)

### Para Producción:
Usar **Dockerfile.source** con Git clone (compilación limpia desde fuente certificada)

### Para Testing Rápido:
Usar imagen oficial directamente en `docker-compose.yml`:

```yaml
asterisk:
  image: andrius/asterisk:21-alpine
  volumes:
    - ./docker/asterisk/configs:/etc/asterisk:ro
  # ... resto de configuración
```

---

## 📚 Referencias

- [Asterisk Downloads](https://www.asterisk.org/downloads/)
- [Asterisk GitHub Releases](https://github.com/asterisk/asterisk/releases)
- [Asterisk Docker Hub](https://hub.docker.com/r/andrius/asterisk)
- [Asterisk Wiki](https://wiki.asterisk.org/)
