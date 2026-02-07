# Instrucciones para Activar el Sistema de Login

## ✅ Estado Actual

El sistema de autenticación **YA ESTÁ IMPLEMENTADO** con:
- ✅ Endpoints JWT: `/api/auth/login/` y `/api/auth/refresh/`
- ✅ Componente de Login funcional
- ✅ Interceptores axios para tokens automáticos
- ✅ Protección de rutas con autenticación

## 🔑 Crear Usuario Administrador

### En el servidor de producción (Linux):

```bash
# Conectar al servidor
ssh usuario@tu-servidor

# Ir al directorio del proyecto
cd /opt/vozipomni

# Crear superusuario interactivamente
docker compose exec backend python manage.py createsuperuser

# Seguir las instrucciones:
# - Username: admin
# - Email: admin@vozipomni.com
# - Password: (tu contraseña segura)
# - Password (again): (repetir)
```

### Verificar que el usuario se creó:

```bash
docker compose exec backend python manage.py shell -c "from apps.users.models import User; print(f'Usuarios: {User.objects.count()}'); [print(f'- {u.username} ({u.role})') for u in User.objects.all()]"
```

## 🚀 Iniciar Sesión

1. **Abrir el navegador**: http://localhost (o http://tu-servidor)

2. **Se mostrará la página de login automáticamente**

3. **Ingresar credenciales**:
   - Usuario: `admin`
   - Contraseña: (la que configuraste)

4. **Presionar "Iniciar Sesión"**

5. **El sistema guardará el token JWT y redirigirá al Dashboard**

## 🔍 Flujo de Autenticación

1. **Login**: POST `/api/auth/login/` → Devuelve `{ access, refresh }`
2. **Tokens guardados**: localStorage.setItem('token', access)
3. **Peticiones API**: Incluyen header `Authorization: Bearer ${token}`
4. **Token expirado**: Se refresca automáticamente con `/api/auth/refresh/`
5. **Logout**: Botón en navbar elimina tokens y recarga página

## 🐛 Troubleshooting

### Error: "Credenciales inválidas"
- Verificar username y password
- Usuario debe existir en base de datos
- Usuario debe estar activo (`is_active=True`)

### Error 401 en API
- Token expirado o inválido
- Hacer logout y login nuevamente

### No se guarda el token
- Verificar console del navegador (F12)
- Verificar respuesta de `/api/auth/login/`

## 📝 Crear Más Usuarios

### Opción 1: Django Admin
1. Ir a: http://localhost/admin/
2. Login con superusuario
3. Ir a "Usuarios" → "Agregar usuario"

### Opción 2: Django Shell
```bash
docker compose exec backend python manage.py shell

from apps.users.models import User
user = User.objects.create_user(
    username='agente1',
    password='password123',
    email='agente1@vozipomni.com',
    role='agent',
    first_name='Juan',
    last_name='Pérez'
)
print(f'Usuario creado: {user}')
```

## 🔐 CORS Ya Configurado

Los errores CORS que veías eran por **falta de autenticación** (401), no por configuración CORS.

El backend devuelve 401 → El navegador no procesa la respuesta → Muestra "CORS error"

Una vez autenticado:
- ✅ Token incluido en header
- ✅ Backend devuelve 200
- ✅ CORS permite la respuesta
- ✅ Frontend recibe los datos

## 🎯 Próximos Pasos

1. ✅ Crear superusuario en servidor
2. ✅ Iniciar sesión en frontend
3. ✅ Verificar que carga extensiones telefónicas
4. ⏳ Implementar integración con Asterisk (siguiente fase)
