# Pruebas y CI

Este documento reúne lo que existe hoy en VozipCX para verificar cambios: las pruebas del backend y su configuración de pytest, la prueba de carga con k6, el flujo de integración continua en `.github/workflows/ci.yml`, cómo ejecutar cada verificación en local y qué problemas se detectaron al leer esos archivos. Termina con sugerencias para ampliar la cobertura. No se ejecutó la suite durante la redacción; lo que se afirma sale de leer el código y la configuración.

## Qué hay

| Ubicación | Contenido | Pruebas |
|---|---|---|
| `backend/apps/agents/tests/test_models.py` | Modelo `Agent` | 11 |
| `backend/apps/campaigns/tests/test_models.py` | Modelo `Campaign` | 9 |
| `backend/apps/campaigns/tests/test_api.py` | Endpoints de campañas con `APIClient` y `force_authenticate` | 8 |
| `backend/apps/campaigns/tests/test_tasks.py` | Tareas de campañas | 4 |
| `backend/apps/contacts/tests/test_models.py` | Modelos de contactos | 10 |
| `backend/core/tests/` | `base.py`, `conftest.py`, `factories.py` (factory-boy), `helpers.py` | Utilidades, sin `test_*.py` |
| `tests/load/api-smoke.js` | k6 contra `/api/health/` | Carga |

No hay pruebas de telefonía (generadores de dialplan, listener AMI, `security.py`, `webrtc_views.py`), de consumers de Channels, de mensajería ni del marcador. El frontend no tiene pruebas ni script `test` en `package.json`.

Las pruebas existentes usan `django.test.TestCase`, que pytest-django ejecuta sin cambios.

## Configuración de pytest

`backend/pytest.ini`:

- `DJANGO_SETTINGS_MODULE = config.settings`, `pythonpath = .`, `testpaths = apps core`, archivos `test_*.py` y `*_test.py`.
- `addopts`: `-v -ra -l --strict-markers --strict-config`, cobertura de `apps` y `core` con reportes HTML, terminal y XML, `--cov-fail-under=80`, `--reuse-db`, `-n auto` (pytest-xdist) y `--durations=10`.
- Marcadores declarados: `unit`, `integration`, `slow`, `websocket`, `celery`, `ami`, `api`, `model`, `performance`, `property`. Con `--strict-markers`, cualquier otro marcador hace fallar la recolección.
- `asyncio_mode = auto`, `minversion = 3.11`, `timeout = 300`.

Dependencias de prueba en `backend/requirements/dev.txt` (versiones fijas): pytest 7.4.4, pytest-django 4.7.0, pytest-cov 4.1.0, pytest-mock 3.12.0, pytest-asyncio 0.23.3, pytest-xdist 3.5.0, factory-boy 3.3.0 y Faker 22.0.0.

## Ejecutar en local

Backend, con PostgreSQL y Redis disponibles (ver [Entorno local](./entorno-local.md)):

```powershell
cd backend
pip install -r requirements/dev.txt
$env:DEBUG = "True"
pytest                                   # configuración completa de pytest.ini
pytest apps/campaigns -p no:cacheprovider -o addopts="" -v    # sin cobertura ni xdist
pytest -m model -o addopts=""            # solo un marcador
```

Dentro del contenedor de desarrollo la imagen instala `requirements/prod.txt`, que no trae pytest; instálelo antes:

```powershell
docker compose exec backend pip install -r requirements/dev.txt
docker compose exec backend pytest -o addopts="" -v
```

Frontend:

```powershell
cd frontend
npm install
npm run lint
npx vue-tsc --noEmit
npm run build
```

Prueba de carga (requiere k6 instalado):

```powershell
k6 run -e BASE_URL=https://<servidor> -e VUS=10 -e DURATION=1m tests/load/api-smoke.js
```

Los umbrales del script son `http_req_failed < 1 %` y `p(95) < 500 ms` sobre `/api/health/`. No lo apunte a producción sin avisar.

Verificaciones de calidad que corre la CI:

```powershell
cd backend
pip install ruff bandit
python manage.py check --deploy
ruff check .
bandit -r apps core config -q
```

## Flujo de CI

`.github/workflows/ci.yml` se ejecuta en cada `pull_request` y en `push` a `main`, con `permissions: contents: read`. Tiene cuatro trabajos:

| Trabajo | Qué hace |
|---|---|
| `backend` | Servicios `postgres:14-alpine` y `redis:7-alpine`; Python 3.11; `pip install -r requirements.txt ruff bandit`; `manage.py check --deploy`; `ruff check .`; `bandit -r apps core config -q`; `pytest -q` |
| `frontend` | Node 20; `npm install`; `npm run lint`; `npx vue-tsc --noEmit`; `npm run build` |
| `security` | `gitleaks/gitleaks-action@v2` sobre todo el historial (`fetch-depth: 0`) y `aquasecurity/trivy-action@0.28.0` en modo `fs` con severidad `CRITICAL,HIGH` |
| `compose` | `docker compose -f docker-compose.prod.yml config --quiet` con valores ficticios en todas las variables obligatorias |

