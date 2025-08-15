from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_, func
from typing import List, Optional
from datetime import datetime, date

from app.models.payout import Payout
from app.models.user import User
from admin.app.database import get_db
from admin.app.auth import get_current_admin
from admin.app.schemas import PayoutResponse, PayoutCreate, PayoutUpdate

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")

@router.get("/", response_class=HTMLResponse)
async def get_payouts_page(request: Request, current_admin=Depends(get_current_admin)):
    """Отображает страницу со списком выплат"""
    return templates.TemplateResponse("payouts.html", {"request": request, "current_user": current_admin})

@router.get("/api", response_model=List[PayoutResponse])
async def get_payouts(
    skip: int = 0, 
    limit: int = 10, 
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Получает список выплат с возможностью фильтрации"""
    query = select(Payout)
    
    # Применяем фильтры, если они указаны
    if user_id:
        query = query.filter(Payout.user_id == user_id)
    if status:
        query = query.filter(Payout.status == status)
    if date_from:
        start_date = datetime.combine(date_from, datetime.min.time())
        query = query.filter(Payout.created_at >= start_date)
    if date_to:
        end_date = datetime.combine(date_to, datetime.max.time())
        query = query.filter(Payout.created_at <= end_date)
    
    # Добавляем пагинацию и сортировку по убыванию даты создания
    query = query.offset(skip).limit(limit).order_by(Payout.created_at.desc())
    
    result = await db.execute(query)
    payouts = result.scalars().all()
    
    return payouts

@router.get("/{payout_id}", response_class=HTMLResponse)
async def get_payout_page(
    request: Request, 
    payout_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Отображает страницу с детальной информацией о выплате"""
    # Получаем выплату
    query = select(Payout).filter(Payout.id == payout_id)
    result = await db.execute(query)
    payout = result.scalar_one_or_none()
    
    if not payout:
        raise HTTPException(status_code=404, detail="Выплата не найдена")
    
    # Получаем информацию о пользователе
    user_query = select(User).filter(User.id == payout.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    return templates.TemplateResponse(
        "payout_detail.html", 
        {
            "request": request, 
            "payout": payout, 
            "user": user,
            "current_user": current_admin
        }
    )

@router.get("/api/{payout_id}", response_model=PayoutResponse)
async def get_payout(
    payout_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Получает информацию о конкретной выплате"""
    query = select(Payout).filter(Payout.id == payout_id)
    result = await db.execute(query)
    payout = result.scalar_one_or_none()
    
    if not payout:
        raise HTTPException(status_code=404, detail="Выплата не найдена")
    
    return payout

@router.post("/api", response_model=PayoutResponse)
async def create_payout(
    payout_data: PayoutCreate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Создает новую выплату"""
    # Проверяем существование пользователя
    user_query = select(User).filter(User.id == payout_data.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Создаем новую выплату
    new_payout = Payout(
        user_id=payout_data.user_id,
        amount=payout_data.amount,
        status="pending",
        payment_method=payout_data.payment_method,
        payment_details=payout_data.payment_details,
        description=payout_data.description
    )
    
    db.add(new_payout)
    await db.commit()
    await db.refresh(new_payout)
    
    return new_payout

@router.post("/api/{payout_id}/approve")
async def approve_payout(
    payout_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Подтверждает выплату"""
    query = select(Payout).filter(Payout.id == payout_id)
    result = await db.execute(query)
    payout = result.scalar_one_or_none()
    
    if not payout:
        raise HTTPException(status_code=404, detail="Выплата не найдена")
    
    if payout.status != "pending":
        raise HTTPException(status_code=400, detail="Нельзя подтвердить выплату в текущем статусе")
    
    payout.status = "approved"
    payout.processed_at = datetime.now()
    payout.processed_by = current_admin.id
    await db.commit()
    
    return {"message": "Выплата подтверждена"}

@router.post("/api/{payout_id}/reject")
async def reject_payout(
    payout_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Отклоняет выплату"""
    query = select(Payout).filter(Payout.id == payout_id)
    result = await db.execute(query)
    payout = result.scalar_one_or_none()
    
    if not payout:
        raise HTTPException(status_code=404, detail="Выплата не найдена")
    
    if payout.status != "pending":
        raise HTTPException(status_code=400, detail="Нельзя отклонить выплату в текущем статусе")
    
    payout.status = "rejected"
    payout.processed_at = datetime.now()
    payout.processed_by = current_admin.id
    await db.commit()
    
    return {"message": "Выплата отклонена"}

@router.put("/api/{payout_id}", response_model=PayoutResponse)
async def update_payout(
    payout_id: int, 
    payout_update: PayoutUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Обновляет информацию о выплате"""
    query = select(Payout).filter(Payout.id == payout_id)
    result = await db.execute(query)
    payout = result.scalar_one_or_none()
    
    if not payout:
        raise HTTPException(status_code=404, detail="Выплата не найдена")
    
    # Обновляем только указанные поля
    update_data = payout_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(payout, key, value)
    
    await db.commit()
    await db.refresh(payout)
    
    return payout