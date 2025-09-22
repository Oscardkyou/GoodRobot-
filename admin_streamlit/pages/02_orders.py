"""
Страница управления заказами.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from admin_streamlit.utils.auth import check_auth
from admin_streamlit.utils.db import (
    execute_query, execute_action, get_session, 
    insert_record, update_record, delete_record, get_record_by_id
)

# Настройка страницы
st.set_page_config(
    page_title="Заказы | GoodRobot Admin",
    page_icon="🤖",
    layout="wide",
)

# Аутентификация
if not check_auth():
    st.stop()

st.title("Управление заказами")

# Вкладки
tab1, tab2 = st.tabs(["Список заказов", "Детали заказа"])

# Вкладка "Список заказов"
with tab1:
    # Фильтры
    st.subheader("Фильтры")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Статус",
            options=["Все", "new", "in_progress", "completed", "cancelled"],
            index=0
        )
    
    with col2:
        date_range = st.date_input(
            "Период",
            value=(datetime.now() - timedelta(days=30), datetime.now()),
            max_value=datetime.now()
        )
    
    with col3:
        search_text = st.text_input("Поиск (ID, клиент, мастер)")
    
    # Формирование запроса с учетом фильтров
    query = """
    SELECT o.id, o.created_at, c.name as client_name, m.name as master_name, 
           o.status, o.price, s.name as specialty
    FROM orders o
    LEFT JOIN clients c ON o.client_id = c.id
    LEFT JOIN masters m ON o.master_id = m.id
    LEFT JOIN specialties s ON o.specialty_id = s.id
    """
    
    where_clauses = []
    params = {}
    
    if status_filter != "Все":
        where_clauses.append("o.status = :status")
        params["status"] = status_filter
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        where_clauses.append("DATE(o.created_at) BETWEEN :start_date AND :end_date")
        params["start_date"] = start_date.strftime('%Y-%m-%d')
        params["end_date"] = end_date.strftime('%Y-%m-%d')
    
    if search_text:
        where_clauses.append("(o.id::text LIKE :search OR c.name LIKE :search OR m.name LIKE :search)")
        params["search"] = f"%{search_text}%"
    
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    
    query += " ORDER BY o.created_at DESC LIMIT 100"
    
    # Получение данных
    orders_df = execute_query(query, params)
    
    # Отображение таблицы заказов
    st.subheader("Список заказов")
    
    if not orders_df.empty:
        # Форматирование данных
        orders_df['created_at'] = pd.to_datetime(orders_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Цветовая кодировка статусов
        def highlight_status(val):
            color_map = {
                'new': 'background-color: #ffeb3b',
                'in_progress': 'background-color: #2196f3',
                'completed': 'background-color: #4caf50',
                'cancelled': 'background-color: #f44336'
            }
            return color_map.get(val, '')
        
        st.dataframe(
            orders_df.style.applymap(highlight_status, subset=['status']),
            use_container_width=True
        )
        
        st.info(f"Найдено заказов: {len(orders_df)}")
    else:
        st.info("Заказы не найдены")

# Вкладка "Детали заказа"
with tab2:
    st.subheader("Детали заказа")
    
    order_id = st.number_input("ID заказа", min_value=1, step=1)
    
    if st.button("Показать детали"):
        # Информация о заказе
        order_info = execute_query(
            """
            SELECT o.*, 
                   c.name as client_name, c.phone as client_phone,
                   m.name as master_name, m.phone as master_phone,
                   s.name as specialty_name
            FROM orders o
            LEFT JOIN clients c ON o.client_id = c.id
            LEFT JOIN masters m ON o.master_id = m.id
            LEFT JOIN specialties s ON o.specialty_id = s.id
            WHERE o.id = :id
            """,
            {"id": order_id}
        )
        
        if not order_info.empty:
            order_data = order_info.iloc[0]
            
            # Основная информация о заказе
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("### Информация о заказе")
                st.write(f"**ID:** {order_data['id']}")
                st.write(f"**Дата создания:** {pd.to_datetime(order_data['created_at']).strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**Статус:** {order_data['status']}")
                st.write(f"**Цена:** {order_data['price']} руб.")
                st.write(f"**Специальность:** {order_data['specialty_name']}")
                
                # Форма изменения статуса
                st.write("### Изменить статус")
                new_status = st.selectbox(
                    "Новый статус",
                    options=["new", "in_progress", "completed", "cancelled"],
                    index=["new", "in_progress", "completed", "cancelled"].index(order_data['status']) if order_data['status'] in ["new", "in_progress", "completed", "cancelled"] else 0
                )
                
                if st.button("Обновить статус"):
                    success = update_record(
                        "orders", 
                        {"status": new_status}, 
                        f"id = {order_id}"
                    )
                    
                    if success:
                        st.success(f"Статус заказа успешно изменен на '{new_status}'")
                        # Перезагружаем страницу для обновления данных
                        st.experimental_rerun()
                    else:
                        st.error("Ошибка при обновлении статуса заказа")
            
            with col2:
                st.write("### Информация о клиенте")
                st.write(f"**Имя:** {order_data['client_name']}")
                st.write(f"**Телефон:** {order_data['client_phone']}")
                
                st.write("### Информация о мастере")
                if order_data['master_name']:
                    st.write(f"**Имя:** {order_data['master_name']}")
                    st.write(f"**Телефон:** {order_data['master_phone']}")
                else:
                    st.info("Мастер не назначен")
            
            # Детали заказа
            st.write("### Детали заказа")
            st.json({
                "id": int(order_data['id']),
                "client_id": int(order_data['client_id']),
                "master_id": int(order_data['master_id']) if order_data['master_id'] else None,
                "specialty_id": int(order_data['specialty_id']),
                "status": order_data['status'],
                "price": float(order_data['price']),
                "created_at": pd.to_datetime(order_data['created_at']).strftime('%Y-%m-%d %H:%M:%S'),
                "description": order_data['description'] if 'description' in order_data else None,
                "address": order_data['address'] if 'address' in order_data else None
            })
            
            # История изменений (если есть такая таблица)
            try:
                history = execute_query(
                    """
                    SELECT * FROM order_history
                    WHERE order_id = :order_id
                    ORDER BY created_at DESC
                    """,
                    {"order_id": order_id}
                )
                
                if not history.empty:
                    st.write("### История изменений")
                    st.dataframe(history)
            except:
                pass  # Если таблицы нет, просто пропускаем
        else:
            st.error("Заказ не найден")
