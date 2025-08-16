from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
import os

from admin.app.database import get_db
from admin.app.auth import authenticate_user, create_access_token, get_current_admin
from admin.app.routers import api_router
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

    @app.get("/logout")
    async def logout():
        """Выход из админ-панели"""
        response = RedirectResponse(url="/login")
        # В будущем здесь можно будет очищать сессию
        return response
        
    return app