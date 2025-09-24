from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from admin.app.auth import get_current_admin
from admin.app.database import get_db
from admin.app.schemas import BidResponse, BidUpdate
from app.models.bid import Bid
from app.models.order import Order
from app.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")

@router.get("/", response_class=HTMLResponse)
async def get_bids_page(request: Request, current_admin=Depends(get_current_admin)):
    """Отображает страницу со списком ставок"""
    return templates.TemplateResponse("bids.html", {"request": request, "current_user": current_admin})

@router.get("/api", response_model=list[BidResponse])
async def get_bids(
    skip: int = 0,
    limit: int = 10,
    order_id: int | None = None,
    master_id: int | None = None,
    date: date | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Получает список ставок с возможностью фильтрации"""
    query = select(Bid)

    # Применяем фильтры, если они указаны
    if order_id:
        query = query.filter(Bid.order_id == order_id)
    if master_id:
        query = query.filter(Bid.master_id == master_id)
    if status:
        query = query.filter(Bid.status == status)
    if date:
        # Фильтрация по дате (начало и конец дня)
        start_date = datetime.combine(date, datetime.min.time())
        end_date = datetime.combine(date, datetime.max.time())
        query = query.filter(and_(Bid.created_at >= start_date, Bid.created_at <= end_date))

    # Добавляем пагинацию и сортировку по убыванию даты создания
    query = query.offset(skip).limit(limit).order_by(Bid.created_at.desc())

    result = await db.execute(query)
    bids = result.scalars().all()

    return bids

@router.get("/{bid_id}", response_class=HTMLResponse)
async def get_bid_page(
    request: Request,
    bid_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Отображает страницу с детальной информацией о ставке"""
    # Получаем ставку
    query = select(Bid).filter(Bid.id == bid_id)
    result = await db.execute(query)
    bid = result.scalar_one_or_none()

    if not bid:
        raise HTTPException(status_code=404, detail="Ставка не найдена")

    # Получаем информацию о заказе
    order_query = select(Order).filter(Order.id == bid.order_id)
    order_result = await db.execute(order_query)
    order = order_result.scalar_one_or_none()

    # Получаем информацию о мастере
    master_query = select(User).filter(User.id == bid.master_id)
    master_result = await db.execute(master_query)
    master = master_result.scalar_one_or_none()

    return templates.TemplateResponse(
        "bid_detail.html",
        {
            "request": request,
            "bid": bid,
            "order": order,
            "master": master,
            "current_user": current_admin
        }
    )

@router.get("/api/{bid_id}", response_model=BidResponse)
async def get_bid(
    bid_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Получает информацию о конкретной ставке"""
    query = select(Bid).filter(Bid.id == bid_id)
    result = await db.execute(query)
    bid = result.scalar_one_or_none()

    if not bid:
        raise HTTPException(status_code=404, detail="Ставка не найдена")

    return bid

@router.post("/api/{bid_id}/accept")
async def accept_bid(
    bid_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Принимает ставку и назначает мастера на заказ"""
    # Получаем ставку
    query = select(Bid).filter(Bid.id == bid_id)
    result = await db.execute(query)
    bid = result.scalar_one_or_none()

    if not bid:
        raise HTTPException(status_code=404, detail="Ставка не найдена")

    if bid.status != "pending":
        raise HTTPException(status_code=400, detail="Нельзя принять ставку в текущем статусе")

    # Получаем заказ
    order_query = select(Order).filter(Order.id == bid.order_id)
    order_result = await db.execute(order_query)
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    if order.status != "new":
        raise HTTPException(status_code=400, detail="Нельзя принять ставку для заказа в текущем статусе")

    # Обновляем статус ставки
    bid.status = "accepted"

    # Обновляем заказ - назначаем мастера и меняем статус
    order.master_id = bid.master_id
    order.status = "in_progress"
    order.price = bid.amount

    # Отклоняем все остальные ставки на этот заказ
    other_bids_query = select(Bid).filter(and_(Bid.order_id == bid.order_id, Bid.id != bid.id))
    other_bids_result = await db.execute(other_bids_query)
    other_bids = other_bids_result.scalars().all()

    for other_bid in other_bids:
        other_bid.status = "rejected"

    await db.commit()

    return {"message": "Ставка принята, мастер назначен на заказ"}

@router.post("/api/{bid_id}/reject")
async def reject_bid(
    bid_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Отклоняет ставку"""
    query = select(Bid).filter(Bid.id == bid_id)
    result = await db.execute(query)
    bid = result.scalar_one_or_none()

    if not bid:
        raise HTTPException(status_code=404, detail="Ставка не найдена")

    if bid.status != "pending":
        raise HTTPException(status_code=400, detail="Нельзя отклонить ставку в текущем статусе")

    bid.status = "rejected"
    await db.commit()

    return {"message": "Ставка отклонена"}

@router.put("/api/{bid_id}", response_model=BidResponse)
async def update_bid(
    bid_id: int,
    bid_update: BidUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    """Обновляет информацию о ставке"""
    query = select(Bid).filter(Bid.id == bid_id)
    result = await db.execute(query)
    bid = result.scalar_one_or_none()

    if not bid:
        raise HTTPException(status_code=404, detail="Ставка не найдена")

    # Обновляем только указанные поля
    update_data = bid_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(bid, key, value)

    await db.commit()
    await db.refresh(bid)

    return bid
