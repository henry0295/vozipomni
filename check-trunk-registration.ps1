# Script de diagnóstico: Verificar estado de registros PJSIP
# Uso: .\check-trunk-registration.ps1
# Nota: Este script necesita SSH configurado para conectarse al servidor

param(
    [string]$ServerIP = "",
    [string]$ServerUser = "root",
    [int]$ServerPort = 22
)

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "  DIAGNÓSTICO DE REGISTROS PJSIP" -ForegroundColor Cyan
Write-Host "==========================================`n" -ForegroundColor Cyan

if ([string]::IsNullOrWhiteSpace($ServerIP)) {
    Write-Host "⚠️  Modo Local (asume que tienes Docker corriendo localmente)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Para verificar un servidor remoto, ejecuta:" -ForegroundColor Yellow
    Write-Host "  .\check-trunk-registration.ps1 -ServerIP x.x.x.x -ServerUser usuario" -ForegroundColor White
    Write-Host ""
    
    # Verificar Docker local
    try {
        $dockerPs = docker compose ps 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Docker Compose no está disponible o no hay contenedores corriendo" -ForegroundColor Red
            Write-Host "   Este script está diseñado para verificar el servidor de producción" -ForegroundColor Yellow
            exit 1
        }
    } catch {
        Write-Host "❌ Docker no está disponible en este sistema" -ForegroundColor Red
        Write-Host ""
        Write-Host "Opciones:" -ForegroundColor Yellow
        Write-Host "  1. Ejecutar con -ServerIP para verificar servidor remoto" -ForegroundColor White
        Write-Host "  2. Este es el código fuente; el servidor está en Linux" -ForegroundColor White
        exit 1
    }
    
    $RemoteMode = $false
} else {
    Write-Host "🌐 Modo Remoto: Conectando a $ServerUser@$ServerIP" -ForegroundColor Green
    $RemoteMode = $true
    
    # Verificar SSH
    $sshTest = ssh -o ConnectTimeout=5 -p $ServerPort "$ServerUser@$ServerIP" "echo OK" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ No se pudo conectar por SSH a $ServerIP" -ForegroundColor Red
        Write-Host "   Verifica: ssh $ServerUser@$ServerIP" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "✅ Conexión SSH establecida`n" -ForegroundColor Green
}

function Invoke-Command-Local-Or-Remote {
    param([string]$Command)
    
    if ($RemoteMode) {
        ssh -p $ServerPort "$ServerUser@$ServerIP" "cd /opt/vozipomni && $Command" 2>&1
    } else {
        Invoke-Expression $Command
    }
}

# 1. Verificar troncales en la base de datos
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "📊 TRONCALES EN BASE DE DATOS (Django)" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor DarkGray

$djangoShellScript = @'
from apps.telephony.models import SIPTrunk
trunks = SIPTrunk.objects.all()
if not trunks:
    print("⚠️  No hay troncales configuradas en la base de datos")
else:
    print(f"Total de troncales: {trunks.count()}\n")
    for trunk in trunks:
        print(f"  • {trunk.name}")
        print(f"    Host: {trunk.host}:{trunk.port}")
        print(f"    Usuario: {trunk.username}")
        print(f"    Protocolo: {trunk.protocol}")
        print(f"    Estado: {'Activo' if trunk.is_active else 'Inactivo'}")
        print("")
'@

$result = Invoke-Command-Local-Or-Remote "docker compose exec -T backend python manage.py shell << 'PYEOF'`n$djangoShellScript`nPYEOF"
Write-Host $result

Write-Host ""

# 2. Verificar registros PJSIP en Asterisk
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "📡 REGISTROS PJSIP EN ASTERISK" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor DarkGray

$registrations = Invoke-Command-Local-Or-Remote 'docker compose exec -T asterisk asterisk -rx "pjsip show registrations"'

if ($registrations -match "No objects found") {
    Write-Host "⚠️  No hay objetos de tipo [registration] configurados en Asterisk`n" -ForegroundColor Yellow
    Write-Host "Esto significa que las troncales no tienen configurado el componente" -ForegroundColor White
    Write-Host "de REGISTRO en /etc/asterisk/pjsip.conf`n" -ForegroundColor White
    Write-Host "Para configurar un registro, agrega en pjsip.conf:`n" -ForegroundColor Cyan
    Write-Host "  [nombre_troncal-reg]" -ForegroundColor White
    Write-Host "  type=registration" -ForegroundColor White
    Write-Host "  transport=transport-udp" -ForegroundColor White
    Write-Host "  outbound_auth=nombre_troncal-auth" -ForegroundColor White
    Write-Host "  server_uri=sip:proveedor.com" -ForegroundColor White
    Write-Host "  client_uri=sip:usuario@proveedor.com" -ForegroundColor White
    Write-Host "  retry_interval=60`n" -ForegroundColor White
} else {
    Write-Host $registrations
    
    $registeredCount = ($registrations | Select-String "Registered" -AllMatches).Matches.Count
    $totalLines = ($registrations | Select-String "^\s+\S+/sip:" -AllMatches).Matches.Count
    
    Write-Host ""
    if ($registeredCount -gt 0) {
        Write-Host "✅ Registros activos: $registeredCount de $totalLines" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Ningún registro activo (0 de $totalLines)" -ForegroundColor Yellow
    }
}

Write-Host ""

# 3. Verificar endpoints PJSIP
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "📞 ENDPOINTS PJSIP EN ASTERISK" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor DarkGray

