
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from admin.app.auth import get_current_admin
from core.db import get_session
from admin.app.schemas_specialty import (
    MasterSpecialtyUpdate,
    SpecialtyCreate,
    SpecialtyResponse,
    SpecialtyUpdate,
)
from app.models.specialty import Specialty, master_specialties
from app.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")

@router.get("/", response_class=HTMLResponse)
async def get_specialties_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Отображает страницу со списком специальностей."""
    query = select(Specialty).order_by(Specialty.name)
    result = await db.execute(query)
    specialties = result.scalars().all()

    return templates.TemplateResponse(
        "specialties.html",
        {"request": request, "specialties": specialties}
    )

@router.get("/view/{specialty_id}", response_class=HTMLResponse)
async def get_specialty_detail(
    specialty_id: int,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Отображает детальную страницу специальности.

    Путь изменён на /view/{specialty_id}, чтобы избежать конфликта со статическим /api.
    """
    # Получаем специальность
    query = select(Specialty).filter(Specialty.id == specialty_id)
    result = await db.execute(query)
    specialty = result.scalar_one_or_none()

    if not specialty:
        raise HTTPException(status_code=404, detail="Специальность не найдена")

    # Получаем мастеров с этой специальностью
    query = select(User).join(master_specialties).filter(
        master_specialties.c.specialty_id == specialty_id,
        User.role == "master"
    )
    result = await db.execute(query)
    masters = result.scalars().all()

    return templates.TemplateResponse(
        "specialty_detail.html",
        {"request": request, "specialty": specialty, "masters": masters}
    )

# API endpoints для работы со специальностями

@router.get("/api", response_model=list[SpecialtyResponse])
async def list_specialties(
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
):
    """Возвращает список специальностей с optional фильтром активности."""
    query = select(Specialty)
    if is_active is not None:
        query = query.filter(Specialty.is_active == is_active)
    query = query.order_by(Specialty.name)

    result = await db.execute(query)
    specialties = result.scalars().all()
    return specialties

@router.post("/api/specialties", response_model=SpecialtyResponse)
async def create_specialty(
    specialty: SpecialtyCreate,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Создает новую специальность."""
    try:
        new_specialty = Specialty(
            name=specialty.name,
            is_active=specialty.is_active
        )
        db.add(new_specialty)
        await db.commit()
        await db.refresh(new_specialty)
        return new_specialty
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Специальность с таким названием уже существует"
        )

@router.put("/api/specialties/{specialty_id}", response_model=SpecialtyResponse)
async def update_specialty(
    specialty_id: int,
    specialty_data: SpecialtyUpdate,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Обновляет существующую специальность."""
    query = select(Specialty).filter(Specialty.id == specialty_id)
    result = await db.execute(query)
    specialty = result.scalar_one_or_none()

    if not specialty:
        raise HTTPException(status_code=404, detail="Специальность не найдена")

    update_data = specialty_data.dict(exclude_unset=True)

    try:
        for key, value in update_data.items():
            setattr(specialty, key, value)

        await db.commit()
        await db.refresh(specialty)
        return specialty
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка при обновлении специальности"
        )

@router.delete("/api/specialties/{specialty_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_specialty(
    specialty_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Удаляет специальность.

    Перед удалением чистим связи в таблице master_specialties, чтобы избежать FK-ошибок.
    """
    query = select(Specialty).filter(Specialty.id == specialty_id)
    result = await db.execute(query)
    specialty = result.scalar_one_or_none()

    if not specialty:
        raise HTTPException(status_code=404, detail="Специальность не найдена")

    # Сначала удаляем связи мастер↔специальности
    await db.execute(delete(master_specialties).where(master_specialties.c.specialty_id == specialty_id))
    # Затем удаляем саму специальность
    await db.execute(delete(Specialty).filter(Specialty.id == specialty_id))
    await db.commit()

    return None

@router.post("/api/masters/{master_id}/specialties")
async def update_master_specialties(
    master_id: int,
    specialties: MasterSpecialtyUpdate,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin)
):
    """Обновляет специальности мастера."""
    # Проверяем существование мастера
    query = select(User).filter(User.id == master_id, User.role == "master")
    result = await db.execute(query)
    master = result.scalar_one_or_none()

    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")

    # Проверяем существование всех специальностей
    for specialty_id in specialties.specialty_ids:
        query = select(Specialty).filter(Specialty.id == specialty_id)
        result = await db.execute(query)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Специальность с ID {specialty_id} не найдена"
            )

    # Удаляем текущие связи
    await db.execute(
        delete(master_specialties).where(master_specialties.c.user_id == master_id)
    )

    # Добавляем новые связи
    for specialty_id in specialties.specialty_ids:
        await db.execute(
            master_specialties.insert().values(
                user_id=master_id,
                specialty_id=specialty_id
            )
        )

    await db.commit()

    return {"status": "success", "message": "Специальности мастера обновлены"}
