#!/usr/bin/env python3
"""Quick script to check database contents."""
import asyncio
from sqlalchemy import select, text
from core.db import SessionFactory
from app.models import User, Order, Bid

async def check_db():
    async with SessionFactory() as session:
        # Проверяем таблицы
        result = await session.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        tables = result.fetchall()
        print("📊 Таблицы в БД:")
        for t in tables:
            print(f"  - {t[0]}")
        
        # Считаем записи
        from sqlalchemy import func
        user_count = await session.scalar(select(func.count(User.id)))
        order_count = await session.scalar(select(func.count(Order.id)))
        bid_count = await session.scalar(select(func.count(Bid.id)))
        
        print(f"\n📈 Статистика:")
        print(f"  Пользователей: {user_count}")
        print(f"  Заказов: {order_count}")
        print(f"  Ставок: {bid_count}")
        
        # Показываем пользователей
        users = (await session.execute(select(User))).scalars().all()
        if users:
            print(f"\n👥 Пользователи:")
            for u in users:
                print(f"  [{u.id}] @{u.tg_id} - {u.role} - {u.name}")
                if u.zones:
                    print(f"      Районы: {', '.join(u.zones)}")
        
        # Показываем последние заказы
        orders = (await session.execute(
            select(Order).order_by(Order.created_at.desc()).limit(5)
        )).scalars().all()
        if orders:
            print(f"\n📦 Последние заказы:")
            for o in orders:
                print(f"  [{o.id}] {o.category} в {o.zone} - статус: {o.status}")

if __name__ == "__main__":
    asyncio.run(check_db())