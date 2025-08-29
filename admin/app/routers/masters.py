from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, delete
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from app.models.user import User
from admin.app.database import get_db
from admin.app.auth import get_current_admin, get_password_hash
from admin.app.schemas import UserResponse, UserCreate, UserUpdate

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")

@router.get("/", response_class=HTMLResponse)
async def get_masters_page(request: Request):
    """Отображает страницу со списком мастеров.

    Важно: страница защищается на клиенте через наличие JWT в localStorage (см. `admin/templates/base.html`).
    Сами API-эндпоинты ниже защищены зависимостью `get_current_admin`.
    """
    return templates.TemplateResponse("masters.html", {"request": request, "page_type": "private"})

@router.get("/api", response_model=List[UserResponse])
async def get_masters(
    skip: int = 0, 
    limit: int = 10, 
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Получает список мастеров с возможностью фильтрации"""
    # Базовый запрос на выборку мастеров
    query = select(User).filter(User.role == "master")
    
    # Применяем фильтры, если они указаны
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.name.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%")
            )
        )
    
    # Сортировка и пагинация
    query = query.order_by(User.id.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    masters = result.scalars().all()
    # Дополняем вычисляемыми атрибутами для схемы ответа
    for m in masters:
        setattr(m, "telegram_id", getattr(m, "tg_id", None))
        setattr(m, "full_name", getattr(m, "name", None))
        # Обеспечиваем строковый username (не None), чтобы пройти валидацию схемы
        if getattr(m, "username", None) is None:
            setattr(m, "username", "")
        # Районы удалены из модели
        setattr(m, "zones", [])
    return masters

@router.post("/api", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_master(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Создает нового мастера"""
    # Проверяем, что пользователь с таким telegram_id еще не существует
    if user.telegram_id:
        query = select(User).filter(User.tg_id == user.telegram_id)
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким Telegram ID уже существует"
            )

    # Проверяем уникальность username
    if user.username:
        result = await db.execute(select(User).filter(User.username == user.username))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким username уже существует"
            )

    # Проверяем уникальность телефона
    if user.phone:
        result = await db.execute(select(User).filter(User.phone == user.phone))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким телефоном уже существует"
            )
    
    # Создаем нового мастера
    new_master = User(
        username=user.username,
        name=user.full_name,
        phone=user.phone,
        tg_id=user.telegram_id,
        # Районы удалены из модели
        role="master",
        is_active=True
    )
    
    # Если пароль указан, устанавливаем его
    if user.password:
        new_master.hashed_password = get_password_hash(user.password)
    
    try:
        db.add(new_master)
        await db.commit()
        await db.refresh(new_master)
    except IntegrityError:
        await db.rollback()
        # На случай гонок или других уникальных ограничений
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нарушение уникальности: Telegram ID, username или телефон уже существуют"
        )
    # Выставляем алиасы атрибутов для корректного ответа схемы
    setattr(new_master, "telegram_id", getattr(new_master, "tg_id", None))
    setattr(new_master, "full_name", getattr(new_master, "name", None))
    
    return new_master

@router.post("/api/{master_id}/block")
async def block_master(
    master_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Блокирует мастера"""
    query = select(User).filter(User.id == master_id, User.role == "master")
    result = await db.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    master.is_active = False
    await db.commit()
    
    return {"message": "Мастер заблокирован"}

@router.post("/api/{master_id}/unblock")
async def unblock_master(
    master_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Разблокирует мастера"""
    query = select(User).filter(User.id == master_id, User.role == "master")
    result = await db.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    master.is_active = True
    await db.commit()
    
    return {"message": "Мастер разблокирован"}

@router.delete("/api/{master_id}")
async def delete_master(
    master_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Удаляет мастера"""
    # Проверяем существование мастера
    query = select(User).filter(User.id == master_id, User.role == "master")
    result = await db.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    # Удаляем самого мастера
    await db.delete(master)
    await db.commit()
    
    return {"message": "Мастер удален"}

@router.get("/{master_id}", response_class=HTMLResponse)
async def get_master_page(
    request: Request, 
    master_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Отображает страницу с детальной информацией о мастере"""
    query = select(User).filter(User.id == master_id, User.role == "master")
    result = await db.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    return templates.TemplateResponse(
        "master_detail.html", 
        {"request": request, "master": master, "current_user": current_admin}
    )
