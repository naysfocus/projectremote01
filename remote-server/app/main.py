from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.session_middleware import DynamicSessionMiddleware

from app import __version__
from app.api.admin import router as admin_api_router
from app.api.client import router as client_api_router
from app.config import Settings
from app.database import Database
from app.rate_limit import InMemoryRateLimitMiddleware, Limit
from app.web.routes import router as web_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.validate()
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        logging.getLogger("app").info(
            "Starting %s v%s (%s, cookie_secure_mode=%s)",
            settings.app_name,
            __version__,
            settings.environment,
            settings.session_cookie_secure_mode,
        )
        yield

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/api/docs" if settings.environment != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = Database(settings)

    app.add_middleware(
        DynamicSessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=settings.session_cookie_name,
        max_age=8 * 60 * 60,
        same_site="strict",
        secure_mode=settings.session_cookie_secure_mode,
    )
    app.add_middleware(
        InMemoryRateLimitMiddleware,
        rules={
            "POST /api/v1/activate": Limit(10, 60),
            "POST /api/v1/session/open": Limit(30, 60),
            "POST /api/v1/session/heartbeat": Limit(120, 60),
            "POST /api/v1/report": Limit(120, 60),
            "POST /login": Limit(10, 60),
        },
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'",
        )
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception(_request: Request, exc: Exception):
        logging.getLogger("app").exception("Unhandled application error", exc_info=exc)
        return JSONResponse(status_code=500, content={"ok": False, "error": "internal_server_error"})

    @app.get("/health", tags=["system"])
    def health():
        return {"ok": True, "service": "remote-server", "version": __version__}

    @app.get("/ready", tags=["system"])
    def ready():
        try:
            with app.state.database.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - tested through failure injection only
            logging.getLogger("app").exception("Readiness database check failed", exc_info=exc)
            return JSONResponse(
                status_code=503,
                content={"ok": False, "service": "remote-server", "database": "unavailable"},
            )
        return {
            "ok": True,
            "service": "remote-server",
            "version": __version__,
            "database": "ready",
        }

    app.include_router(client_api_router)
    app.include_router(admin_api_router)
    app.include_router(web_router)
    app.mount("/static", StaticFiles(directory=Path("app/static")), name="static")
    return app


app = create_app()
