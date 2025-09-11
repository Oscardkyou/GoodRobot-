
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from admin.app.auth import get_current_admin
from admin.app.database import get_db
from admin.app.schemas import UserResponse, UserUpdate
from app.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")

@router.get("/", response_class=HTMLResponse)
async def get_users_page(request: Request, current_admin=Depends(get_current_admin)):
    """Отображает страницу со списком пользователей"""
    return templates.TemplateResponse("users.html", {"request": request, "current_user": current_admin})

@router.get("/api", response_model=list[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 10,
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Получает список пользователей с возможностью фильтрации"""
    query = select(User)

    # Применяем фильтры, если они указаны
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%")
            )
        )

    # Добавляем пагинацию
    query = query.offset(skip).limit(limit).order_by(User.id.desc())

    result = await db.execute(query)
    users = result.scalars().all()

    return users

@router.get("/{user_id}", response_class=HTMLResponse)
async def get_user_page(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Отображает страницу с детальной информацией о пользователе"""
    query = select(User).filter(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return templates.TemplateResponse(
        "user_detail.html",
        {"request": request, "user": user, "current_user": current_admin}
    )

@router.get("/api/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Получает информацию о конкретном пользователе"""
    query = select(User).filter(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return user

@router.post("/api/{user_id}/block")
async def block_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Блокирует пользователя"""
    query = select(User).filter(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.is_active = False
    await db.commit()

    return {"message": "Пользователь заблокирован"}

@router.post("/api/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Разблокирует пользователя"""
    query = select(User).filter(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.is_active = True
    await db.commit()

    return {"message": "Пользователь разблокирован"}

@router.put("/api/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Обновляет информацию о пользователе"""
    query = select(User).filter(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Обновляем только указанные поля
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)

    return user
