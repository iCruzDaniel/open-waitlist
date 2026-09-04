"""Vercel serverless entry point.

Wraps the FastAPI app for Vercel's Python runtime. Vercel injects the
environment via `app.main` imports, and because DATABASE_TYPE=redis uses
environment-driven connection (no local SQLite files), the same code works
in a serverless function.
"""

from app.main import app

# Vercel's Python runtime calls the exported `app` object directly as the
# WSGI/ASGI handler. FastAPI exposes an ASGI interface, so this is all that's
# needed.
handler = app
