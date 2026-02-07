# VoziPOmni - GitHub Setup Script (PowerShell)
# Execute with: .\push-to-github.ps1

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host "  VoziPOmni - Configuración de GitHub" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host ""

# Verificar si Git está instalado
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Git no está instalado" -ForegroundColor Red
    Write-Host "Descarga Git desde: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Git instalado: " -NoNewline -ForegroundColor Green
git --version

# Solicitar información del usuario
Write-Host ""
Write-Host "Por favor ingresa la siguiente información:" -ForegroundColor Cyan
Write-Host ""

$username = Read-Host "Tu nombre de usuario de GitHub"
$isOrganization = Read-Host "¿Es una organización? (S/N)" 

if ($isOrganization -eq "S" -or $isOrganization -eq "s") {
    $repoOwner = Read-Host "Nombre de la organización"
} else {
    $repoOwner = $username
}

$repoName = Read-Host "Nombre del repositorio (default: vozipomni)"
if ([string]::IsNullOrWhiteSpace($repoName)) {
    $repoName = "vozipomni"
}

# Construir URL del repositorio
$repoUrl = "https://github.com/$repoOwner/$repoName.git"

Write-Host ""
Write-Host "Configuración:" -ForegroundColor Cyan
Write-Host "  Propietario: $repoOwner" -ForegroundColor White
Write-Host "  Repositorio: $repoName" -ForegroundColor White
Write-Host "  URL: $repoUrl" -ForegroundColor White
Write-Host ""

$confirm = Read-Host "¿Es correcta esta información? (S/N)"
if ($confirm -ne "S" -and $confirm -ne "s") {
    Write-Host "Operación cancelada" -ForegroundColor Yellow
    exit 0
}

# Cambiar al directorio del proyecto
$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectPath

# Verificar si es un repositorio Git
if (-not (Test-Path ".git")) {
    Write-Host ""
    Write-Host "Error: No se encontró un repositorio Git" -ForegroundColor Red
    Write-Host "Ejecuta primero: git init" -ForegroundColor Yellow
    exit 1
}

# Configurar usuario de Git si no está configurado
Write-Host ""
Write-Host "Configurando usuario de Git..." -ForegroundColor Cyan

$gitUserName = git config user.name
if ([string]::IsNullOrWhiteSpace($gitUserName)) {
    $userName = Read-Host "Tu nombre completo"
    git config --global user.name $userName
    Write-Host "✓ Nombre configurado: $userName" -ForegroundColor Green
} else {
    Write-Host "✓ Nombre ya configurado: $gitUserName" -ForegroundColor Green
}

$gitUserEmail = git config user.email
if ([string]::IsNullOrWhiteSpace($gitUserEmail)) {
    $userEmail = Read-Host "Tu email de GitHub"
    git config --global user.email $userEmail
    Write-Host "✓ Email configurado: $userEmail" -ForegroundColor Green
} else {
    Write-Host "✓ Email ya configurado: $gitUserEmail" -ForegroundColor Green
}

# Verificar si ya existe el remote
Write-Host ""
Write-Host "Configurando remote..." -ForegroundColor Cyan

$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    Write-Host "Remote 'origin' ya existe: $existingRemote" -ForegroundColor Yellow
    $updateRemote = Read-Host "¿Deseas actualizarlo? (S/N)"
    if ($updateRemote -eq "S" -or $updateRemote -eq "s") {
        git remote set-url origin $repoUrl
        Write-Host "✓ Remote actualizado" -ForegroundColor Green
    }
} else {
    git remote add origin $repoUrl
    Write-Host "✓ Remote agregado" -ForegroundColor Green
}

# Cambiar a rama main
Write-Host ""
Write-Host "Configurando rama principal..." -ForegroundColor Cyan
git branch -M main
Write-Host "✓ Rama renombrada a 'main'" -ForegroundColor Green

# Hacer push
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host "  Subiendo código a GitHub..." -ForegroundColor Blue
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host ""
Write-Host "GitHub te pedirá autenticación..." -ForegroundColor Yellow
Write-Host "Usa tu Personal Access Token en lugar de contraseña" -ForegroundColor Yellow
Write-Host ""

$pushResult = git push -u origin main 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ¡Código subido exitosamente a GitHub!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "Tu repositorio está disponible en:" -ForegroundColor Cyan
    Write-Host "  https://github.com/$repoOwner/$repoName" -ForegroundColor White
    Write-Host ""
    Write-Host "Los usuarios podrán instalar VoziPOmni con:" -ForegroundColor Cyan
    Write-Host ''
    Write-Host '  curl -o install.sh -L "https://raw.githubusercontent.com/' -NoNewline -ForegroundColor White
    Write-Host "$repoOwner/$repoName" -NoNewline -ForegroundColor Yellow
    Write-Host '/main/install.sh" && chmod +x install.sh' -ForegroundColor White
    Write-Host "  export VOZIPOMNI_IPV4=X.X.X.X && ./install.sh" -ForegroundColor White
    Write-Host ""
    Write-Host "Próximos pasos:" -ForegroundColor Cyan
    Write-Host "  1. Ve a GitHub y verifica que todo se subió correctamente" -ForegroundColor White
    Write-Host "  2. Configura topics y descripción del repositorio" -ForegroundColor White
    Write-Host "  3. Crea un release (v1.0.0)" -ForegroundColor White
    Write-Host "  4. ¡Comparte tu proyecto!" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host "  Error al subir el código" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host ""
    
    if ($pushResult -match "remote: Repository not found") {
        Write-Host "El repositorio no existe en GitHub." -ForegroundColor Yellow
        Write-Host "Por favor:" -ForegroundColor Yellow
        Write-Host "  1. Ve a https://github.com/new" -ForegroundColor White
        Write-Host "  2. Crea un repositorio llamado '$repoName'" -ForegroundColor White
        Write-Host "  3. NO lo inicialices con README, .gitignore o LICENSE" -ForegroundColor White
        Write-Host "  4. Ejecuta este script nuevamente" -ForegroundColor White
    } elseif ($pushResult -match "Authentication failed") {
        Write-Host "Error de autenticación." -ForegroundColor Yellow
        Write-Host "Necesitas crear un Personal Access Token:" -ForegroundColor Yellow
        Write-Host "  1. Ve a https://github.com/settings/tokens" -ForegroundColor White
        Write-Host "  2. Generate new token (classic)" -ForegroundColor White
        Write-Host "  3. Marca los scopes: repo, workflow" -ForegroundColor White
        Write-Host "  4. Copia el token generado" -ForegroundColor White
        Write-Host "  5. Usa el token como contraseña cuando Git lo pida" -ForegroundColor White
    } else {
        Write-Host "Error desconocido:" -ForegroundColor Yellow
        Write-Host $pushResult -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Para más ayuda, consulta: GITHUB_SETUP.md" -ForegroundColor Cyan
    exit 1
}
