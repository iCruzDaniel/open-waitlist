from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


def configure_cors(app: FastAPI) -> None:
    settings = get_settings()

    if settings.cors_origins == "*":
        origins = ["*"]
        credentials = False
    else:
        origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
        credentials = True

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
        ],
    )
