from fastapi import FastAPI, Depends, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm, SecurityScopes
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
import os

from admin.app.database import get_db
from admin.app.auth import authenticate_user, create_access_token, get_current_admin
from admin.app.routers import api_router
from admin.app.schemas import Token
from core.config import get_settings

# Получаем настройки
settings = get_settings()

# Глобальная переменная для шаблонов
templates = None

def create_app():
    """Создание и настройка экземпляра FastAPI приложения"""
    # Создаем экземпляр FastAPI
    app = FastAPI(
        title="GoodRobot Admin Panel",
        description="Админ-панель для управления ботом GoodRobot",
        version="1.0.0",
    )

    # Подключаем статические файлы
    app.mount("/static", StaticFiles(directory="admin/static"), name="static")

    # Настраиваем шаблоны Jinja2
    global templates
    templates = Jinja2Templates(directory="admin/templates")

    # Подключаем все роутеры из модуля routers
    app.include_router(api_router)
    
    # Определяем маршруты
    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        """Главная страница админ-панели (дашборд)"""
        return templates.TemplateResponse("dashboard.html", {"request": request, "page_type": "private"})

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        """Страница входа в админ-панель"""
        return templates.TemplateResponse("login.html", {"request": request, "page_type": "public"})
        
    @app.get("/masters", response_class=HTMLResponse)
    async def masters_page(request: Request):
        """Страница управления мастерами"""
        return templates.TemplateResponse("masters.html", {"request": request, "page_type": "private"})
        
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_redirect(request: Request):
        """Перенаправление с /dashboard на главную страницу"""
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    @app.post("/token", response_model=Token)
    async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db),
    ):
        """Выдача JWT токена для админ-панели"""
        user = await authenticate_user(form_data.username, form_data.password, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Включаем admin scope, т.к. все приватные эндпоинты требуют его
        access_token = create_access_token(
            data={"sub": user.username, "scopes": ["admin"]},
            expires_delta=timedelta(minutes=60),
        )
        return {"access_token": access_token, "token_type": "bearer"}

    @app.get("/logout")
    async def logout():
        """Выход из админ-панели"""
        response = RedirectResponse(url="/login")
        # В будущем здесь можно будет очищать сессию
        return response
        
    return app