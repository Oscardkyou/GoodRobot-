import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from admin.app.auth import get_current_admin, get_password_hash
from admin.app.schemas import UserResponse
from admin.app.schemas_category import MasterCategoryResponse, MasterCategoryUpdate
from app.models.category import MasterCategory, master_categories
from app.models.specialty import Specialty
from app.models.user import User
from core.cache_service import get_master_categories_cache
from core.db import get_session

# Настройка логирования
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")

@router.get("/", response_class=HTMLResponse)
async def get_masters_page(request: Request):
    """Отображает страницу со списком мастеров.

    Важно: страница защищается на клиенте через наличие JWT в localStorage (см. `admin/templates/base.html`).
    Сами API-эндпоинты ниже защищены зависимостью `get_current_admin`.
    """
    return templates.TemplateResponse("masters.html", {"request": request, "page_type": "private"})

@router.get("/api", response_model=list[UserResponse])
async def get_masters(
    skip: int = 0,
    limit: int = 10,
    is_active: bool | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Получает список мастеров с возможностью фильтрации (оптимизировано)"""
    # Используем один оптимизированный запрос с загрузкой связанных данных
    from sqlalchemy.orm import selectinload

    query = select(User).options(
        selectinload(User.specialties),
        selectinload(User.categories)
    ).filter(User.role == "master")

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

    # Оптимизированная обработка вычисляемых атрибутов
    for m in masters:
        # Устанавливаем алиасы для схемы ответа
        m.telegram_id = getattr(m, "tg_id", None)
        m.full_name = getattr(m, "name", None)
        m.username = getattr(m, "username", "") or ""
        m.zones = []

    return masters

@router.post("/api", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_master(
    user_data: dict,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Создает нового мастера с возможностью назначения специальностей (оптимизировано)"""
    # Извлекаем данные из запроса
    telegram_id = user_data.get('telegram_id')
    username = user_data.get('username')
    full_name = user_data.get('full_name')
    phone = user_data.get('phone')
    password = user_data.get('password')
    specialty_ids = user_data.get('specialty_ids', [])

    # Оптимизированная проверка уникальности - один запрос вместо трех
    conditions = []
    if telegram_id:
        conditions.append(User.tg_id == telegram_id)
    if username:
        conditions.append(User.username == username)
    if phone:
        conditions.append(User.phone == phone)

    if conditions:
        # Один запрос для проверки всех уникальных полей
        from sqlalchemy import or_
        query = select(User).filter(or_(*conditions))
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Определяем, какое поле конфликтует
            if telegram_id and existing_user.tg_id == telegram_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким Telegram ID уже существует"
                )
            elif username and existing_user.username == username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким username уже существует"
                )
            elif phone and existing_user.phone == phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким телефоном уже существует"
                )

    # Создаем нового мастера
    new_master = User(
        username=username,
        name=full_name,
        phone=phone,
        tg_id=telegram_id,
        role="master",
        is_active=True
    )

    # Если пароль указан, устанавливаем его
    if password:
        new_master.hashed_password = get_password_hash(password)

    try:
        db.add(new_master)
        await db.commit()
        await db.refresh(new_master)

        # Если указаны специальности, добавляем их мастеру одним запросом
        if specialty_ids and len(specialty_ids) > 0:
            # Один запрос для получения всех специальностей
            query = select(Specialty).filter(Specialty.id.in_(specialty_ids))
            result = await db.execute(query)
            specialties = result.scalars().all()

            # Добавляем специальности мастеру
            for specialty in specialties:
                new_master.specialties.append(specialty)

            await db.commit()
            await db.refresh(new_master)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нарушение уникальности: Telegram ID, username или телефон уже существуют"
        )

    # Выставляем алиасы атрибутов для корректного ответа схемы
    new_master.telegram_id = getattr(new_master, "tg_id", None)
    new_master.full_name = getattr(new_master, "name", None)

    return new_master

