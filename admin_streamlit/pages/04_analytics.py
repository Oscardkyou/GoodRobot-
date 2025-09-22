"""
Страница аналитики.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from admin_streamlit.utils.auth import check_auth
from admin_streamlit.utils.db import execute_query

# Настройка страницы
st.set_page_config(
    page_title="Аналитика | GoodRobot Admin",
    page_icon="🤖",
    layout="wide",
)

# Аутентификация
if not check_auth():
    st.stop()

st.title("Аналитика")

# Выбор периода
st.sidebar.header("Настройки")
date_range = st.sidebar.date_input(
    "Период",
    value=(datetime.now() - timedelta(days=30), datetime.now()),
    max_value=datetime.now()
)

if len(date_range) == 2:
    start_date, end_date = date_range
    date_filter = {
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d')
    }
else:
    date_filter = {
        "start_date": (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        "end_date": datetime.now().strftime('%Y-%m-%d')
    }

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

# Вкладки аналитики
tab1, tab2, tab3, tab4 = st.tabs(["Заказы", "Мастера", "Клиенты", "Специальности"])

# Вкладка "Заказы"
with tab1:
    st.header("Аналитика заказов")
    
    # Метрики заказов
    col1, col2, col3, col4 = st.columns(4)
    
    # Общее количество заказов
    total_orders = scalar_query(
        """
        SELECT COUNT(*) as count
        FROM orders
        WHERE DATE(created_at) BETWEEN :start_date AND :end_date
        """,
        date_filter,
        'count', 0
    )
    
    col1.metric("Всего заказов", total_orders)
    
    # Завершенные заказы
    completed_orders = scalar_query(
        """
        SELECT COUNT(*) as count
        FROM orders
        WHERE status = 'completed' AND DATE(created_at) BETWEEN :start_date AND :end_date
        """,
        date_filter,
        'count', 0
    )
    
    col2.metric("Завершено", completed_orders)
    
    # Отмененные заказы
    cancelled_orders = scalar_query(
        """
        SELECT COUNT(*) as count
        FROM orders
        WHERE status = 'cancelled' AND DATE(created_at) BETWEEN :start_date AND :end_date
        """,
        date_filter,
        'count', 0
    )
    
    col3.metric("Отменено", cancelled_orders)
    
    # Средняя стоимость заказа
    avg_price = scalar_query(
        """
        SELECT AVG(price) as avg_price
        FROM orders
        WHERE DATE(created_at) BETWEEN :start_date AND :end_date
        """,
        date_filter,
        'avg_price', 0
    )
    col4.metric("Средняя стоимость", f"{int(avg_price)} руб.")
    
    # График заказов по дням
    orders_by_day = execute_query(
        """
        SELECT DATE(created_at) as date, COUNT(*) as count 
        FROM orders 
        WHERE DATE(created_at) BETWEEN :start_date AND :end_date
        GROUP BY DATE(created_at)
        ORDER BY date
        """,
        date_filter
    )
    
    if not orders_by_day.empty:
        st.subheader("Динамика заказов")
        fig = px.line(
            orders_by_day, 
            x='date', 
            y='count',
            title='Количество заказов по дням',
            labels={'date': 'Дата', 'count': 'Количество заказов'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # График заказов по статусам
    orders_by_status = execute_query(
        """
        SELECT status, COUNT(*) as count 
        FROM orders 
        WHERE DATE(created_at) BETWEEN :start_date AND :end_date
        GROUP BY status
        ORDER BY count DESC
        """,
        date_filter
    )
    
    if not orders_by_status.empty:
        st.subheader("Заказы по статусам")
        fig = px.pie(
            orders_by_status, 
            values='count', 
            names='status',
            title='Распределение заказов по статусам',
            color='status',
            color_discrete_map={
                'new': '#ffeb3b',
                'in_progress': '#2196f3',
                'completed': '#4caf50',
                'cancelled': '#f44336'
            }
        )
        st.plotly_chart(fig, use_container_width=True)

# Вкладка "Мастера"
with tab2:
    st.header("Аналитика мастеров")
    
    # Метрики мастеров
    col1, col2, col3 = st.columns(3)
    
    # Общее количество мастеров
    total_masters = scalar_query(
        """
        SELECT COUNT(*) as count
        FROM masters
        """,
        None,
        'count', 0
    )
    
    col1.metric("Всего мастеров", total_masters)
    
    # Активные мастера (выполнившие хотя бы один заказ в выбранный период)
    active_masters = scalar_query(
        """
        SELECT COUNT(DISTINCT master_id) as count
        FROM orders
        WHERE master_id IS NOT NULL 
          AND status = 'completed'
          AND DATE(created_at) BETWEEN :start_date AND :end_date
        """,
        date_filter,
        'count', 0
    )
    
    col2.metric("Активные мастера", active_masters)
    
    # Средний рейтинг мастеров
    avg_rating = scalar_query(
        """
        SELECT AVG(rating) as avg_rating
        FROM masters
        """,
        None,
        'avg_rating', 0
    )
    col3.metric("Средний рейтинг", f"{float(avg_rating):.1f}")
    
    # Топ мастеров по количеству заказов
    top_masters = execute_query(
        """
        SELECT m.id, m.name, COUNT(o.id) as orders_count, AVG(o.price) as avg_price
        FROM masters m
        JOIN orders o ON m.id = o.master_id
        WHERE DATE(o.created_at) BETWEEN :start_date AND :end_date
          AND o.status = 'completed'
        GROUP BY m.id, m.name
        ORDER BY orders_count DESC
        LIMIT 10
        """,
        date_filter
    )
    
    if not top_masters.empty:
        st.subheader("Топ мастеров по количеству заказов")
        
        # Форматирование средней цены
        top_masters['avg_price'] = top_masters['avg_price'].round(0).astype(int)
        
        fig = px.bar(
            top_masters, 
            x='name', 
            y='orders_count',
            title='Топ-10 мастеров по количеству заказов',
            labels={'name': 'Мастер', 'orders_count': 'Количество заказов'},
            text='orders_count'
        )
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            top_masters.rename(columns={
                'name': 'Имя', 
                'orders_count': 'Кол-во заказов', 
                'avg_price': 'Средняя цена (руб.)'
            }),
            use_container_width=True
        )

# Вкладка "Клиенты"
with tab3:
    st.header("Аналитика клиентов")
    
    # Метрики клиентов
    col1, col2, col3 = st.columns(3)
    
    # Общее количество клиентов
    total_clients = scalar_query(
        """
        SELECT COUNT(*) as count
        FROM clients
        """,
        None,
        'count', 0
    )
    
    col1.metric("Всего клиентов", total_clients)
    
    # Новые клиенты за период
    new_clients = scalar_query(
        """
        SELECT COUNT(*) as count
        FROM clients
        WHERE DATE(created_at) BETWEEN :start_date AND :end_date
        """,
        date_filter,
        'count', 0
    )
    
    col2.metric("Новые клиенты", new_clients)
    
    # Активные клиенты (сделавшие хотя бы один заказ в выбранный период)
    active_clients = scalar_query(
        """
        SELECT COUNT(DISTINCT client_id) as count
        FROM orders
        WHERE DATE(created_at) BETWEEN :start_date AND :end_date
        """,
        date_filter,
        'count', 0
    )
    
    col3.metric("Активные клиенты", active_clients)
    
    # Топ клиентов по количеству заказов
    top_clients = execute_query(
        """
        SELECT c.id, c.name, COUNT(o.id) as orders_count, SUM(o.price) as total_spent
        FROM clients c
        JOIN orders o ON c.id = o.client_id
        WHERE DATE(o.created_at) BETWEEN :start_date AND :end_date
        GROUP BY c.id, c.name
        ORDER BY orders_count DESC
        LIMIT 10
        """,
        date_filter
    )
    
    if not top_clients.empty:
        st.subheader("Топ клиентов по количеству заказов")
        
        # Форматирование общих расходов
        top_clients['total_spent'] = top_clients['total_spent'].round(0).astype(int)
        
        fig = px.bar(
            top_clients, 
            x='name', 
            y='orders_count',
            title='Топ-10 клиентов по количеству заказов',
            labels={'name': 'Клиент', 'orders_count': 'Количество заказов'},
            text='orders_count'
        )
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            top_clients.rename(columns={
                'name': 'Имя', 
                'orders_count': 'Кол-во заказов', 
                'total_spent': 'Общие расходы (руб.)'
            }),
            use_container_width=True
        )

# Вкладка "Специальности"
with tab4:
    st.header("Аналитика специальностей")
    
    # Популярные специальности
    popular_specialties = execute_query(
        """
        SELECT s.id, s.name, COUNT(o.id) as orders_count, AVG(o.price) as avg_price
        FROM specialties s
        JOIN orders o ON s.id = o.specialty_id
        WHERE DATE(o.created_at) BETWEEN :start_date AND :end_date
        GROUP BY s.id, s.name
        ORDER BY orders_count DESC
        """,
        date_filter
    )
    
    if not popular_specialties.empty:
        st.subheader("Популярные специальности")
        
        # Форматирование средней цены
        popular_specialties['avg_price'] = popular_specialties['avg_price'].round(0).astype(int)
        
        fig = px.bar(
            popular_specialties.head(10), 
            x='name', 
            y='orders_count',
            title='Топ-10 специальностей по количеству заказов',
            labels={'name': 'Специальность', 'orders_count': 'Количество заказов'},
            text='orders_count'
        )
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        # График средней стоимости заказа по специальностям
        fig = px.bar(
            popular_specialties.head(10), 
            x='name', 
            y='avg_price',
            title='Средняя стоимость заказа по специальностям',
            labels={'name': 'Специальность', 'avg_price': 'Средняя стоимость (руб.)'},
            text='avg_price'
        )
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            popular_specialties.rename(columns={
                'name': 'Специальность', 
                'orders_count': 'Кол-во заказов', 
                'avg_price': 'Средняя цена (руб.)'
            }),
            use_container_width=True
        )
    
    # Количество мастеров по специальностям
    masters_by_specialty = execute_query(
        """
        SELECT s.id, s.name, COUNT(ms.master_id) as masters_count
        FROM specialties s
        LEFT JOIN master_specialties ms ON s.id = ms.specialty_id
        GROUP BY s.id, s.name
        ORDER BY masters_count DESC
        """
    )
    
    if not masters_by_specialty.empty:
        st.subheader("Количество мастеров по специальностям")
        
        fig = px.bar(
            masters_by_specialty.head(10), 
            x='name', 
            y='masters_count',
            title='Топ-10 специальностей по количеству мастеров',
            labels={'name': 'Специальность', 'masters_count': 'Количество мастеров'},
            text='masters_count'
        )
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
