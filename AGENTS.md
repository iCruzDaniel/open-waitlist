# AGENTS.md — Microservicio Waitlist / Leads API

Este archivo va en la raíz del repo. Contiene el contexto operativo del proyecto para el agente.
La especificación completa está en `PLAN_microservicio_waitlist.md` (léelo antes de empezar si no lo has hecho) — este archivo es el resumen accionable para trabajar día a día.

## Qué se está construyendo
Microservicio FastAPI (gestionado con UV) que recibe registros de formularios de landing pages hacia "waitlists" (listas nombradas), con panel admin opcional en React+TS, desplegado con Docker Compose. SQLite por defecto, Postgres opcional.

## Comandos

**Backend**
```bash
uv sync                                   # instalar/actualizar dependencias
uv run uvicorn app.main:app --reload      # servidor dev
uv run pytest                             # tests
uv run pytest --cov=app                   # tests con cobertura
uv run ruff check .                       # lint
uv run ruff format .                      # formato
uv run alembic revision --autogenerate -m "mensaje"
uv run alembic upgrade head
```

**Panel admin** (dentro de `admin-panel/`)
```bash
npm ci
npm run dev
npm run build
```

**Docker — desarrollo**
```bash
docker compose -f docker-compose.dev.yml up -d --build              # SQLite
docker compose -f docker-compose.dev.yml --profile postgres up -d --build   # con Postgres
docker compose -f docker-compose.dev.yml logs -f api
```

**Docker — producción (VPS)**
```bash
docker compose up -d                          # SQLite (usa imagen de DockerHub)
docker compose --profile postgres up -d       # con Postgres
```

## Reglas no negociables (no desviarse del plan sin avisar)

- Dockerfile **multi-stage** obligatorio; la imagen final no debe contener compiladores ni `node_modules`/toolchain de build, solo el `.venv` y los estáticos ya compilados del panel.
- `DATABASE_TYPE=sqlite|postgres` en `.env` decide el motor. Postgres vive en un **profile** de compose, nunca en `depends_on` duro — la app debe reintentar la conexión con backoff al arrancar (`tenacity`), no depender del orden de arranque de contenedores.
- Auth: **Cloudflare Turnstile** (site key + secret key) para el endpoint público de entradas — verificación de humanidad, no autenticación. **JWT** solo para el panel admin. No mezclar los dos mecanismos en un mismo endpoint salvo que el plan lo indique.
- La entrada (`entry.data`) es **JSON libre, sin schema fijo**. No forzar campos obligatorios como `email` a nivel de Pydantic salvo validación mínima de tamaño/tipo.
- `addtowaitlist` (`POST /waitlists/{slug}/entries`) **auto-crea** la waitlist si el slug no existe. No debe fallar por "waitlist no encontrada".
- Waitlists se **soft-delete** (`is_active=false` / `deleted_at`), nunca DELETE físico.
- Notificaciones (email + webhook) **siempre** como background task — jamás deben añadir latencia a la respuesta del `POST /entries`, y su fallo nunca debe romper la respuesta al cliente.
- Rate limiting obligatorio en `POST /entries` y `POST /auth/login` desde el principio, no como "mejora futura".
- `/docs` y `/redoc` apagados por defecto (`ENABLE_DOCS=false`).
- Panel admin apagado por defecto (`ENABLE_ADMIN_PANEL=false`); cuando esté activo se sirve montado en `/admin` desde la misma imagen, sin contenedor nginx separado.
- Nunca loguear secrets (Turnstile secret, contraseñas, JWT completos) ni el contenido crudo de secretos.
- Contenedor corre con usuario no-root.

## Convenciones de código

- Python: type hints en todo, `async def` en toda la capa de I/O (DB, HTTP, SMTP), Pydantic v2 para request/response, `ruff` como único formateador/linter.
- Nombres de variables/funciones/commits en inglés; los mensajes de cara al usuario (si los hay) pueden ir en español.
- Un servicio (`services/`) por responsabilidad de negocio; los routers (`api/v1/`) no deben tener lógica de negocio, solo orquestar.
- Cada fase cierra con: tests en verde + `ruff check` limpio + resumen breve de qué se hizo.

## Flujo de trabajo

Avanzar **una fase a la vez**, en el orden de la sección 14 del plan. Al cerrar una fase:
1. `uv run pytest` y `uv run ruff check .` deben pasar.
2. Resumir en 3-4 líneas qué se implementó y qué queda pendiente para la siguiente fase.
3. Marcar el checklist de esta sección y continuar con la siguiente fase.

### Checklist de fases (ver detalle de cada una en el plan, sección 14)

- [ ] Fase 0 — Setup del proyecto ⟵ **empezar aquí**
- [ ] Fase 1 — Core (config, DB, modelos, Alembic)
- [ ] Fase 2 — App base (`main.py`, `/health`, middleware)
- [ ] Fase 3 — Auth (Turnstile, JWT, bootstrap admin)
- [ ] Fase 4 — CRUD Waitlists
- [ ] Fase 5 — addtowaitlist
- [ ] Fase 6 — readwaitlist + export CSV
- [ ] Fase 7 — Notificaciones (email + webhook)
- [ ] Fase 8 — Hardening de seguridad
- [ ] Fase 9 — Tests
- [ ] Fase 10 — Dockerfile + docker-compose
- [ ] Fase 11 — Panel admin (React + TS)
- [ ] Fase 12 — Integración panel + Docker
- [ ] Fase 13 — Documentación (README)
- [ ] Fase 14 — Checklist final de seguridad y rendimiento

## Tareas concretas — Fase 0 (arrancar ahora)

- [ ] `uv init` y `pyproject.toml` con las dependencias listadas en la sección 2 del plan (backend; el panel usa su propio `package.json` en `admin-panel/`)
- [ ] Crear la estructura de carpetas de la sección 3 del plan
- [ ] `.env.example` completo según la sección 10 del plan
- [ ] `.gitignore` (incluir al menos: `.venv/`, `.env`, `__pycache__/`, `data/`, `admin-panel/node_modules/`, `admin-panel/dist/`)
- [ ] `README.md` esqueleto (se completa en Fase 13)
- [ ] Primer commit: "chore: project scaffold"

## Puntos abiertos (preguntar al usuario si se llega a ese punto sin resolver)

1. Email de notificación: ¿solo aviso interno al equipo, o también confirmación automática al lead? Afecta a la Fase 7.
2. Deduplicación de entradas repetidas en una misma waitlist: no implementado en el MVP, requiere definir una convención de campo si se quiere añadir.
3. Turnstile (resuelto): verificación desactivable — `.env` sin `TURNSTILE_SECRET_KEY` = dev mode sin verificación; con secret, fail-closed (503) si Cloudflare no responde.
4. Reverse proxy / HTTPS en el VPS: fuera de este repo, documentar como paso posterior (Caddy recomendado).
