from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Database
from app.models import AdminUser, AppAuthorization
from app.security import token_matches, token_prefix

bearer = HTTPBearer(auto_error=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    database: Database = request.app.state.database
    yield from database.session()


def get_authorization(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> AppAuthorization:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_bearer_token")
    raw_token = credentials.credentials.strip()
    if len(raw_token) < 24:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_access_token")
    authorization = db.scalar(
        select(AppAuthorization).where(AppAuthorization.token_prefix == token_prefix(raw_token))
    )
    if authorization is None or not token_matches(authorization.access_token_hash, raw_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_access_token")
    return authorization


def require_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    admin_id = request.session.get("admin_id") if hasattr(request, "session") else None
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin_login_required")
    admin = db.get(AdminUser, int(admin_id))
    session_version = request.session.get("admin_session_version")
    if admin is None or not admin.is_active or session_version != admin.session_version:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin_login_required")
    return admin


def require_csrf(request: Request) -> None:
    expected = request.session.get("csrf_token") if hasattr(request, "session") else None
    supplied = request.headers.get("X-CSRF-Token")
    if not expected or not supplied or expected != supplied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf_failed")


def client_ip(request: Request) -> str:
    settings = request.app.state.settings
    if settings.trusted_proxy_headers:
        for header in ("CF-Connecting-IP", "X-Forwarded-For"):
            value = request.headers.get(header)
            if value:
                return value.split(",", 1)[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]