@router.post("/api/{master_id}/block")
async def block_master(
    master_id: int,
    db: AsyncSession = Depends(get_session),
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
    db: AsyncSession = Depends(get_session),
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
    db: AsyncSession = Depends(get_session),
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
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Отображает страницу с детальной информацией о мастере"""
    logger.info(f"Requesting master page for ID: {master_id}", extra={
        "master_id": master_id,
        "user_agent": request.headers.get("user-agent", "unknown")
    })

    # Получаем информацию о мастере с загрузкой связанных данных
    from sqlalchemy.orm import selectinload
    query = select(User).options(
        selectinload(User.specialties),
        selectinload(User.categories)
    ).filter(User.id == master_id, User.role == "master")
    result = await db.execute(query)
    master = result.scalar_one_or_none()

    if not master:
        logger.warning("Master not found", extra={
            "master_id": master_id,
            "requested_by": current_admin.username
        })
        raise HTTPException(status_code=404, detail="Мастер не найден")

    # Получаем все доступные специальности для выбора
    specialties_query = select(Specialty).order_by(Specialty.name)
    result = await db.execute(specialties_query)
    all_specialties = result.scalars().all()

    # Получаем все доступные категории
    all_categories = MasterCategory.get_all_categories()

    # Получаем текущие категории мастера (теперь они загружены)
    master_categories_list = list(master.categories) if master.categories else []

    # Получаем текущие специальности мастера (теперь они загружены)
    master_specialties_list = list(master.specialties) if master.specialties else []

    # Кэшируем категории мастера для будущих запросов
    if master_categories_list:
        cache_service = await get_master_categories_cache()
        await cache_service.set_master_categories(master_id, master_categories_list)

    # Получаем статистику заказов мастера
    # В реальном приложении здесь был бы запрос к таблице заказов
    # Для примера используем заглушку
    master_stats = {
        "completed_orders": 0,  # Заглушка, в реальном приложении заменить на запрос
        "active_orders": 0     # Заглушка, в реальном приложении заменить на запрос
    }

    # Если есть модель Order, то можно использовать такой запрос:
    # from app.models.order import Order
    # completed_query = select(func.count()).select_from(Order).filter(
    #     Order.master_id == master_id,
    #     Order.status == "completed"
    # )
    # active_query = select(func.count()).select_from(Order).filter(
    #     Order.master_id == master_id,
    #     Order.status.in_(["active", "in_progress"])
    # )
    # result = await db.execute(completed_query)
    # master_stats["completed_orders"] = result.scalar()
    # result = await db.execute(active_query)
    # master_stats["active_orders"] = result.scalar()

    return templates.TemplateResponse(
        "master_detail.html",
        {
            "request": request,
            "master": master,
            "current_user": current_admin,
            "all_specialties": all_specialties,
            "all_categories": all_categories,
            "master_categories": master_categories_list,
            "master_specialties": master_specialties_list,
            "master_stats": master_stats
        }
    )


@router.post("/api/masters/{master_id}/categories", response_model=MasterCategoryResponse)
async def update_master_categories(
    master_id: int,
    categories: MasterCategoryUpdate,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Обновляет категории мастера с валидацией."""
    try:
        logger.info(f"Updating categories for master {master_id}", extra={
            "master_id": master_id,
            "admin_username": current_admin.username,
            "categories_count": len(categories.categories)
        })

        # Проверяем существование мастера
        query = select(User).filter(User.id == master_id, User.role == "master")
        result = await db.execute(query)
        master = result.scalar_one_or_none()

        if not master:
            logger.warning("Master not found", extra={
                "master_id": master_id,
                "admin_username": current_admin.username
            })
            raise HTTPException(status_code=404, detail="Мастер не найден")

        # Валидация категорий происходит автоматически через Pydantic
        # Удаляем текущие связи
        await db.execute(
            delete(master_categories).where(master_categories.c.user_id == master_id)
        )

        # Добавляем новые связи
        for category in categories.categories:
            await db.execute(
                master_categories.insert().values(
                    user_id=master_id,
                    category=category
                )
            )

        await db.commit()

        # Обновляем кэш после успешного обновления в БД
        cache_service = await get_master_categories_cache()
        cache_success = await cache_service.set_master_categories(master_id, categories.categories)

        if cache_success:
            logger.info(f"Successfully updated cache for master {master_id}", extra={
                "master_id": master_id,
                "admin_username": current_admin.username,
                "cache_updated": True
            })
        else:
            logger.warning(f"Failed to update cache for master {master_id}", extra={
                "master_id": master_id,
                "admin_username": current_admin.username,
                "cache_updated": False
            })

        # Получаем обновленный список категорий для ответа
        updated_categories = categories.categories

        logger.info(f"Successfully updated categories for master {master_id}", extra={
            "master_id": master_id,
            "admin_username": current_admin.username,
            "categories": updated_categories
        })

        return MasterCategoryResponse(
            categories=updated_categories,
            master_id=master_id,
            updated_at=datetime.now().isoformat()
        )

    except HTTPException:
        # Перебрасываем HTTP исключения без изменений
        raise
    except Exception as e:
        logger.error("Error updating master categories", extra={
            "master_id": master_id,
            "admin_username": current_admin.username,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при обновлении категорий"
        )