El trabajo `backend` corre con `DEBUG='False'` y valores de prueba para `SECRET_KEY` y `FIELD_ENCRYPTION_KEY`, de modo que ejercita las validaciones de arranque de producción de `settings.py`.

## Problemas detectados al leer la configuración

Estos puntos salen de la lectura de los archivos; confírmelos con la pestaña Actions del repositorio antes de corregir.

1. `backend` instala `requirements.txt`, que solo incluye `requirements/base.txt`. pytest, pytest-django, pytest-cov y pytest-xdist están en `dev.txt`, así que el paso `pytest -q` no tendría el comando ni los plugins que `pytest.ini` exige (`--cov`, `-n auto`).
2. `pytest.ini` declara `timeout = 300`, que es una opción de pytest-timeout. Ese paquete no está en `dev.txt` y, con `--strict-config`, pytest trata una opción desconocida como error.
3. `--cov-fail-under=80` hará fallar la corrida con la cobertura actual (solo hay pruebas en tres apps).
4. `apps/campaigns/tests/test_tasks.py` parchea `apps.campaigns.tasks.DialerService`, que no existe en `tasks.py`, y espera `'Processed'` en el resultado, mientras la tarea devuelve `"Verificadas N campañas activas, ..."`. Esas pruebas están desactualizadas respecto del código.
5. En el trabajo `frontend`, las líneas `cache: npm` y `- run: npm install` tienen una indentación que no corresponde al bloque `with:`; a simple vista el YAML no es válido y podría invalidar todo el workflow. No se pudo validar con un parser en la máquina de redacción.
6. `setup-node` con `cache: npm` necesita un `package-lock.json`, y `frontend/` no tiene uno versionado.
7. `vue-tsc` no está en `devDependencies`; `npx` descarga la versión más reciente en cada corrida.
8. El trabajo `backend` usa `cache-dependency-path: backend/requirements.txt`, que no cambia cuando cambian `base.txt` o `dev.txt`.

## Sugerencias

Para que la CI sea útil de nuevo:

- Instalar `requirements/dev.txt` en el trabajo `backend` y agregar `pytest-timeout` con versión fija, o quitar `timeout` de `pytest.ini`.
- Bajar `--cov-fail-under` a la cobertura real y subirlo de forma gradual, o moverlo a un trabajo aparte.
- Actualizar o eliminar `test_tasks.py` para que refleje `process_pending_calls` actual (claves de Redis y `queue_campaign_in_dialer`).
- Corregir la indentación del trabajo `frontend`, versionar `package-lock.json`, usar `npm ci` y agregar `vue-tsc` a `devDependencies`.
- Apuntar `cache-dependency-path` a `backend/requirements/*.txt`.

Pruebas que más valor aportan, por riesgo:

| Área | Qué probar | Cómo |
|---|---|---|
| `apps/telephony/security.py` | `outbound_policy_dialplan()` genera los `GotoIf` esperados para cada campo de la política; `policy_payload()` | Unitarias sobre el texto generado, marcador `unit` |
| `apps/telephony/asterisk_config.py` | Rutas salientes con prefijo `_`, `GoSub` antifraude, `${UNIQUEID}` en todos los `MixMonitor` | Unitarias con modelos de prueba (factories) |
| `apps/telephony/webrtc_views.py` | Ticket válido, vencido, de usuario inactivo; formato de credencial TURN | `APIClient` + `override_settings` |
| `apps/telephony/ami_cdr_listener.py` | `_determine_direction`, `_map_disposition`, `_process_cdr_event` con un diccionario de evento | Unitarias sin socket, marcador `ami` |
| `apps/recordings/tasks.py` | `_id_in_name` con uniqueids que comparten prefijo | Unitarias |
| `core/permissions.py` | Cada clase contra cada rol y método | Parametrizadas |
| Consumers | Cierre 4401/4403 y grupos | `channels.testing.WebsocketCommunicator` (ya importado en `core/tests/conftest.py`), marcador `websocket` |
| `dialer_engine/dialer.py` | `_number_reason` y `calculate_predictive_ratio` | Unitarias puras (no requieren Redis ni AMI) |
| Frontend | `utils/navigation.ts` (`canAccessRoute`, `homeForRole`) y `useHttp.errorMessage` | Vitest, si el equipo decide agregarlo |

Los fixtures de `core/tests/conftest.py` no llegan a `apps/*/tests` porque pytest aplica un `conftest.py` solo a su carpeta y subcarpetas. Si quiere reutilizarlos, muévalos a `backend/conftest.py`.

Para cambios de telefonía, además de las pruebas automáticas haga una prueba manual de llamada saliente, entrante a cola y transferencia, siguiendo [Depuración VoIP](../operacion/depuracion-voip.md).

## Ver también

- [Arquitectura](../general/arquitectura.md)
- [Glosario](../general/glosario.md)
- [Variables de entorno](../instalacion/variables-entorno.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
- [API](../api/README.md)
- [Entorno local](./entorno-local.md)
- [Estructura del código](./estructura-del-codigo.md)
- [Backend](./backend.md)
- [Frontend](./frontend.md)
- [Telefonía interna](./telefonia-interna.md)
- [Marcador](./marcador.md)
- [Contribuir](./contribuir.md)
