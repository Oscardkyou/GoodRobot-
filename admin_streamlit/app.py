"""
Главный файл Streamlit админ-панели GoodRobot.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from admin_streamlit.utils.auth import check_auth
from admin_streamlit.utils.db import execute_query

# Настройка страницы
st.set_page_config(
    page_title="GoodRobot Admin",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Аутентификация
if not check_auth():
    st.stop()

# Главная страница админки
st.title("GoodRobot Admin Panel")
st.write("Добро пожаловать в админ-панель GoodRobot!")

# Статистика
st.header("Общая статистика")

# Утилита безопасного чтения одного скалярного значения из запроса
def scalar_query(query: str, params: dict | None, column: str, default=0):
    try:
        df = execute_query(query, params) if params is not None else execute_query(query)
        if df.empty or column not in df.columns:
            return default
        val = df.iloc[0][column]
        if pd.isna(val):
            return default
        return val
    except Exception:
        return default
col1, col2, col3, col4 = st.columns(4)

try:
    # Количество мастеров
    masters_count = scalar_query("SELECT COUNT(*) as count FROM masters", None, 'count', 0)
    col1.metric("Мастера", masters_count)
    
    # Количество заказов
    orders_count = scalar_query("SELECT COUNT(*) as count FROM orders", None, 'count', 0)
    col2.metric("Заказы", orders_count)
    
    # Количество клиентов
    clients_count = scalar_query("SELECT COUNT(*) as count FROM clients", None, 'count', 0)
    col3.metric("Клиенты", clients_count)
    
    # Количество специальностей
    specialties_count = scalar_query("SELECT COUNT(*) as count FROM specialties", None, 'count', 0)
    col4.metric("Специальности", specialties_count)
    
    # График заказов по дням
    st.header("Заказы по дням")
    
    # Получаем данные за последние 30 дней
    orders_by_day = execute_query(
        """
        SELECT DATE(created_at) as date, COUNT(*) as count 
        FROM orders 
        WHERE created_at >= :start_date
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        """,
        {"start_date": (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}
    )
    
    if not orders_by_day.empty:
        st.bar_chart(orders_by_day.set_index('date'))
    else:
        st.info("Нет данных о заказах за последние 30 дней")
    
    # Последние заказы
    st.header("Последние заказы")
    recent_orders = execute_query(
        """
        SELECT o.id, o.created_at, c.name as client_name, m.name as master_name, o.status, o.price
        FROM orders o
        LEFT JOIN clients c ON o.client_id = c.id
        LEFT JOIN masters m ON o.master_id = m.id
        ORDER BY o.created_at DESC
        LIMIT 10
        """
    )
    
    if not recent_orders.empty:
        st.dataframe(recent_orders, use_container_width=True)
    else:
        st.info("Нет данных о заказах")
    
except Exception as e:
    st.error(f"Ошибка при получении данных: {e}")

# Сайдбар с навигацией
st.sidebar.title("Навигация")
st.sidebar.info(
    """
    Используйте меню выше для навигации по разделам админки.
    
    **Доступные разделы:**
    - Главная (текущая страница)
    - Мастера
    - Заказы
    - Клиенты
    - Специальности
    - Аналитика
    """
)

# Информация о версии
st.sidebar.markdown("---")
st.sidebar.info(
    """
    **GoodRobot Admin Panel**
    
    Версия: 1.0.0
    
    © 2025 GoodRobot
    """
)
