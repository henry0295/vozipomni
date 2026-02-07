# Guía de Publicación en GitHub

## 📝 Estado Actual

✅ Repositorio Git inicializado
✅ Commit inicial realizado (88 archivos, 5269 líneas)
✅ Scripts de instalación listos
✅ Documentación completa

## 🚀 Paso 1: Crear Repositorio en GitHub

### Opción A: Desde la Web (Recomendado)

1. Ve a [GitHub](https://github.com) e inicia sesión
2. Haz clic en el botón **"+"** (arriba a la derecha) → **"New repository"**
3. Completa los datos:
   - **Repository name**: `vozipomni`
   - **Description**: `Sistema de Contact Center omnicanal con Django, React y Asterisk`
   - **Visibility**: Public o Private (según tu preferencia)
   - ⚠️ **NO marques** "Initialize this repository with a README" (ya lo tenemos)
   - ⚠️ **NO agregues** .gitignore ni LICENSE (ya los tenemos)
4. Haz clic en **"Create repository"**

### Opción B: Usando GitHub CLI (gh)

```bash
gh repo create vozipomni --public --description "Sistema de Contact Center omnicanal con Django, React y Asterisk" --source=. --remote=origin --push
```

## 🔗 Paso 2: Conectar con GitHub y Push

Después de crear el repositorio en GitHub, ejecuta estos comandos:

### Para GitHub personal:

```bash
cd "c:\Users\PT\OneDrive - VOZIP COLOMBIA\Documentos\GitHub\vozipomni"
git remote add origin https://github.com/henry0295/vozipomni.git
git branch -M main
git push -u origin main
```

### Para organización VOZIP:

```bash
cd "c:\Users\PT\OneDrive - VOZIP COLOMBIA\Documentos\GitHub\vozipomni"
git remote add origin https://github.com/VOZIP/vozipomni.git
git branch -M main
git push -u origin main
```

**Reemplaza `TU_USUARIO` o `VOZIP` con el nombre de usuario u organización correcto.**

## 🔐 Autenticación

Si es tu primera vez haciendo push, Git te pedirá autenticación:

### Método recomendado: Personal Access Token

1. Ve a GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click en "Generate new token (classic)"
3. Marca los scopes: `repo`, `workflow`
4. Copia el token generado
5. Cuando Git pida contraseña, usa el token (no tu contraseña de GitHub)

### Alternativa: GitHub CLI

```bash
gh auth login
```

Sigue las instrucciones en pantalla.

## ✅ Paso 3: Verificar

1. Ve a `https://github.com/TU_USUARIO/vozipomni`
2. Deberías ver todos los archivos del proyecto
3. Verifica que el README.md se muestre correctamente

## 🎯 Paso 4: Probar la Instalación estilo OmniLeads

Una vez el código esté en GitHub, cualquiera podrá instalar con:

```bash
curl -o install.sh -L "https://raw.githubusercontent.com/henry0295/vozipomni/main/install.sh" && chmod +x install.sh
export VOZIPOMNI_IPV4=X.X.X.X && ./install.sh
```

## 📋 Configuración Adicional Recomendada

### 1. Proteger la rama main

En GitHub: Settings → Branches → Add rule
- Branch name pattern: `main`
- ☑️ Require pull request reviews before merging
- ☑️ Require status checks to pass before merging

### 2. Agregar Topics al Repositorio

En la página principal del repo → ⚙️ (junto a About) → Topics:
- `contact-center`
- `django`
- `react`
- `asterisk`
- `voip`
- `webrtc`
- `call-center`
- `pbx`
- `acd`
- `ivr`

### 3. Crear Releases

```bash
git tag -a v1.0.0 -m "Primera versión estable de VoziPOmni"
git push origin v1.0.0
```

Luego en GitHub: Releases → Draft a new release

### 4. Habilitar GitHub Pages (Opcional)

Settings → Pages → Source: `main` branch → `/docs` folder

### 5. Agregar Badges al README

GitHub automáticamente mostrará algunos badges, pero puedes agregar más:

```markdown
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![Asterisk](https://img.shields.io/badge/asterisk-20.6.0-orange.svg)
```

## 🔄 Comandos Git Útiles

### Ver estado
```bash
git status
```

### Hacer cambios futuros
```bash
git add .
git commit -m "Descripción del cambio"
git push
```

### Actualizar desde GitHub
```bash
git pull
```

### Ver historial
```bash
git log --oneline
```

### Crear una nueva rama
```bash
git checkout -b feature/nueva-funcionalidad
```

## 📞 Soporte

Si tienes problemas:

1. Verifica que tengas Git instalado: `git --version`
2. Verifica tu configuración de Git:
   ```bash
   git config --global user.name "Tu Nombre"
   git config --global user.email "tu@email.com"
   ```
3. Revisa la documentación de GitHub: https://docs.github.com

## 🎉 ¡Listo!

Tu proyecto ahora está en GitHub y disponible para:
- ✅ Instalación con un solo comando (estilo OmniLeads)
- ✅ Colaboración con otros desarrolladores
- ✅ Control de versiones profesional
- ✅ CI/CD (GitHub Actions)
- ✅ Issues y Project Management
- ✅ Wiki y Documentación
