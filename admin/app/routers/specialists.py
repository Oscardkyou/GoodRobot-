"""Маршруты для управления специалистами в админке."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from admin.app.auth import get_current_admin
from admin.app.schemas import UserResponse
from app.models.specialty import Specialty
from app.models.user import User
from core.db import get_session

# Настройка логирования
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")


@router.get("/", response_class=HTMLResponse)
async def get_specialists_page(request: Request):
    """Отображает страницу со списком специалистов."""
    return templates.TemplateResponse(
        "specialists.html", 
        {"request": request, "page_type": "private"}
    )


@router.get("/api", response_model=List[UserResponse])
async def get_specialists(
    skip: int = 0,
    limit: int = 20,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    specialty_id: Optional[int] = None,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Получает список специалистов с возможностью фильтрации."""
    query = select(User).options(
        selectinload(User.specialties)
    ).filter(User.role == "master")
    
    # Применяем фильтры
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if search:
        query = query.filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%")
            )
        )
    
    if specialty_id:
        query = query.join(User.specialties).filter(Specialty.id == specialty_id)
    
    # Сортировка и пагинация
    query = query.order_by(User.id.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    specialists = result.scalars().all()
    
    # Подготавливаем данные для ответа
    for specialist in specialists:
        specialist.telegram_id = getattr(specialist, "tg_id", None)
        specialist.full_name = getattr(specialist, "name", None) or "Без имени"
        specialist.username = getattr(specialist, "username", "") or ""
    
    return specialists


@router.get("/api/specialties")
async def get_all_specialties(
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Получает список всех специальностей для фильтрации."""
    query = select(Specialty).filter(Specialty.is_active == True).order_by(Specialty.name)
    result = await db.execute(query)
    specialties = result.scalars().all()
    
    return [
        {
            "id": specialty.id,
            "name": specialty.name,
            "is_active": specialty.is_active
        }
        for specialty in specialties
    ]


@router.get("/api/{specialist_id}")
async def get_specialist_details(
    specialist_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Получает детальную информацию о специалисте."""
    query = select(User).options(
        selectinload(User.specialties)
    ).filter(User.id == specialist_id, User.role == "master")
    
    result = await db.execute(query)
    specialist = result.scalars().first()
    
    if not specialist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Специалист с ID {specialist_id} не найден"
        )
    
    # Получаем статистику заказов
    from sqlalchemy import func
    from app.models import Order
    
    orders_query = select(
        func.count(Order.id).label("total_orders"),
        func.count(Order.id).filter(Order.status == "completed").label("completed_orders")
    ).filter(Order.master_id == specialist_id)
    
    orders_result = await db.execute(orders_query)
    orders_stats = orders_result.first()
    
    # Формируем ответ
    response = {
        "id": specialist.id,
        "telegram_id": specialist.tg_id,
        "full_name": specialist.name or "Без имени",
        "username": specialist.username or "",
        "phone": specialist.phone or "",
        "email": specialist.email or "",
        "rating": specialist.rating_avg or 0,
        "is_active": specialist.is_active,
        "created_at": specialist.created_at.isoformat() if specialist.created_at else None,
        "specialties": [
            {
                "id": specialty.id,
                "name": specialty.name
            }
            for specialty in specialist.specialties
        ],
        "orders_stats": {
            "total": orders_stats.total_orders or 0,
            "completed": orders_stats.completed_orders or 0,
            "completion_rate": round((orders_stats.completed_orders / orders_stats.total_orders) * 100, 1) if orders_stats.total_orders else 0
        }
    }
    
    return response


@router.put("/api/{specialist_id}/toggle-active")
async def toggle_specialist_active_status(
    specialist_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Включает/выключает активный статус специалиста."""
    query = select(User).filter(User.id == specialist_id, User.role == "master")
    result = await db.execute(query)
    specialist = result.scalars().first()
    
    if not specialist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Специалист с ID {specialist_id} не найден"
        )
    
    # Инвертируем статус
    specialist.is_active = not specialist.is_active
    await db.commit()
    
    return {
        "id": specialist.id,
        "is_active": specialist.is_active
    }