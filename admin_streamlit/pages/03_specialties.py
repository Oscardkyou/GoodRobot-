"""
Страница управления специальностями.
"""
import streamlit as st
import pandas as pd
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
    page_title="Специальности | GoodRobot Admin",
    page_icon="🤖",
    layout="wide",
)

# Аутентификация
if not check_auth():
    st.stop()

st.title("Управление специальностями")

# Разделение на две колонки
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Список специальностей")
    
    # Получение списка специальностей
    specialties_df = execute_query(
        """
        SELECT s.id, s.name, s.description, c.name as category_name,
               COUNT(DISTINCT ms.master_id) as masters_count,
               COUNT(DISTINCT o.id) as orders_count
        FROM specialties s
        LEFT JOIN categories c ON s.category_id = c.id
        LEFT JOIN master_specialties ms ON s.id = ms.specialty_id
        LEFT JOIN orders o ON s.id = o.specialty_id
        GROUP BY s.id, s.name, s.description, c.name
        ORDER BY s.name
        """
    )
    
    # Отображение таблицы специальностей
    if not specialties_df.empty:
        st.dataframe(specialties_df, use_container_width=True)
    else:
        st.info("Специальности не найдены")
    
    # Детальная информация о специальности
    st.subheader("Детальная информация")
    
    specialty_id = st.number_input("ID специальности", min_value=1, step=1)
    
    if st.button("Показать детали", key="show_details"):
        # Информация о специальности
        specialty_info = execute_query(
            """
            SELECT s.*, c.name as category_name
            FROM specialties s
            LEFT JOIN categories c ON s.category_id = c.id
            WHERE s.id = :id
            """,
            {"id": specialty_id}
        )
        
        if not specialty_info.empty:
            specialty_data = specialty_info.iloc[0]
            
            st.write("### Основная информация")
            st.write(f"**ID:** {specialty_data['id']}")
            st.write(f"**Название:** {specialty_data['name']}")
            st.write(f"**Описание:** {specialty_data['description'] if 'description' in specialty_data and specialty_data['description'] else 'Нет описания'}")
            st.write(f"**Категория:** {specialty_data['category_name'] if 'category_name' in specialty_data and specialty_data['category_name'] else 'Нет категории'}")
            
            # Мастера с этой специальностью
            masters = execute_query(
                """
                SELECT m.id, m.name, m.phone, m.rating
                FROM masters m
                JOIN master_specialties ms ON m.id = ms.master_id
                WHERE ms.specialty_id = :specialty_id
                ORDER BY m.name
                """,
                {"specialty_id": specialty_id}
            )
            
            st.write("### Мастера с этой специальностью")
            if not masters.empty:
                st.dataframe(masters)
            else:
                st.info("Нет мастеров с этой специальностью")
            
            # Заказы по этой специальности
            orders = execute_query(
                """
                SELECT o.id, o.created_at, o.status, o.price,
                       c.name as client_name, m.name as master_name
                FROM orders o
                LEFT JOIN clients c ON o.client_id = c.id
                LEFT JOIN masters m ON o.master_id = m.id
                WHERE o.specialty_id = :specialty_id
                ORDER BY o.created_at DESC
                LIMIT 10
                """,
                {"specialty_id": specialty_id}
            )
            
            st.write("### Последние заказы по этой специальности")
            if not orders.empty:
                # Форматирование даты
                orders['created_at'] = pd.to_datetime(orders['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                st.dataframe(orders)
            else:
                st.info("Нет заказов по этой специальности")
        else:
            st.error("Специальность не найдена")

with col2:
    st.subheader("Добавление специальности")
    
    with st.form("add_specialty_form"):
        name = st.text_input("Название")
        description = st.text_area("Описание")
        
        # Получение списка категорий
        categories = execute_query("SELECT id, name FROM categories ORDER BY name")
        
        if not categories.empty:
            category_options = [(0, "Нет категории")] + [(row['id'], row['name']) for _, row in categories.iterrows()]
            category_id = st.selectbox(
                "Категория",
                options=category_options,
                format_func=lambda x: x[1]
            )[0]
        else:
            category_id = None
            st.info("Нет доступных категорий")
        
        submitted = st.form_submit_button("Добавить")
        
        if submitted:
            if name:
                # Подготовка данных для добавления
                specialty_data = {
                    "name": name,
                    "description": description,
                    "category_id": category_id if category_id and category_id > 0 else None
                }
                
                # Добавление специальности
                success = insert_record("specialties", specialty_data)
                
                if success:
                    st.success(f"Специальность '{name}' успешно добавлена")
                    # Очистка формы
                    st.experimental_rerun()
                else:
                    st.error("Ошибка при добавлении специальности")
            else:
                st.error("Название специальности обязательно")
    
    st.subheader("Редактирование специальности")
    
    edit_specialty_id = st.number_input("ID специальности для редактирования", min_value=1, step=1, key="edit_specialty_id")
    
    if st.button("Загрузить данные", key="load_data"):
        specialty_data = execute_query(
            """
            SELECT * FROM specialties WHERE id = :id
            """,
            {"id": edit_specialty_id}
        )
        
        if not specialty_data.empty:
            st.session_state.specialty_data = specialty_data.iloc[0].to_dict()
        else:
            st.error("Специальность не найдена")
    
    if "specialty_data" in st.session_state:
        with st.form("edit_specialty_form"):
            edit_name = st.text_input("Название", value=st.session_state.specialty_data.get("name", ""))
            edit_description = st.text_area("Описание", value=st.session_state.specialty_data.get("description", ""))
            
            # Получение списка категорий
            categories = execute_query("SELECT id, name FROM categories ORDER BY name")
            
            if not categories.empty:
                category_options = [(0, "Нет категории")] + [(row['id'], row['name']) for _, row in categories.iterrows()]
                current_category_id = st.session_state.specialty_data.get("category_id", 0) or 0
                
                # Находим индекс текущей категории в списке
                selected_index = 0
                for i, (cat_id, _) in enumerate(category_options):
                    if cat_id == current_category_id:
                        selected_index = i
                        break
                
                edit_category_id = st.selectbox(
                    "Категория",
                    options=category_options,
                    index=selected_index,
                    format_func=lambda x: x[1]
                )[0]
            else:
                edit_category_id = None
                st.info("Нет доступных категорий")
            
            update_submitted = st.form_submit_button("Обновить")
            
            if update_submitted:
                if edit_name:
                    # Подготовка данных для обновления
                    update_data = {
                        "name": edit_name,
                        "description": edit_description,
                        "category_id": edit_category_id if edit_category_id and edit_category_id > 0 else None
                    }
                    
                    # Обновление специальности
                    success = update_record(
                        "specialties", 
                        update_data, 
                        f"id = {st.session_state.specialty_data['id']}"
                    )
                    
                    if success:
                        st.success(f"Специальность '{edit_name}' успешно обновлена")
                        # Обновление данных в сессии
                        st.session_state.specialty_data.update(update_data)
                        # Перезагрузка страницы для обновления данных
                        st.experimental_rerun()
                    else:
                        st.error("Ошибка при обновлении специальности")
                else:
                    st.error("Название специальности обязательно")
