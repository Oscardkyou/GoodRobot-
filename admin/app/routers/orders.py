from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_, func
from typing import List, Optional
from datetime import datetime, date

from app.models.order import Order
from app.models.user import User
from admin.app.database import get_db
from admin.app.auth import get_current_admin
from admin.app.schemas import OrderResponse, OrderUpdate

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")

@router.get("/", response_class=HTMLResponse)
async def get_orders_page(request: Request, current_admin=Depends(get_current_admin)):
    """Отображает страницу со списком заказов"""
    return templates.TemplateResponse("orders.html", {"request": request, "current_user": current_admin})

@router.get("/api", response_model=List[OrderResponse])
async def get_orders(
    skip: int = 0, 
    limit: int = 10, 
    status: Optional[str] = None,
    date: Optional[date] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Получает список заказов с возможностью фильтрации"""
    query = select(Order)
    
    # Применяем фильтры, если они указаны
    if status:
        query = query.filter(Order.status == status)
    if date:
        # Фильтрация по дате (начало и конец дня)
        start_date = datetime.combine(date, datetime.min.time())
        end_date = datetime.combine(date, datetime.max.time())
        query = query.filter(and_(Order.created_at >= start_date, Order.created_at <= end_date))
    if search:
        query = query.filter(
            or_(
                Order.title.ilike(f"%{search}%"),
                Order.description.ilike(f"%{search}%"),
                Order.address.ilike(f"%{search}%")
            )
        )
    
    # Добавляем пагинацию и сортировку по убыванию даты создания
    query = query.offset(skip).limit(limit).order_by(Order.created_at.desc())
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return orders

@router.get("/{order_id}", response_class=HTMLResponse)
async def get_order_page(
    request: Request, 
    order_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Отображает страницу с детальной информацией о заказе"""
    # Получаем заказ
    query = select(Order).filter(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    # Получаем информацию о клиенте
    client_query = select(User).filter(User.id == order.client_id)
    client_result = await db.execute(client_query)
    client = client_result.scalar_one_or_none()
    
    # Получаем информацию о мастере, если он назначен
    master = None
    if order.master_id:
        master_query = select(User).filter(User.id == order.master_id)
        master_result = await db.execute(master_query)
        master = master_result.scalar_one_or_none()
    
    return templates.TemplateResponse(
        "order_detail.html", 
        {
            "request": request, 
            "order": order, 
            "client": client,
            "master": master,
            "current_user": current_admin
        }
    )

@router.get("/api/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Получает информацию о конкретном заказе"""
    query = select(Order).filter(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    return order

@router.post("/api/{order_id}/complete")
async def complete_order(
    order_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Завершает заказ"""
    query = select(Order).filter(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    if order.status not in ["new", "in_progress"]:
        raise HTTPException(status_code=400, detail="Нельзя завершить заказ в текущем статусе")
    
    order.status = "completed"
    order.completed_at = datetime.now()
    await db.commit()
    
    return {"message": "Заказ завершен"}

@router.post("/api/{order_id}/cancel")
async def cancel_order(
    order_id: int, 
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Отменяет заказ"""
    query = select(Order).filter(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    if order.status not in ["new", "in_progress"]:
        raise HTTPException(status_code=400, detail="Нельзя отменить заказ в текущем статусе")
    
    order.status = "cancelled"
    await db.commit()
    
    return {"message": "Заказ отменен"}

@router.put("/api/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int, 
    order_update: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Обновляет информацию о заказе"""
    query = select(Order).filter(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    # Обновляем только указанные поля
    update_data = order_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)
    
    await db.commit()
    await db.refresh(order)
    
    return order