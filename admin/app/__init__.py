"""
Thin compatibility layer for the Admin app.

Provides a stable import surface under `admin.app.*` while the actual
implementation currently lives in `backup/admin_backup/app`.

This module defines `create_app()` and mounts static/templates using
absolute paths so it works both locally and inside Docker.
"""
from __future__ import annotations

import os
from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

# Re-use logic from backup implementation
from backup.admin_backup.app.auth import (
    authenticate_user,
    create_access_token,
    get_current_admin,
)
from backup.admin_backup.app.routers import api_router
from backup.admin_backup.app.schemas import Token
from core.config import get_settings
from core.db import get_session

# Settings
settings = get_settings()

# Global templates ref (used by route handlers below)
_templates: Jinja2Templates | None = None


def _resolve_path(*parts: str) -> str:
    """Return absolute path joining repo root and provided parts.

    Falls back to current working directory if repo root cannot be inferred.
    """
    # repo root is two levels up from this file: admin/app/__init__.py
    this_dir = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(this_dir, os.pardir, os.pardir))
    return os.path.join(repo_root, *parts)


def create_app() -> FastAPI:
    """Create and configure FastAPI Admin application.

    Uses absolute paths for static and templates. Prefers `admin/` locations
    if present, otherwise falls back to `backup/admin_backup/` assets.
    """
    app = FastAPI(
        title="GoodRobot Admin Panel",
        description="Админ-панель для управления ботом GoodRobot",
        version="1.0.0",
    )

    # Resolve assets
    admin_static = _resolve_path("admin", "static")
    admin_templates = _resolve_path("admin", "templates")
    backup_static = _resolve_path("backup", "admin_backup", "static")
    backup_templates = _resolve_path("backup", "admin_backup", "templates")

    static_dir = admin_static if os.path.isdir(admin_static) else backup_static
    templates_dir = (
        admin_templates if os.path.isdir(admin_templates) else backup_templates
    )

    # Mount static and configure templates
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    global _templates
    _templates = Jinja2Templates(directory=templates_dir)
    _templates.env.auto_reload = True
    _templates.env.cache_size = 0

    # Include routers from backup implementation
    app.include_router(api_router)

    # Basic pages
    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        assert _templates is not None
        return _templates.TemplateResponse(
            "dashboard.html", {"request": request, "page_type": "private"}
        )

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        assert _templates is not None
        return _templates.TemplateResponse(
            "login.html", {"request": request, "page_type": "public"}
        )

    @app.get("/masters", response_class=HTMLResponse)
    async def masters_page(request: Request):
        assert _templates is not None
        return _templates.TemplateResponse(
            "masters.html", {"request": request, "page_type": "private"}
        )

    @app.get("/specialties", response_class=HTMLResponse)
    async def specialties_page(request: Request):
        assert _templates is not None
        return _templates.TemplateResponse(
            "specialties.html", {"request": request, "page_type": "private"}
        )

    @app.get("/specialists", response_class=HTMLResponse)
    async def specialists_page(request: Request):
        assert _templates is not None
        return _templates.TemplateResponse(
            "specialists.html", {"request": request, "page_type": "private"}
        )

    @app.get("/client-actions", response_class=HTMLResponse)
    async def client_actions_page(request: Request):
        assert _templates is not None
        return _templates.TemplateResponse(
            "client_actions.html", {"request": request, "page_type": "private"}
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_redirect(request: Request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    @app.post("/token", response_model=Token)
    async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_session),
    ):
        user = await authenticate_user(form_data.username, form_data.password, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = create_access_token(
            data={"sub": user.username, "scopes": ["admin"]},
            expires_delta=timedelta(minutes=60),
        )
        return {"access_token": access_token, "token_type": "bearer"}

    @app.get("/logout")
    async def logout():
        return RedirectResponse(url="/login")

    return app
