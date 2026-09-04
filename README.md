<p align="center">
  <img src="docs/img/portada.png" alt="OpenWaitlist" width="100%">
</p>

<h1 align="center"><img src="docs/img/favicon0-rounded.png" width="45" height="45" style="vertical-align: middle;"> OpenWaitlist</h1>

<p align="center">
  <strong>Self-hosted waitlist & lead management for landing pages.</strong>
</p>

<p align="center">
  <a href="https://img.shields.io/badge/Python-3.12+-00D2B8?logo=python&logoColor=white"><img src="https://img.shields.io/badge/Python-3.12+-00D2B8?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://img.shields.io/badge/FastAPI-0.115-00D2B8?logo=fastapi&logoColor=white"><img src="https://img.shields.io/badge/FastAPI-0.115-00D2B8?logo=fastapi&logoColor=white" alt="FastAPI 0.115"></a>
  <a href="https://img.shields.io/badge/React-18-00D2B8?logo=react&logoColor=white"><img src="https://img.shields.io/badge/React-18-00D2B8?logo=react&logoColor=white" alt="React 18"></a>
  <a href="https://img.shields.io/github/license/iCruzDaniel/open-waitlist"><img src="https://img.shields.io/github/license/iCruzDaniel/open-waitlist" alt="License"></a>
  <a href="https://img.shields.io/docker/v/dcruz04/waitlistgo?color=00D2B8"><img src="https://img.shields.io/docker/v/dcruz04/waitlistgo?color=00D2B8" alt="Docker Version"></a>
  <a href="https://img.shields.io/docker/pulls/dcruz04/waitlistgo?color=00D2B8"><img src="https://img.shields.io/docker/pulls/dcruz04/waitlistgo?color=00D2B8" alt="Docker Pulls"></a>
  <a href="https://img.shields.io/github/actions/workflow/status/iCruzDaniel/open-waitlist/docker-publish.yml?color=00D2B8"><img src="https://img.shields.io/github/actions/workflow/status/iCruzDaniel/open-waitlist/docker-publish.yml?color=00D2B8" alt="CI Status"></a>
  <a href="https://img.shields.io/github/v/release/iCruzDaniel/open-waitlist?color=00D2B8"><img src="https://img.shields.io/github/v/release/iCruzDaniel/open-waitlist?color=00D2B8" alt="Release"></a>
  <a href="https://img.shields.io/badge/PRs-welcome-00D2B8"><img src="https://img.shields.io/badge/PRs-welcome-00D2B8" alt="PRs Welcome"></a>
</p>

---

## 🎯 Pruébalo en segundos (no hace falta configurar nada)

¿Quieres ver qué hace sin leer más? Deja que OpenWaitlist se muestre solo.

**Modo demo (1 minuto):** sirve un formulario de leads en `/` con un botón **🎲 Random** que rellena datos realistas en un clic. Captura leads → míralos crecer en el panel admin.

```bash
cp .env.demo .env          # config demo lista (Redis + modo demo + admin panel)
uv sync
uv run uvicorn app.main:app --reload
```

Abre **http://localhost:8000** → pulsa **🎲 Random → Join waitlist** un par de veces → entra en **http://localhost:8000/admin** y verás los leads que acabas de capturar. Listo. 🎉

