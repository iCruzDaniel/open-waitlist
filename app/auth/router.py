from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, verify_access_token
from app.auth.schemas import AdminRead, LoginRequest, TokenResponse
from app.auth.service import authenticate_admin
from app.config import get_settings
from app.database import get_session
from app.middleware.rate_limit import limiter
from app.models.admin import Admin

router = APIRouter(prefix="/auth", tags=["auth"])
_security = HTTPBearer(auto_error=False)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,  # noqa: ARG001  — used by slowapi limiter
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    admin = await authenticate_admin(session, payload.email, payload.password)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(str(admin.id))
    return TokenResponse(access_token=token, api_key=get_settings().api_key)


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Admin:
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
    result = await session.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
        )
    return admin


@router.get("/me", response_model=AdminRead)
async def me(
    admin: Admin = Depends(require_admin),  # noqa: B008
) -> Admin:
    return admin