$endpoints = Invoke-Command-Local-Or-Remote 'docker compose exec -T asterisk asterisk -rx "pjsip show endpoints"'

if ($endpoints -match "No objects found") {
    Write-Host "❌ No hay endpoints configurados en Asterisk" -ForegroundColor Red
} else {
    $endpointsLines = $endpoints -split "`n" | Select-Object -First 20
    Write-Host ($endpointsLines -join "`n")
    
    $endpointCount = ($endpoints | Select-String "^\s+\S+/\S+" -AllMatches).Matches.Count
    Write-Host "`nTotal de endpoints: $endpointCount" -ForegroundColor White
}

Write-Host ""

# 4. Verificar estado detallado de cada troncal
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "🔍 ESTADO DETALLADO POR TRONCAL" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor DarkGray

$getTrunkNamesScript = @'
from apps.telephony.models import SIPTrunk
for trunk in SIPTrunk.objects.all():
    print(trunk.name)
'@

$trunkNames = Invoke-Command-Local-Or-Remote "docker compose exec -T backend python manage.py shell << 'PYEOF'`n$getTrunkNamesScript`nPYEOF"
$trunkNamesArray = $trunkNames -split "`n" | Where-Object { $_.Trim() -ne "" }

if ($trunkNamesArray.Count -eq 0) {
    Write-Host "⚠️  No hay troncales en la base de datos" -ForegroundColor Yellow
} else {
    foreach ($trunkName in $trunkNamesArray) {
        $trunkName = $trunkName.Trim()
        if ([string]::IsNullOrWhiteSpace($trunkName)) { continue }
        
        Write-Host ""
        Write-Host "  📌 Troncal: $trunkName" -ForegroundColor Cyan
        Write-Host "  ─────────────────────────────────────" -ForegroundColor DarkGray
        
        # Verificar endpoint
        $endpointInfo = Invoke-Command-Local-Or-Remote "docker compose exec -T asterisk asterisk -rx 'pjsip show endpoint $trunkName'"
        if ($endpointInfo -match "Unable to find object") {
            Write-Host "    ❌ Endpoint [$trunkName] NO existe en Asterisk" -ForegroundColor Red
        } else {
            Write-Host "    ✅ Endpoint [$trunkName] existe" -ForegroundColor Green
        }
        
        # Verificar registro
        $regInfo = Invoke-Command-Local-Or-Remote "docker compose exec -T asterisk asterisk -rx 'pjsip show registration ${trunkName}-reg'"
        if ($regInfo -match "Unable to find object") {
            Write-Host "    ℹ️  Registro [${trunkName}-reg] NO configurado" -ForegroundColor Cyan
            Write-Host "       → Estado: Sin Configurar (Peer sin registro)" -ForegroundColor Gray
        } else {
            # Extraer estado del registro
            $regState = ($regInfo | Select-String "Status\s+:\s+(.+)" -AllMatches).Matches.Groups[1].Value
            if ($regState) {
                Write-Host "    ✅ Registro [${trunkName}-reg] existe" -ForegroundColor Green
                Write-Host "       → Estado: $regState" -ForegroundColor White
            } else {
                Write-Host "    ⚠️  Registro [${trunkName}-reg] existe pero estado desconocido" -ForegroundColor Yellow
            }
        }
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "📋 RESUMEN" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor DarkGray

# Contar troncales en Django
$countTrunksScript = @'
from apps.telephony.models import SIPTrunk
print(SIPTrunk.objects.count())
'@

$djangoTrunks = Invoke-Command-Local-Or-Remote "docker compose exec -T backend python manage.py shell << 'PYEOF'`n$countTrunksScript`nPYEOF"
$djangoTrunks = ($djangoTrunks -split "`n" | Select-Object -Last 2)[0].Trim()

# Contar registros en Asterisk
$asteriskRegsOutput = Invoke-Command-Local-Or-Remote 'docker compose exec -T asterisk asterisk -rx "pjsip show registrations"'
$asteriskRegs = ($asteriskRegsOutput | Select-String "^\s+\S+/sip:" -AllMatches).Matches.Count

Write-Host "  • Troncales en Base de Datos: $djangoTrunks" -ForegroundColor White
Write-Host "  • Registros en Asterisk: $asteriskRegs`n" -ForegroundColor White

if ([int]$djangoTrunks -gt 0 -and [int]$asteriskRegs -eq 0) {
    Write-Host "⚠️  ATENCIÓN:" -ForegroundColor Yellow
    Write-Host "   Tienes troncales en la base de datos pero ningún registro" -ForegroundColor White
    Write-Host "   configurado en Asterisk PJSIP.`n" -ForegroundColor White
    Write-Host "   Si tus troncales requieren registro, configúralos en:" -ForegroundColor Cyan
    Write-Host "   docker/asterisk/configs/pjsip.conf`n" -ForegroundColor White
    Write-Host "   Luego ejecuta:" -ForegroundColor Cyan
    Write-Host "   docker compose exec asterisk asterisk -rx 'pjsip reload'`n" -ForegroundColor White
} elseif ([int]$asteriskRegs -gt 0) {
    Write-Host "✅ Hay registros configurados en Asterisk" -ForegroundColor Green
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "Para más información, consulta:" -ForegroundColor Cyan
Write-Host "  • EXPLICACION_SIN_CONFIGURAR.md" -ForegroundColor White
Write-Host "  • GUIA_PJSIP.md" -ForegroundColor White
Write-Host "  • CONFIGURAR_TRONCALES_REGISTRO.md" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor DarkGray
