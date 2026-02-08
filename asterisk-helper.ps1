# Script de diagnóstico y conexión a Asterisk para Windows PowerShell
# VoziPOmni - Asterisk Connection Helper

param(
    [Parameter(Mandatory=$false)]
    [string]$Action = "menu"
)

function Show-Menu {
    Clear-Host
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "  HERRAMIENTA DE CONEXIÓN ASTERISK - VoziPOmni" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. Probar conexión AMI al servidor Asterisk" -ForegroundColor Yellow
    Write-Host "  2. Conectar por SSH al servidor" -ForegroundColor Yellow
    Write-Host "  3. Conectar por SSH y abrir consola Asterisk CLI" -ForegroundColor Yellow
    Write-Host "  4. Ejecutar comando Asterisk remoto via SSH" -ForegroundColor Yellow
    Write-Host "  5. Ver configuración actual (.env)" -ForegroundColor Yellow
    Write-Host "  6. Editar configuración (.env)" -ForegroundColor Yellow
    Write-Host "  7. Ver guía de diagnóstico completa" -ForegroundColor Yellow
    Write-Host "  0. Salir" -ForegroundColor Red
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-AsteriskConnection {
    Write-Host "`n🔌 Probando conexión AMI a Asterisk...`n" -ForegroundColor Green
    
    $scriptPath = Join-Path $PSScriptRoot "test_asterisk_connection.py"
    
    if (Test-Path $scriptPath) {
        python $scriptPath
    } else {
        Write-Host "❌ No se encontró el script test_asterisk_connection.py" -ForegroundColor Red
        Write-Host "   Ruta esperada: $scriptPath" -ForegroundColor Yellow
    }
    
    Write-Host "`nPresiona cualquier tecla para continuar..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

function Connect-SSH {
    Write-Host "`n🔐 Conexión SSH al servidor Asterisk`n" -ForegroundColor Green
    
    $host_ip = Read-Host "Ingresa la IP o dominio del servidor"
    $username = Read-Host "Ingresa el usuario SSH"
    
    Write-Host "`n🔑 Opciones de autenticación:" -ForegroundColor Cyan
    Write-Host "  1. Contraseña"
    Write-Host "  2. Clave privada (.pem o .ppk)"
    $auth_method = Read-Host "Selecciona método"
    
    if ($auth_method -eq "2") {
        $key_path = Read-Host "Ruta completa de la clave privada"
        Write-Host "`n📡 Conectando a $username@$host_ip con clave privada..." -ForegroundColor Yellow
        ssh -i $key_path "$username@$host_ip"
    } else {
        Write-Host "`n📡 Conectando a $username@$host_ip..." -ForegroundColor Yellow
        ssh "$username@$host_ip"
    }
}

function Connect-AsteriskCLI {
    Write-Host "`n📞 Conexión SSH + Consola Asterisk CLI`n" -ForegroundColor Green
    
    $host_ip = Read-Host "Ingresa la IP o dominio del servidor"
    $username = Read-Host "Ingresa el usuario SSH"
    
    Write-Host "`n🔑 Opciones de autenticación:" -ForegroundColor Cyan
    Write-Host "  1. Contraseña"
    Write-Host "  2. Clave privada (.pem o .ppk)"
    $auth_method = Read-Host "Selecciona método"
    
    $ssh_cmd = if ($auth_method -eq "2") {
        $key_path = Read-Host "Ruta completa de la clave privada"
        "ssh -i `"$key_path`" $username@$host_ip"
    } else {
        "ssh $username@$host_ip"
    }
    
    Write-Host "`n📡 Conectando a Asterisk CLI en $host_ip..." -ForegroundColor Yellow
    Write-Host "   Ejecutarás: sudo asterisk -rvvv" -ForegroundColor Gray
    Write-Host "`n💡 Comandos útiles en CLI:" -ForegroundColor Cyan
    Write-Host "   - core show version      (ver versión)" -ForegroundColor Gray
    Write-Host "   - core show channels     (llamadas activas)" -ForegroundColor Gray
    Write-Host "   - pjsip show endpoints   (extensiones PJSIP)" -ForegroundColor Gray
    Write-Host "   - exit                   (salir)`n" -ForegroundColor Gray
    
    # Ejecutar SSH con comando para entrar a Asterisk CLI
    $full_cmd = "$ssh_cmd 'sudo asterisk -rvvv'"
    Invoke-Expression $full_cmd
}

function Run-RemoteAsteriskCommand {
    Write-Host "`n⚡ Ejecutar comando Asterisk remoto`n" -ForegroundColor Green
    
    $host_ip = Read-Host "Ingresa la IP o dominio del servidor"
    $username = Read-Host "Ingresa el usuario SSH"
    
    Write-Host "`n📋 Comandos comunes:" -ForegroundColor Cyan
    Write-Host "  1. core show version"
    Write-Host "  2. core show channels"
    Write-Host "  3. pjsip show endpoints"
    Write-Host "  4. manager show connected"
    Write-Host "  5. Comando personalizado"
    
    $cmd_choice = Read-Host "`nSelecciona comando (1-5)"
    
    $asterisk_cmd = switch ($cmd_choice) {
        "1" { "core show version" }
        "2" { "core show channels verbose" }
        "3" { "pjsip show endpoints" }
        "4" { "manager show connected" }
        "5" { Read-Host "Ingresa el comando Asterisk" }
        default { "core show version" }
    }
    
    Write-Host "`n⚙️  Ejecutando: asterisk -rx '$asterisk_cmd'`n" -ForegroundColor Yellow
    
    ssh "$username@$host_ip" "sudo asterisk -rx '$asterisk_cmd'"
    
    Write-Host "`nPresiona cualquier tecla para continuar..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

function Show-CurrentConfig {
    Write-Host "`n⚙️  Configuración actual (.env)`n" -ForegroundColor Green
    
    $envPath = Join-Path $PSScriptRoot ".env"
    
    if (Test-Path $envPath) {
        Write-Host "================================================================" -ForegroundColor Cyan
        Get-Content $envPath | Where-Object {
            $_ -match "ASTERISK_" -or $_ -match "DB_" -or $_ -match "REDIS_"
        } | ForEach-Object {
            if ($_ -match "PASSWORD|SECRET") {
                $line = $_ -replace '=.*', '=********'
                Write-Host $line -ForegroundColor Yellow
            } else {
                Write-Host $_ -ForegroundColor White
            }
        }
        Write-Host "================================================================" -ForegroundColor Cyan
    } else {
        Write-Host "❌ No se encontró el archivo .env" -ForegroundColor Red
        Write-Host "   Ruta esperada: $envPath" -ForegroundColor Yellow
    }
    
    Write-Host "`nPresiona cualquier tecla para continuar..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

function Edit-Config {
    Write-Host "`n📝 Editando configuración (.env)`n" -ForegroundColor Green
    
    $envPath = Join-Path $PSScriptRoot ".env"
    
    if (Test-Path $envPath) {
        # Intentar abrir con VS Code si está disponible
        if (Get-Command code -ErrorAction SilentlyContinue) {
            code $envPath
            Write-Host "✅ Archivo .env abierto en VS Code" -ForegroundColor Green
        } else {
            # Usar notepad como fallback
            notepad $envPath
            Write-Host "✅ Archivo .env abierto en Notepad" -ForegroundColor Green
        }
    } else {
        Write-Host "❌ No se encontró el archivo .env" -ForegroundColor Red
        Write-Host "   ¿Deseas crear uno nuevo? (S/N)" -ForegroundColor Yellow
        $create = Read-Host
        
        if ($create -eq "S" -or $create -eq "s") {
            Write-Host "`n📋 Creando archivo .env...`n" -ForegroundColor Green
            
            $ast_host = Read-Host "IP del servidor Asterisk"
            $ast_port = Read-Host "Puerto AMI [5038]"
            if ([string]::IsNullOrWhiteSpace($ast_port)) { $ast_port = "5038" }
            $ast_user = Read-Host "Usuario AMI [admin]"
            if ([string]::IsNullOrWhiteSpace($ast_user)) { $ast_user = "admin" }
            $ast_pass = Read-Host "Contraseña AMI"
            
            $envContent = @"
# VoziPOmni Environment Variables

# Django
DEBUG=True
SECRET_KEY=vozipomni-secret-key-change-in-production-2026

# Database
DB_NAME=vozipomni_db
DB_USER=vozipomni_user
DB_PASSWORD=vozipomni_pass_2026
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Asterisk - Servidor Remoto
ASTERISK_HOST=$ast_host
ASTERISK_AMI_PORT=$ast_port
ASTERISK_AMI_USER=$ast_user
ASTERISK_AMI_PASSWORD=$ast_pass

# Security
ALLOWED_HOSTS=localhost,127.0.0.1,backend
CORS_ORIGINS=http://localhost:3000,http://localhost:80,http://localhost:5173

# API
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
VITE_ASTERISK_WS=wss://localhost:8089/ws
"@
            
            $envContent | Out-File -FilePath $envPath -Encoding UTF8
            Write-Host "`n✅ Archivo .env creado exitosamente" -ForegroundColor Green
            Write-Host "   Ubicación: $envPath`n" -ForegroundColor Gray
        }
    }
    
    Write-Host "`nPresiona cualquier tecla para continuar..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

function Show-DiagnosticGuide {
    Write-Host "`n📖 Abriendo guía de diagnóstico...`n" -ForegroundColor Green
    
    $guidePath = Join-Path $PSScriptRoot "DIAGNOSTICO_ASTERISK.md"
    
    if (Test-Path $guidePath) {
        if (Get-Command code -ErrorAction SilentlyContinue) {
            code $guidePath
            Write-Host "✅ Guía abierta en VS Code" -ForegroundColor Green
        } else {
            Start-Process $guidePath
            Write-Host "✅ Guía abierta" -ForegroundColor Green
        }
    } else {
        Write-Host "❌ No se encontró DIAGNOSTICO_ASTERISK.md" -ForegroundColor Red
    }
    
    Write-Host "`nPresiona cualquier tecla para continuar..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Menú principal
do {
    Show-Menu
    $selection = Read-Host "Selecciona una opción"
    
    switch ($selection) {
        '1' { Test-AsteriskConnection }
        '2' { Connect-SSH }
        '3' { Connect-AsteriskCLI }
        '4' { Run-RemoteAsteriskCommand }
        '5' { Show-CurrentConfig }
        '6' { Edit-Config }
        '7' { Show-DiagnosticGuide }
        '0' { 
            Write-Host "`n👋 ¡Hasta luego!`n" -ForegroundColor Green
            return 
        }
        default {
            Write-Host "`n❌ Opción inválida`n" -ForegroundColor Red
            Start-Sleep -Seconds 2
        }
    }
} while ($selection -ne '0')
