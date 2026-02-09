@echo off
echo ========================================
echo  REINICIAR FRONTEND - VoziPOmni
echo ========================================
echo.

echo 1. Deteniendo servidor frontend...
taskkill /F /IM node.exe 2>nul
timeout /t 2 >nul

echo 2. Limpiando cache de Vite...
cd frontend
if exist node_modules\.vite (
    rmdir /s /q node_modules\.vite
    echo    Cache de Vite eliminado
)

echo 3. Iniciando servidor de desarrollo...
echo    Presiona Ctrl+C para detener
echo.
npm run dev

pause
