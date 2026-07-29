from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.auth.router import router as auth_router
from app.auth.service import bootstrap_admin
from app.config import get_settings
from app.database import _SessionFactory, dispose_engine
from app.middleware.cors import configure_cors
from app.middleware.rate_limit import limiter
from app.middleware.security import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Bootstrap admin user on startup
    async with _SessionFactory() as session:
        await bootstrap_admin(session)
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="OpenWaitlist API",
        version="0.1.0",
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        lifespan=lifespan,
    )

    # --- Rate limiter ---
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # --- CORS ---
    configure_cors(app)

    # --- Security headers ---
    app.add_middleware(SecurityHeadersMiddleware)

    # --- Routers ---
    app.include_router(auth_router)

    # --- Routes ---
    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app


app = create_app()
