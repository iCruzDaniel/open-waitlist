import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.docs import OpenWaitlistAPI, install_docs
from app.api.v1.entries import router as entries_router
from app.api.v1.exports import router as exports_router
from app.api.v1.waitlists import router as waitlists_router
from app.auth.router import router as auth_router
from app.auth.service import bootstrap_admin
from app.config import get_settings
from app.database import _SessionFactory, dispose_engine, wait_for_db
from app.middleware.cors import configure_cors
from app.middleware.rate_limit import limiter
from app.middleware.security import (
    RequestBodySizeMiddleware,
    SecurityHeadersMiddleware,
    SensitiveDataFilter,
)
from app.services.export import ExportJobManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await wait_for_db()
    async with _SessionFactory() as session:
        await bootstrap_admin(session)
    settings = get_settings()
    app.state.export_manager = ExportJobManager(
        export_dir=Path(settings.export_dir),
        ttl_minutes=settings.export_ttl_minutes,
        session_factory=_SessionFactory,
    )
    app.state.export_manager.export_dir.mkdir(parents=True, exist_ok=True)
    await app.state.export_manager._sweep()
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()

    app = OpenWaitlistAPI(
        title="OpenWaitlist API",
        version="0.1.0",
        # Docs are registered via install_docs() with local, CSP-compatible
        # assets — FastAPI's defaults load them from CDNs.
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # --- Logging: redact sensitive data ---
    if settings.log_sensitive_redact:
        root_logger = logging.getLogger()
        root_logger.addFilter(SensitiveDataFilter())

    # --- Rate limiter ---
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # --- Admin panel (optional) ---
    if settings.enable_admin_panel:
        admin_dist = Path(__file__).resolve().parent.parent / "admin-panel" / "dist"
        if admin_dist.is_dir():
            app.mount("/admin", StaticFiles(directory=str(admin_dist), html=True), name="admin")
        else:
            logger.warning(
                "Admin panel enabled but dist/ not found — run 'npm run build' in admin-panel/",
            )

    # --- Docs (local Swagger UI / ReDoc assets, CSP-compatible) ---
    if settings.enable_docs:
        install_docs(app)

    # --- Request body size limit ---
    app.add_middleware(RequestBodySizeMiddleware, max_bytes=settings.max_request_body_size)

    # --- CORS ---
    configure_cors(app)

    # --- Security headers ---
    app.add_middleware(SecurityHeadersMiddleware)

    # --- Routers ---
    app.include_router(auth_router)
    app.include_router(waitlists_router)
    app.include_router(entries_router)
    app.include_router(exports_router)

    # --- Routes ---
    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/robots.txt", include_in_schema=False)
    async def robots() -> PlainTextResponse:
        return PlainTextResponse("User-agent: *\nDisallow: /admin/\n")

    return app


app = create_app()
