"""Self-hosted Swagger UI / ReDoc pages.

FastAPI's default ``/docs`` and ``/redoc`` pages load their assets from public
CDNs and Swagger UI runs an inline initializer script. Both violate the strict
Content-Security-Policy set by :class:`app.middleware.security.SecurityHeadersMiddleware`
(``script-src 'self'``), so we serve the assets from ``app/static/`` and
initialize Swagger UI from an external script instead.

Pinned asset versions (vendored under ``app/static/``):

- swagger-ui-dist 5.32.12
- redoc 2.5.3

The vendored ``redoc.standalone.js`` has one local patch: ReDoc's "Redocly"
header badge hardcodes ``https://cdn.redoc.ly/redoc/logo-mini.svg``, which the
strict CSP blocks; the URL literal is replaced with the local favicon. Re-apply
the patch when upgrading the bundle.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

SWAGGER_JS_URL = "/static/swagger-ui/swagger-ui-bundle.js"
SWAGGER_PRESET_URL = "/static/swagger-ui/swagger-ui-standalone-preset.js"
SWAGGER_CSS_URL = "/static/swagger-ui/swagger-ui.css"
SWAGGER_FAVICON_URL = "/static/swagger-ui/favicon.png"
SWAGGER_INIT_URL = "/static/swagger-ui/swagger-init.js"
REDOC_JS_URL = "/static/redoc/redoc.standalone.js"

SWAGGER_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - Swagger UI</title>
<link rel="stylesheet" href="{css_url}">
<link rel="icon" href="{favicon_url}">
</head>
<body>
<div id="swagger-ui"></div>
<script src="{js_url}"></script>
<script src="{preset_url}"></script>
<script src="{init_url}"></script>
</body>
</html>"""

REDOC_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - ReDoc</title>
</head>
<body>
<redoc spec-url="{openapi_url}"></redoc>
<script src="{redoc_js_url}"></script>
</body>
</html>"""


class OpenWaitlistAPI(FastAPI):
    """FastAPI subclass that injects a local logo into the OpenAPI schema.

    ReDoc renders the default redoc.ly logo image otherwise, which the strict
    ``img-src 'self' data:`` CSP blocks. Pointing ``info["x-logo"]`` at a
    locally served favicon keeps ReDoc's header self-hosted.
    """

    def openapi(self) -> dict:
        schema = super().openapi()
        info = schema.setdefault("info", {})
        info.pop("logo", None)  # ReDoc rejects info.logo outside patch mode
        info.setdefault("x-logo", {"url": SWAGGER_FAVICON_URL})
        return schema


def install_docs(app: FastAPI) -> None:
    """Mount the local docs assets and register ``/docs`` and ``/redoc``.

    Call only when ``settings.enable_docs`` is true. The FastAPI app must be
    created with ``docs_url=None`` / ``redoc_url=None`` so the default CDN-based
    pages are replaced instead of conflicting with these routes.
    """
    if not STATIC_DIR.is_dir():
        raise RuntimeError(
            "Docs are enabled but the static assets are missing in "
            "app/static/ (swagger-ui-dist and redoc bundles). "
            "Restore them and rebuild the image."
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui_html() -> HTMLResponse:
        return HTMLResponse(
            SWAGGER_HTML_TEMPLATE.format(
                title=app.title,
                css_url=SWAGGER_CSS_URL,
                favicon_url=SWAGGER_FAVICON_URL,
                js_url=SWAGGER_JS_URL,
                preset_url=SWAGGER_PRESET_URL,
                init_url=SWAGGER_INIT_URL,
            )
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html() -> HTMLResponse:
        return HTMLResponse(
            REDOC_HTML_TEMPLATE.format(
                title=app.title,
                openapi_url=app.openapi_url,
                redoc_js_url=REDOC_JS_URL,
            )
        )
