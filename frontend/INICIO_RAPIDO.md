# 🚀 Inicio Rápido - Frontend Nuxt 3

## Instalación y Ejecución

### 1. Instalar Dependencias

```powershell
cd frontend
npm install
```

### 2. Configurar Variables de Entorno

```powershell
cp .env.example .env
```

Editar `.env` con las URLs correctas:
```env
NUXT_PUBLIC_API_BASE=http://localhost:8000/api
NUXT_PUBLIC_WS_BASE=ws://localhost:8000/ws
```

### 3. Ejecutar en Desarrollo

```powershell
npm run dev
```

Abre tu navegador en: **http://localhost:3000**

## 🔑 Credenciales de Prueba

Si el backend está configurado, usa las credenciales existentes del sistema.

```
Usuario: admin
Contraseña: [tu contraseña]
```

## 📋 Verificación Rápida

### ✅ Checklist de Verificación

- [ ] La aplicación se inicia sin errores
- [ ] La página de login se muestra correctamente
- [ ] El diseño es responsive
- [ ] Los iconos se muestran correctamente
- [ ] Nuxt UI está funcionando

### 🔧 Solución de Problemas

**Error: Cannot find module**
```powershell
rm -rf node_modules
rm package-lock.json
npm install
```

**Puerto 3000 en uso**
```powershell
# Cambiar puerto en nuxt.config.ts o usar:
npm run dev -- --port 3001
```

**Error de TypeScript**
```powershell
npm run postinstall
```

## 📦 Comandos Disponibles

```powershell
# Desarrollo
npm run dev

# Compilar para producción
npm run build

# Previsualizar compilación
npm run preview

# Linting
npm run lint
npm run lint:fix

# Generar sitio estático
npm run generate
```

## 🐳 Ejecutar con Docker

### Desarrollo
```powershell
docker build -f Dockerfile.dev -t vozipomni-frontend-dev .
docker run -p 3000:3000 -v ${PWD}:/app vozipomni-frontend-dev
```

### Producción
```powershell
docker build -t vozipomni-frontend .
docker run -p 3000:3000 vozipomni-frontend
```

## 🔗 Estructura de URLs

- `/` → Redirección a dashboard o login
- `/login` → Inicio de sesión
- `/dashboard` → Panel principal
- `/agents` → Gestión de agentes
- `/queues` → Gestión de colas
- `/campaigns` → Campañas
- `/contacts` → Contactos
- `/reports` → Reportes
- `/settings` → Configuración

## 🎨 Características UI

### Nuxt UI Components
- UCard, UButton, UInput, UTable
- UModal, UDropdown, UBadge
- UIcon (Heroicons + Lucide)

### Tailwind CSS
- Utility-first CSS
- Responsive design
- Custom colors y themes

## 🔐 Autenticación

El sistema usa JWT tokens:
1. Login en `/login`
2. Token guardado en localStorage
3. Header `Authorization: Bearer {token}` en todas las requests
4. Middleware protege rutas privadas

## 📡 Conexión con Backend

### API REST
```typescript
const { apiFetch } = useApi()
const { data } = await apiFetch('/agents/')
```

### WebSocket (preparado)
```typescript
const { connect, onMessage } = useWebSocket()
connect('/call-center/')
onMessage((data) => console.log(data))
```

## 🎯 Próximos Pasos

1. **Verificar backend Django está corriendo**
   ```powershell
   # En otra terminal
   cd backend
   python manage.py runserver
   ```

2. **Configurar CORS en Django** (si no está)
   ```python
   CORS_ALLOWED_ORIGINS = [
       "http://localhost:3000",
   ]
   ```

3. **Probar login** con credenciales reales

4. **Implementar funcionalidades específicas** de tu negocio

## 📚 Documentación

- [README.md](README.md) - Documentación completa
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Guía de migración
- [Nuxt 3 Docs](https://nuxt.com)
- [Nuxt UI Docs](https://ui.nuxt.com)
- [Vue 3 Docs](https://vuejs.org)

## 🆘 Ayuda

Si tienes problemas:
1. Revisa la consola del navegador
2. Revisa la terminal donde corre `npm run dev`
3. Verifica que el backend esté corriendo
4. Revisa las variables de entorno en `.env`

---

**¡Listo para desarrollar! 🎉**