> 🔥 **¿En Vercel?** OpenWaitlist corre sin servidor con Upstash Redis — sin disco, sin contenedor. Los pasos están en [Despliegue](#despliegue).

---

## 💡 ¿Qué resuelve?

Cada landing page tiene un formulario "único" de registro a una waitlist. Al final acabas con 15 formularios, 12 bases de datos y 0 visibilidad.

OpenWaitlist es un **único backend** que recibe los registros de todas tus landings hacia listas (waitlists) nombradas, y te da **un panel admin** para ver, gestionar y exportar esos leads.

**El patrón es simple y poderoso:**

- Metes datos a una lista **aunque no exista todavía**. `POST /waitlists/{slug}/entries` con `slug=launch-2025` crea la waitlist sobre la marcha y guarda el lead. Sin pre-registrar nada.
- **`entry.data` es JSON libre** — `email`, `name`, `referrer`, o lo que tu landing mande. Sin schema obligatorio, sin migraciones por formulario.
- **Todo lo que lee** (listar, exportar, CRUD) exige **JWT de admin**. Lo público solo es para escribir leads.

---

## 👤 ¿Para quién es?

| Quién | Por qué le sirve |
|-------|------------------|
| **Indie hackers / founders** | Capturan leads de varias landings en un panel único, sin renovar un SaaS cada mes. |
| **Equipos pequeños** | Un backend barato (o gratis en Vercel) para validar demanda antes de construir el producto. |
| **Agencias** | Multiplican landings por cliente y las centralizan en una sola API de leads con export a CSV. |
| **Quien valore privacidad** | Self-hosted, tus leads son tuyos: SQLite, Postgres o Upstash Redis, tú decides dónde viven. |

---

## 🛠️ ¿Por qué está construido así?

Los errores más caros en este tipo de sistema son los silenciosos: leads que se pierden, notificaciones que no salen, o un rate-limit que crees haber configurado y no hace nada. El diseño apunta directo a esos tres.

- **Almacenamiento intercambiable (un patrón `Store`).** Toda la lógica habla con una interfaz `Store`, no con SQLAlchemy directamente. `DATABASE_TYPE=sqlite|postgres|redis` elige la implementación en el arranque. Eso permite ir de **SQLite local → Postgres en un VPS → Upstash Redis en Vercel sin tocar servicios ni routers**.
- **Las notificaciones son background tasks.** Email y webhook se disparan en segundo plano: jamás añaden latencia al `POST /entries` ni rompen la respuesta al cliente si fallan.
- **Bot protection ≠ autenticación.** Cloudflare Turnstile verifica que hay un humano en el formulario público. El **JWT** protege el panel admin. Dos mecanismos, ninguno mezclado en el mismo endpoint.
- **Soft-delete, nunca DELETE físico.** Se desactiva (`is_active=false`), no se borra. Porque un "deshacer" o una migración que necesite el historial no deberían ser imposibles.
- **Rate limiting desde el día 1**, configurable por env var — no como "mejora futura".
- **Self-hosted real.** Docker multi-stage sin toolchains de build en la imagen final, usuario no-root, `/docs` y admin panel apagados por defecto.

---

## 🧰 Features

- **Waitlists auto-creadas.** POST a cualquier slug y la lista nace sola.
- **Datos libres.** `entry.data` es JSON arbitrario, sin schema forzado.
- **Turnstile + JWT.** Humano verificado para escribir, admin autenticado para leer.
- **Notificaciones en background.** Email (SMTP) y webhook, sin bloquear la respuesta.
- **Export CSV asíncrono con progreso en vivo.** Jobs en segundo plano con barra de progreso (SSE). CSV con BOM UTF-8, columnas aplanadas y sanitización anti inyección.
- **Rate limiting configurable** en entries y login.
- **Panel admin React 18 + TS + Tailwind + Vite** servido en `/admin` desde la misma imagen.
- **SQLite / Postgres / Redis listos.** Ahí es donde quieras correrlo.
- **Modo demo.** Formulario de captura listo en `/` con botón 🎲 Random.
- **Multi-stage Dockerfile**, seguridad por defecto, health check, robots.txt.

---

## 🐛 Evidencias: momentos de fallo y cómo se corrigieron

> Esta sección documenta bugs y decisiones reales del desarrollo. Es la prueba de que el diseño se endurece con el uso — y de que hay guardarraíles que detectan lo que el ojo no ve.

### 🔴 P0 — Las notificaciones no salían nunca (fallo silencioso)
`get_store()` es un **async generator**, y se llamaba como si fuera una función normal. El `TypeError` resultante se tragaba en el arranque de la background task → el webhook y el email **jamás se disparaban**, sin error visible para el cliente.
**El fix:** resolver el store con `await init_store()`.
**La lección:** un fallo que no rompe la respuesta del usuario es el más peligroso de todos: no lo oyes hasta que el producto "funciona" y no llega nada.

### 🔴 P0 — Entry a una waitlist "eliminada" crasheaba con 500
Un `POST /entries` a un slug soft-deleted lanzaba un `500` (`MissingGreenlet`) en lugar de reactivar la lista. La consulta no incluía listas inactivas, y la reactivación no refrescaba el objeto tras el commit.
**El fix:** buscar con `include_inactive=True` + `await session.refresh(obj)`.
**La lección:** el soft-delete tenía un caso borde que rompía justo el flujo que debía ser más resiliente (auto-create). Se cerró con test de regresión.

### 🟠 P1 — El rate limit por env var era config muerta
`RATE_LIMIT_ENTRIES` / `RATE_LIMIT_LOGIN` estaban definidas en la configuración, pero los decoradores **hardcodeaban** `"10/minute"` / `"5/minute"`. Un operador creía estar subiendo los límites y no hacía nada.
**El fix:** cablear `get_settings().rate_limit_*` en los decoradores.
**La lección:** una env var documentada que no se lee es peor que no tenerla — da falsa sensación de control.

### 🟠 Revertido: un cambio que proponía DELETE físico
Durante la revisión se detectó (antes de commitear) un cambio que eliminaba físicamente en vez de respetar el soft-delete. Se revirtió. Es un **guardarraíl del proceso de revisión**, no un bug de producción.

> **Estado de verificación:** la suite pasa **82 tests**, `ruff check` limpio y `ruff format --check` en los 64 archivos. Los dos P0 tienen test de regresión que los reactivaría si volvieran a introducirse.

---

## 🚀 Captura un lead (API)

Landing page embebiendo el widget de Turnstile, o en dev sin secretos:

```bash
curl -X POST http://localhost:8000/waitlists/launch-2025/entries \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "name": "Alice", "referrer": "twitter"}'
```

→ `201 Created` con el lead creado (y la waitlist, si no existía).

> ⚠️ Seguridad: solo `POST /entries` es público. **Todo lo que lee o exporta leads requiere JWT de admin** — Turnstile demuestra un humano, jamás autoriza a leer datos.

---

## 🧪 Pruébalo local

```bash
uv sync
cp .env.example .env        # o .env.demo para el modo demo
uv run alembic upgrade head # solo backends SQL; se omite con redis
uv run uvicorn app.main:app --reload
```

### Tests y lint

```bash
uv run pytest                  # 82 tests
uv run ruff check .            # lint
uv run ruff format .           # formato
```

---

## 🐳 Despliegue

### Docker (VPS)

```bash
# SQLite (lo más simple)
docker compose up -d

# PostgreSQL
docker compose --profile postgres up -d
```

### Redis + Vercel (sin servidor)

Serverless no tiene disco persistente, por eso en Vercel se usa **Upstash Redis**:

1. Crea una base en [Upstash](https://upstash.com).
2. Despliega en Vercel y pon estas env vars (usa `.env.demo` como plantilla):
   - `DATABASE_TYPE=redis`, `REDIS_URL`, `REDIS_TOKEN`
   - `DEMO_MODE=true` (formulario en `/`), `ADMIN_EMAIL`/`ADMIN_PASSWORD`/`JWT_SECRET`
3. El demo form vive en `/`, el panel admin en `/admin`.

> Nota: `EXPORT_DIR` escribe CSV a disco; en funciones serverless ese disco es efímero, así que el export es mejor en despliegues siempre-activos (Docker/VPS).

El repo trae `vercel.json` listo para el runtime Python de Vercel: el `installCommand` compila el panel admin y lo copia a `api/admin-dist` (dentro del árbol de la función serverless), y el app FastAPI (`app/main.py`) sirve `/admin` desde ahí (o desde `admin-panel/dist` en Docker). `api/main.py` queda como wrapper opcional para otros targets.

---

## ⚙️ Configuración

Todas las opciones van por env vars. Copia `.env.example` a `.env` y edítalas.

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_TYPE` | `sqlite` | `sqlite`, `postgres` o `redis` |
| `DATABASE_URL` | sqlite local | Cadena async de SQLAlchemy (SQL) |
| `REDIS_URL` / `REDIS_TOKEN` | — | URL + token Upstash (cuando `DATABASE_TYPE=redis`) |
| `REDIS_NAMESPACE_ORG` | `waitlistgo` | Prefijo de todas las claves Redis (aislamiento multi-tenant) |
| `DEMO_MODE` | `false` | Sirve el formulario demo en `/` con botón 🎲 Random |
| `DEMO_SLUG` | `demo` | Slug al que apunta el formulario demo |
| `DEMO_TITLE` | `Join the demo waitlist` | Título del formulario demo |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | — | Turnstile humano. Secret vacío = verificación desactivada (dev) |
| `JWT_SECRET` | `changeme-jwt-secret` | Firma de JWT del admin (mín 16 chars) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | — | Credenciales admin auto-creado |
| `ENABLE_ADMIN_PANEL` | `false` | Sirve el panel en `/admin` |
| `ENABLE_DOCS` | `false` | Habilita `/docs` y `/redoc` |
| `RATE_LIMIT_ENTRIES` | `10/minute` | Rate limit de `POST /entries` |
| `RATE_LIMIT_LOGIN` | `5/minute` | Rate limit de `POST /auth/login` |
| `SMTP_*` / `WEBHOOK_URL` | — | Notificaciones (email + webhook) |
| `MAX_REQUEST_BODY_SIZE` | `1048576` | Tope de body (1 MB) |
| `EXPORT_DIR` / `EXPORT_TTL_MINUTES` | `data/exports` / `60` | Jobs de export CSV |

Ver `.env.example` para la lista completa con comentarios.

---

## 🧱 Arquitectura

```
waitlistgo/
├── app/
│   ├── api/v1/           # Routers (sin lógica de negocio)
│   ├── auth/             # Turnstile + JWT
│   ├── repositories/     # Capa de almacenamiento (SQL o Redis)
│   │   ├── models.py     #   DTOs de dominio
│   │   ├── protocols.py  #   Interfaz Store/repo
│   │   ├── sql/          #   SQLite/Postgres
│   │   └── redis/        #   Upstash Redis
│   ├── dependencies.py   # init_store() por DATABASE_TYPE
│   ├── middleware/       # CORS, rate limit, headers, body size
│   ├── models/           # Modelos SQLAlchemy (backend SQL)
│   ├── schemas/          # Pydantic v2
│   ├── services/         # Lógica de negocio
│   └── main.py           # App factory
├── api/main.py           # Handler serverless (Vercel)
├── vercel.json
├── admin-panel/          # React + Vite
├── alembic/              # Migraciones (solo backends SQL)
├── tests/
├── Dockerfile            # Multi-stage
├── docker-compose*.yml
└── .env.example
```

---

## 📜 Licencia

[MIT](LICENSE)
