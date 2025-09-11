
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from admin.app.auth import get_current_admin, get_password_hash, verify_password
from admin.app.database import get_db
from admin.app.schemas import UserResponse
from app.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")

@router.get("/", response_class=HTMLResponse)
async def get_admins_page(request: Request, current_admin=Depends(get_current_admin)):
    """Отображает страницу со списком администраторов"""
    return templates.TemplateResponse("admins.html", {"request": request, "current_user": current_admin})

@router.get("/api", response_model=list[UserResponse])
async def get_admins(
    skip: int = 0,
    limit: int = 10,
    is_active: bool | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Получает список администраторов с возможностью фильтрации"""
    # Базовый запрос на выборку администраторов
    query = select(User).filter(User.role == "admin")

    # Применяем фильтры, если они указаны
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    # Добавляем пагинацию
    query = query.offset(skip).limit(limit).order_by(User.id.desc())

    result = await db.execute(query)
    admins = result.scalars().all()

    return admins

@router.get("/create", response_class=HTMLResponse)
async def get_create_admin_page(request: Request, current_admin=Depends(get_current_admin)):
    """Отображает страницу создания нового администратора"""
    return templates.TemplateResponse("admin_create.html", {"request": request, "current_user": current_admin})

@router.post("/create", response_class=HTMLResponse)
async def create_admin(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    name: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Создает нового администратора"""
    # Проверяем, существует ли пользователь с таким именем
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        return templates.TemplateResponse(
            "admin_create.html",
            {
                "request": request,
                "current_user": current_admin,
                "error": "Пользователь с таким именем уже существует"
            },
            status_code=400
        )

    # Создаем нового администратора
    hashed_password = get_password_hash(password)
    new_admin = User(
        username=username,
        hashed_password=hashed_password,
        email=email,
        role="admin",
        tg_id=0,  # Фиктивный tg_id для администратора
        name=name or username,
        is_active=True
    )

    db.add(new_admin)
    await db.commit()

    return RedirectResponse(url="/admins", status_code=303)

@router.get("/{admin_id}", response_class=HTMLResponse)
async def get_admin_page(
    request: Request,
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Отображает страницу с детальной информацией об администраторе"""
    query = select(User).filter(User.id == admin_id, User.role == "admin")
    result = await db.execute(query)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(status_code=404, detail="Администратор не найден")

    return templates.TemplateResponse(
        "admin_detail.html",
        {"request": request, "admin": admin, "current_user": current_admin}
    )

@router.get("/api/{admin_id}", response_model=UserResponse)
async def get_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Получает информацию о конкретном администраторе"""
    query = select(User).filter(User.id == admin_id, User.role == "admin")
    result = await db.execute(query)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(status_code=404, detail="Администратор не найден")

    return admin

@router.post("/api/{admin_id}/block")
async def block_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Блокирует администратора"""
    # Проверяем, не пытается ли админ заблокировать сам себя
    if current_admin.id == admin_id:
        raise HTTPException(status_code=400, detail="Нельзя заблокировать самого себя")

    query = select(User).filter(User.id == admin_id, User.role == "admin")
    result = await db.execute(query)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(status_code=404, detail="Администратор не найден")

    admin.is_active = False
    await db.commit()

    return {"message": "Администратор заблокирован"}

@router.post("/api/{admin_id}/unblock")
async def unblock_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Разблокирует администратора"""
    query = select(User).filter(User.id == admin_id, User.role == "admin")
    result = await db.execute(query)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(status_code=404, detail="Администратор не найден")

    admin.is_active = True
    await db.commit()

    return {"message": "Администратор разблокирован"}

@router.post("/api/{admin_id}/change-password")
async def change_admin_password(
    admin_id: int,
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Изменяет пароль администратора"""
    # Проверяем, меняет ли админ свой собственный пароль
    if current_admin.id != admin_id:
        raise HTTPException(status_code=403, detail="Можно менять только свой пароль")

    # Проверяем текущий пароль
    if not verify_password(current_password, current_admin.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")

    # Обновляем пароль
    current_admin.hashed_password = get_password_hash(new_password)
    await db.commit()

    return {"message": "Пароль успешно изменен"}
