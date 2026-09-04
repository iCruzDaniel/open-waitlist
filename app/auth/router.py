from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import create_access_token, verify_access_token
from app.auth.schemas import AdminRead, LoginRequest, TokenResponse
from app.auth.service import authenticate_admin, get_admin_by_id
from app.config import get_settings
from app.dependencies import StoreDep
from app.middleware.rate_limit import limiter
from app.repositories.models import AdminData

router = APIRouter(prefix="/auth", tags=["auth"])
_security = HTTPBearer(auto_error=False)

_RATE_LIMIT_LOGIN = get_settings().rate_limit_login


@router.post("/login", response_model=TokenResponse)
@limiter.limit(_RATE_LIMIT_LOGIN)
async def login(
    request: Request,  # noqa: ARG001  — used by slowapi limiter
    payload: LoginRequest,
    store: StoreDep,
) -> TokenResponse:
    admin = await authenticate_admin(store, payload.email, payload.password)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(str(admin.id))
    return TokenResponse(access_token=token)


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),  # noqa: B008
    store: StoreDep = None,  # type: ignore[assignment]
) -> AdminData:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )
    admin_id_str = verify_access_token(credentials.credentials)
    if admin_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    try:
        admin_id = int(admin_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from None
    admin = await get_admin_by_id(store, admin_id)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
        )
    return admin


@router.get("/me", response_model=AdminRead)
async def me(
    admin: AdminData = Depends(require_admin),  # noqa: B008
) -> AdminData:
    return admin
