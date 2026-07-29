# OpenWaitlist

Microservicio FastAPI para gestión de waitlists y leads. Recibe registros de formularios de landing pages, los organiza en listas nombradas y dispara notificaciones. Incluye panel admin opcional en React.

## Stack

| Capa | Tecnología |
|---|---|
| **Backend** | Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| **Panel admin** | React 18 + TypeScript + Tailwind + Vite |
| **Base de datos** | SQLite (desarrollo) / PostgreSQL (producción) |
| **Infra** | Docker Compose, multi-stage Dockerfile |

## Requisitos

- Python 3.12+ y [uv](https://docs.astral.sh/uv/) (para desarrollo local)
- Docker + Docker Compose (para despliegue)
- Node.js 20+ (solo si modificas el panel admin)

## Inicio rápido (desarrollo local)

```bash
# 1. Clonar y entrar
git clone <repo> && cd waitlistgo

# 2. Crear entorno virtual e instalar dependencias
uv sync

# 3. Copiar variables de entorno
cp .env.example .env

# 4. Ejecutar migraciones de base de datos
uv run alembic upgrade head

# 5. Iniciar servidor de desarrollo
uv run uvicorn app.main:app --reload
```

Servidor en `http://localhost:8000`.

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/waitlist.db` | Conexión a base de datos |
| `DATABASE_TYPE` | `sqlite` | `sqlite` o `postgres` |
| `API_KEY` | `dev-api-key-change-me` | API Key para endpoints públicos |
| `JWT_SECRET_KEY` | *(autogenerado)* | Secreto para firmar JWT del panel admin |
| `JWT_ALGORITHM` | `HS256` | Algoritmo JWT |
| `JWT_EXPIRE_MINUTES` | `60` | Expiración del token admin |
| `ADMIN_EMAIL` | `admin@example.com` | Email del admin por defecto |
| `ADMIN_PASSWORD` | `changeme-admin-password` | Password del admin por defecto |
| `ENABLE_DOCS` | `false` | Activar `/docs` y `/redoc` |
| `ENABLE_ADMIN_PANEL` | `false` | Montar panel admin en `/admin` |
| `SMTP_HOST` | — | Host SMTP para notificaciones |
| `SMTP_PORT` | `587` | Puerto SMTP |
| `SMTP_USER` | — | Usuario SMTP |
| `SMTP_PASSWORD` | — | Contraseña SMTP |
| `SMTP_FROM` | — | Remitente de correos |
| `NOTIFY_WEBHOOK_URL` | — | URL de webhook para notificaciones |
| `RATE_LIMIT_PER_MINUTE` | `60` | Límite de requests por minuto en `/entries` |
| `ADMIN_RATE_LIMIT_PER_MINUTE` | `30` | Límite de requests por minuto en `/auth/login` |

Ver `.env.example` para valores completos.

## Uso de la API

### Endpoints públicos (requieren `X-API-Key`)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/waitlists/{slug}/entries` | Agregar lead a una waitlist (la auto-crea si no existe) |
| `GET` | `/waitlists/{slug}/entries` | Listar entries (paginado) |
| `GET` | `/waitlists/{slug}/entries/export` | Exportar entries como CSV |

### Endpoints admin (requieren JWT — para el panel admin)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/auth/login` | Iniciar sesión (email + password → JWT + API Key) |
| `GET` | `/auth/me` | Información del admin autenticado |
| `GET` | `/waitlists` | Listar todas las waitlists |
| `POST` | `/waitlists` | Crear waitlist |
| `GET` | `/waitlists/{slug}` | Obtener waitlist por slug |
| `PATCH` | `/waitlists/{slug}` | Actualizar waitlist |
| `DELETE` | `/waitlists/{slug}` | Soft-delete de waitlist |

### Health check

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### Agregar un lead

```bash
curl -X POST http://localhost:8000/waitlists/launch-2025/entries \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-change-me" \
  -d '{"email": "user@example.com", "name": "Juan", "referrer": "twitter"}'
```

## Docker Compose

### SQLite (default)

```bash
docker compose up -d --build
```

### PostgreSQL

```bash
docker compose --profile postgres up -d --build
```

Requiere `DATABASE_TYPE=postgres` y `DATABASE_URL=postgresql+asyncpg://...` en `.env`.

### Logs

```bash
docker compose logs -f api
```

## Panel admin

El panel admin se sirve desde la misma imagen de Docker montado en `/admin`.

### Desarrollo local del panel

```bash
cd admin-panel
npm install
npm run dev        # servidor de desarrollo en :5173
npm run build      # compilar para producción
```

El panel requiere `ENABLE_ADMIN_PANEL=true`. Las rutas son:

- `/admin/login` — Inicio de sesión
- `/admin/dashboard` — Gestión de waitlists (CRUD)
- `/admin/waitlist/{slug}` — Detalle de waitlist (entries + export CSV)

## Migraciones (Alembic)

```bash
uv run alembic revision --autogenerate -m "descripcion"
uv run alembic upgrade head
uv run alembic downgrade -1
```

## Tests

```bash
uv run pytest                  # todos
uv run pytest -v              # verbose
uv run pytest --cov=app       # con cobertura
```

## Linting

```bash
uv run ruff check .           # lint
uv run ruff format .          # formatear
```

## Arquitectura

```
waitlistgo/
├── app/
│   ├── api/v1/           # Routers (sin lógica de negocio)
│   │   ├── auth.py       #   Login JWT, /me
│   │   ├── health.py     #   Health check
│   │   ├── waitlists.py  #   CRUD waitlists
│   │   └── entries.py    #   addtowaitlist, list, export
│   ├── auth/             # Auth logic (API Key, JWT)
│   ├── core/             # Config, logging, middleware
│   ├── db/               # DB engine, session, Base
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic v2 schemas
│   ├── services/         # Business logic (notifications, etc.)
│   └── main.py           # FastAPI app
├── admin-panel/          # React + Vite admin panel
├── alembic/              # Migrations
├── tests/                # Tests con pytest-asyncio
├── Dockerfile            # Multi-stage (Node build + Python)
├── docker-compose.yml    # SQLite y Postgres profiles
└── .env.example          # Variables de entorno
```

## Notificaciones

Configura `SMTP_*` para email y/o `NOTIFY_WEBHOOK_URL` para webhooks. Las notificaciones se disparan como background task al crear un entry — nunca afectan la latencia de respuesta ni rompen el flujo si fallan.

## Licencia

MIT
