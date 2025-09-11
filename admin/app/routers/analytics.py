import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.app.auth import get_current_admin
from admin.app.database import get_db
from app.models.bid import Bid
from app.models.order import Order
from app.models.payout import Payout
from app.models.user import User

router = APIRouter()

# API эндпоинты для аналитики
@router.get("/api/statistics")
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Получение основной статистики: пользователи, заказы, средний чек."""
    # Общее количество пользователей
    total_users_query = select(func.count()).select_from(User)
    total_users = await db.execute(total_users_query)
    total_users = total_users.scalar() or 0

    # Общее количество заказов
    total_orders_query = select(func.count()).select_from(Order)
    total_orders = await db.execute(total_orders_query)
    total_orders = total_orders.scalar() or 0

    # Количество активных заказов
    active_orders_query = select(func.count()).select_from(Order).where(
        Order.status.in_(["new", "in_progress"])
    )
    active_orders = await db.execute(active_orders_query)
    active_orders = active_orders.scalar() or 0

    # Средний чек
    avg_price_query = select(func.avg(Order.price)).select_from(Order)
    avg_price = await db.execute(avg_price_query)
    avg_price = avg_price.scalar() or 0

    # Распределение пользователей по ролям
    users_by_role_query = select(
        User.role, func.count().label("count")
    ).group_by(User.role)
    users_by_role = await db.execute(users_by_role_query)
    users_by_role = [{"role": role, "count": count} for role, count in users_by_role]

    return {
        "total_users": total_users,
        "total_orders": total_orders,
        "active_orders": active_orders,
        "average_order_price": float(avg_price),
        "users_by_role": users_by_role
    }

@router.get("/api/user-growth")
async def get_user_growth(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Получение данных о росте числа пользователей за указанный период."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Запрос для получения количества новых пользователей по дням
    query = select(
        func.date(User.created_at).label("date"),
        func.count().label("count")
    ).where(
        User.created_at >= start_date,
        User.created_at <= end_date
    ).group_by(
        func.date(User.created_at)
    ).order_by(
        func.date(User.created_at)
    )

    result = await db.execute(query)
    user_growth = [{"date": date.strftime("%Y-%m-%d"), "count": count} for date, count in result]

    return user_growth

@router.get("/api/order-statistics")
async def get_order_statistics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Получение статистики заказов: количество по дням и распределение по статусам."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Запрос для получения количества заказов по дням
    daily_query = select(
        func.date(Order.created_at).label("date"),
        func.count().label("count")
    ).where(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).group_by(
        func.date(Order.created_at)
    ).order_by(
        func.date(Order.created_at)
    )

    daily_result = await db.execute(daily_query)
    daily_orders = [{"date": date.strftime("%Y-%m-%d"), "count": count} for date, count in daily_result]

    # Запрос для получения распределения заказов по статусам
    status_query = select(
        Order.status,
        func.count().label("count")
    ).group_by(
        Order.status
    )

    status_result = await db.execute(status_query)
    status_statistics = [{"status": status, "count": count} for status, count in status_result]

    return {
        "daily_orders": daily_orders,
        "status_statistics": status_statistics
    }

@router.get("/api/bid-statistics")
async def get_bid_statistics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Получение статистики ставок: распределение по статусам и топ мастеров."""
    # Запрос для получения распределения ставок по статусам
    status_query = select(
        Bid.status,
        func.count().label("count")
    ).group_by(
        Bid.status
    )

    status_result = await db.execute(status_query)
    status_statistics = [{"status": status, "count": count} for status, count in status_result]

    # Запрос для получения топ-5 мастеров по количеству принятых ставок
    top_masters_query = select(
        User.id,
        User.name,
        func.count().label("accepted_bids")
    ).join(
        Bid, User.id == Bid.master_id
    ).where(
        Bid.status == "accepted"
    ).group_by(
        User.id, User.name
    ).order_by(
        desc("accepted_bids")
    ).limit(5)

    top_masters_result = await db.execute(top_masters_query)
    top_masters = [
        {"id": id, "name": name, "accepted_bids": accepted_bids}
        for id, name, accepted_bids in top_masters_result
    ]

    return {
        "status_statistics": status_statistics,
        "top_masters": top_masters
    }

