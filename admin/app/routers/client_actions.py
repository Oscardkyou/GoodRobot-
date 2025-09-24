"""Маршруты для отображения действий клиента в админке."""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from admin.app.auth import get_current_admin
from admin.app.models import ClientAction
from app.models.user import User
from core.db import get_session

# Настройка логирования
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


@router.get("/", response_class=HTMLResponse)
async def get_client_actions_page(request: Request):
    """Отображает страницу с действиями клиентов."""
    return templates.TemplateResponse(
        "client_actions.html", 
        {"request": request, "page_type": "private"}
    )


@router.get("/api")
async def get_client_actions(
    skip: int = 0,
    limit: int = 20,
    user_id: int = None,
    action_type: str = None,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Получает список действий клиентов с возможностью фильтрации."""
    query = select(ClientAction).options(joinedload(ClientAction.user))
    
    # Применяем фильтры
    if user_id:
        query = query.filter(ClientAction.user_id == user_id)
    if action_type:
        query = query.filter(ClientAction.action_type == action_type)
    
    # Сортировка и пагинация
    query = query.order_by(desc(ClientAction.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    actions = result.scalars().all()
    
    # Преобразуем в формат для ответа
    response_data = []
    for action in actions:
        action_data = {}
        if action.action_data:
            try:
                action_data = json.loads(action.action_data)
            except json.JSONDecodeError:
                action_data = {"raw": action.action_data}
        
        response_data.append({
            "id": action.id,
            "user_id": action.user_id,
            "user_name": action.user.name if action.user else "Неизвестно",
            "action_type": action.action_type,
            "description": action.description,
            "metadata": action_data,  # Оставляем ключ metadata в ответе для совместимости
            "created_at": action.created_at.isoformat() if action.created_at else None
        })
    
    return response_data


@router.post("/api/log")
async def log_client_action(
    action_data: dict,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Логирует действие клиента."""
    user_id = action_data.get("user_id")
    action_type = action_data.get("action_type")
    description = action_data.get("description")
    metadata = action_data.get("metadata")
    
    if not user_id or not action_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать user_id и action_type"
        )
    
    # Проверяем существование пользователя
    user_query = select(User).filter(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {user_id} не найден"
        )
    
    # Создаем запись о действии
    action_data_str = json.dumps(metadata) if metadata else None
    client_action = ClientAction(
        user_id=user_id,
        action_type=action_type,
        description=description,
        action_data=action_data_str
    )
    
    db.add(client_action)
    await db.commit()
    await db.refresh(client_action)
    
    return {
        "id": client_action.id,
        "user_id": client_action.user_id,
        "action_type": client_action.action_type,
        "created_at": client_action.created_at.isoformat() if client_action.created_at else None
    }