@echo off
REM Script de inicialización de VoziPOmni Contact Center para Windows

echo ================================================
echo   VoziPOmni Contact Center - Inicializacion
echo ================================================
echo.

REM Verificar Docker
echo Verificando prerequisitos...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [X] Docker no esta instalado
    exit /b 1
)
echo [OK] Docker instalado

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [X] Docker Compose no esta instalado
    exit /b 1
)
echo [OK] Docker Compose instalado

REM Crear directorios necesarios
echo.
echo Creando directorios...
if not exist "backend\logs" mkdir backend\logs
if not exist "backend\static" mkdir backend\static
if not exist "backend\media" mkdir backend\media
if not exist "backend\recordings" mkdir backend\recordings
echo [OK] Directorios creados

REM Construir imágenes
echo.
echo Construyendo imagenes Docker (esto puede tardar varios minutos)...
docker-compose build
if errorlevel 1 (
    echo [X] Error al construir imagenes
    exit /b 1
)
echo [OK] Imagenes construidas exitosamente

REM Iniciar servicios de base de datos
echo.
echo Iniciando servicios de base de datos...
docker-compose up -d postgres redis

REM Esperar a que PostgreSQL esté listo
echo Esperando a que PostgreSQL este listo...
timeout /t 10 /nobreak >nul

REM Ejecutar migraciones
echo.
echo Ejecutando migraciones de base de datos...
docker-compose run --rm backend python manage.py migrate
if errorlevel 1 (
    echo [X] Error en migraciones
    exit /b 1
)
echo [OK] Migraciones ejecutadas

REM Crear superusuario
echo.
echo Creando superusuario por defecto...
docker-compose run --rm backend python manage.py shell -c "from apps.users.models import User; User.objects.create_superuser('admin', 'admin@vozipomni.local', 'admin123') if not User.objects.filter(username='admin').exists() else print('Superusuario ya existe')"

REM Iniciar todos los servicios
echo.
echo Iniciando todos los servicios...
docker-compose up -d
if errorlevel 1 (
    echo [X] Error al iniciar servicios
    exit /b 1
)
echo [OK] Todos los servicios iniciados

REM Esperar inicio
echo.
echo Esperando a que todos los servicios esten listos...
timeout /t 15 /nobreak >nul

REM Mostrar información
echo.
echo ================================================
echo   VoziPOmni instalado exitosamente!
echo ================================================
echo.
echo [OK] Frontend: http://localhost
echo [OK] Frontend Dev: http://localhost:3000
echo [OK] API REST: http://localhost/api
echo [OK] Admin Django: http://localhost/admin
echo [OK] Documentacion API: http://localhost/api/docs
echo.
echo Credenciales de administrador:
echo   Usuario: admin
echo   Contraseña: admin123
echo.
echo [!] IMPORTANTE! Cambia la contraseña del administrador en produccion
echo.
echo Ver logs:
echo   docker-compose logs -f
echo.
echo Detener servicios:
echo   docker-compose down
echo.
echo ================================================
pause