@router.get("/api/payout-statistics")
async def get_payout_statistics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Получение статистики выплат: распределение по статусам и суммы по дням."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Запрос для получения распределения выплат по статусам
    status_query = select(
        Payout.status,
        func.count().label("count")
    ).group_by(
        Payout.status
    )

    status_result = await db.execute(status_query)
    status_statistics = [{"status": status, "count": count} for status, count in status_result]

    # Запрос для получения сумм выплат по дням
    amount_query = select(
        func.date(Payout.created_at).label("date"),
        func.sum(Payout.amount).label("amount")
    ).where(
        Payout.created_at >= start_date,
        Payout.created_at <= end_date
    ).group_by(
        func.date(Payout.created_at)
    ).order_by(
        func.date(Payout.created_at)
    )

    amount_result = await db.execute(amount_query)
    amount_statistics = [
        {"date": date.strftime("%Y-%m-%d"), "amount": float(amount)}
        for date, amount in amount_result
    ]

    return {
        "status_statistics": status_statistics,
        "amount_statistics": amount_statistics
    }

@router.get("/api/revenue-statistics")
async def get_revenue_statistics(
    period: str = Query("month", regex="^(month|quarter|year)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Получение статистики доходов и расходов за указанный период."""
    end_date = datetime.now()

    # Определение начальной даты в зависимости от периода
    if period == "month":
        start_date = end_date - timedelta(days=30)
        group_by = func.date(Order.created_at)
    elif period == "quarter":
        start_date = end_date - timedelta(days=90)
        group_by = func.date_trunc('week', Order.created_at)
    else:  # year
        start_date = end_date - timedelta(days=365)
        group_by = func.date_trunc('month', Order.created_at)

    # Запрос для получения доходов (суммы заказов) по периодам
    revenue_query = select(
        group_by.label("date"),
        func.sum(Order.price).label("revenue")
    ).where(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).group_by(
        group_by
    ).order_by(
        group_by
    )

    revenue_result = await db.execute(revenue_query)
    revenue_data = {date: float(revenue) for date, revenue in revenue_result}

    # Запрос для получения расходов (суммы выплат) по периодам
    expenses_query = select(
        func.date_trunc(
            'day' if period == "month" else 'week' if period == "quarter" else 'month',
            Payout.created_at
        ).label("date"),
        func.sum(Payout.amount).label("expenses")
    ).where(
        Payout.created_at >= start_date,
        Payout.created_at <= end_date,
        Payout.status == "approved"
    ).group_by(
        func.date_trunc(
            'day' if period == "month" else 'week' if period == "quarter" else 'month',
            Payout.created_at
        )
    ).order_by(
        func.date_trunc(
            'day' if period == "month" else 'week' if period == "quarter" else 'month',
            Payout.created_at
        )
    )

    expenses_result = await db.execute(expenses_query)
    expenses_data = {date: float(expenses) for date, expenses in expenses_result}

    # Объединение данных
    all_dates = sorted(set(list(revenue_data.keys()) + list(expenses_data.keys())))

    combined_data = []
    total_revenue = 0
    total_expenses = 0

    for date in all_dates:
        revenue = revenue_data.get(date, 0)
        expenses = expenses_data.get(date, 0)
        profit = revenue - expenses

        total_revenue += revenue
        total_expenses += expenses

        date_str = date.strftime("%Y-%m-%d") if isinstance(date, datetime) else date.strftime("%Y-%m-%d")

        combined_data.append({
            "date": date_str,
            "revenue": revenue,
            "expenses": expenses,
            "profit": profit
        })

    total_profit = total_revenue - total_expenses

    return {
        "revenue_data": combined_data,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "total_profit": total_profit
    }

@router.get("/api/export")
async def export_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Экспорт аналитических данных в CSV формате."""
    # Получаем основную статистику
    stats = await get_statistics(db, current_user)

    # Получаем статистику заказов
    order_stats = await get_order_statistics(days=30, db=db, current_user=current_user)

    # Получаем статистику ставок
    bid_stats = await get_bid_statistics(days=30, db=db, current_user=current_user)

    # Получаем статистику выплат
    payout_stats = await get_payout_statistics(days=30, db=db, current_user=current_user)

    # Получаем статистику доходов и расходов
    revenue_stats = await get_revenue_statistics(period="month", db=db, current_user=current_user)

    # Создаем CSV файл в памяти
    output = io.StringIO()
    writer = csv.writer(output)

    # Записываем заголовок и дату экспорта
    writer.writerow(["Аналитический отчет GoodRobot"])
    writer.writerow(["Дата экспорта:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])

    # Записываем основную статистику
    writer.writerow(["Основная статистика"])
    writer.writerow(["Всего пользователей:", stats["total_users"]])
    writer.writerow(["Всего заказов:", stats["total_orders"]])
    writer.writerow(["Активных заказов:", stats["active_orders"]])
    writer.writerow(["Средний чек:", stats["average_order_price"]])
    writer.writerow([])

    # Записываем распределение пользователей по ролям
    writer.writerow(["Распределение пользователей по ролям"])
    writer.writerow(["Роль", "Количество"])
    for role_data in stats["users_by_role"]:
        writer.writerow([role_data["role"], role_data["count"]])
    writer.writerow([])

    # Записываем статистику заказов по статусам
    writer.writerow(["Статистика заказов по статусам"])
    writer.writerow(["Статус", "Количество"])
    for status_data in order_stats["status_statistics"]:
        writer.writerow([status_data["status"], status_data["count"]])
    writer.writerow([])

    # Записываем статистику ставок по статусам
    writer.writerow(["Статистика ставок по статусам"])
    writer.writerow(["Статус", "Количество"])
    for status_data in bid_stats["status_statistics"]:
        writer.writerow([status_data["status"], status_data["count"]])
    writer.writerow([])

    # Записываем топ мастеров
    writer.writerow(["Топ мастеров по принятым ставкам"])
    writer.writerow(["ID", "Имя", "Количество принятых ставок"])
    for master in bid_stats["top_masters"]:
        writer.writerow([master["id"], master["name"], master["accepted_bids"]])
    writer.writerow([])

    # Записываем статистику выплат по статусам
    writer.writerow(["Статистика выплат по статусам"])
    writer.writerow(["Статус", "Количество"])
    for status_data in payout_stats["status_statistics"]:
        writer.writerow([status_data["status"], status_data["count"]])
    writer.writerow([])

    # Записываем статистику доходов и расходов
    writer.writerow(["Доходы и расходы"])
    writer.writerow(["Общий доход:", revenue_stats["total_revenue"]])
    writer.writerow(["Общие расходы:", revenue_stats["total_expenses"]])
    writer.writerow(["Общая прибыль:", revenue_stats["total_profit"]])
    writer.writerow([])

    writer.writerow(["Детализация доходов и расходов по дням"])
    writer.writerow(["Дата", "Доход", "Расходы", "Прибыль"])
    for data in revenue_stats["revenue_data"]:
        writer.writerow([
            data["date"],
            data["revenue"],
            data["expenses"],
            data["profit"]
        ])

    # Возвращаем CSV файл
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics_export.csv"}
    )

# HTML эндпоинт для страницы аналитики
@router.get("")
async def analytics_page(current_user: User = Depends(get_current_admin)):
    """Страница аналитики."""
    return {"current_user": current_user}
