"""
Страница управления мастерами.
"""
import streamlit as st
import pandas as pd
import sys
import os
import json
from datetime import datetime

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from admin_streamlit.utils.auth import check_auth
from admin_streamlit.utils.db import (
    execute_query, execute_action, get_session, 
    insert_record, update_record, delete_record, get_record_by_id
)

# Настройка страницы
st.set_page_config(
    page_title="Мастера | GoodRobot Admin",
    page_icon="🤖",
    layout="wide",
)

# Аутентификация
if not check_auth():
    st.stop()

# Вспомогательные функции
def get_all_masters():
    """
    Получение списка всех мастеров
    """
    return execute_query("""
        SELECT m.id, m.telegram_id, m.name, m.phone, m.rating, m.created_at,
               COUNT(DISTINCT ms.specialty_id) as specialties_count,
               COUNT(DISTINCT o.id) as orders_count
        FROM masters m
        LEFT JOIN master_specialties ms ON m.id = ms.master_id
        LEFT JOIN orders o ON m.id = o.master_id
        GROUP BY m.id, m.telegram_id, m.name, m.phone, m.rating, m.created_at
        ORDER BY m.id
    """)

def get_master_details(master_id):
    """
    Получение детальной информации о мастере
    """
    master_data = get_record_by_id("masters", "id", master_id)
    if master_data.empty:
        return None
    
    # Получение специальностей мастера
    specialties = execute_query("""
        SELECT s.id, s.name
        FROM specialties s
        JOIN master_specialties ms ON s.id = ms.specialty_id
        WHERE ms.master_id = :master_id
        ORDER BY s.name
    """, {"master_id": master_id})
    
    # Получение заказов мастера
    orders = execute_query("""
        SELECT o.id, o.created_at, o.status, o.price,
               c.name as client_name, s.name as specialty_name
        FROM orders o
        LEFT JOIN clients c ON o.client_id = c.id
        LEFT JOIN specialties s ON o.specialty_id = s.id
        WHERE o.master_id = :master_id
        ORDER BY o.created_at DESC
        LIMIT 10
    """, {"master_id": master_id})
    
    return {
        "master": master_data.iloc[0].to_dict(),
        "specialties": specialties,
        "orders": orders
    }

def get_all_specialties():
    """
    Получение списка всех специальностей
    """
    return execute_query("""
        SELECT id, name, description
        FROM specialties
        ORDER BY name
    """)

def get_master_specialties(master_id):
    """
    Получение списка ID специальностей мастера
    """
    specialties = execute_query("""
        SELECT specialty_id
        FROM master_specialties
        WHERE master_id = :master_id
    """, {"master_id": master_id})
    
    return specialties['specialty_id'].tolist() if not specialties.empty else []

def update_master_specialties(master_id, specialty_ids):
    """
    Обновление специальностей мастера
    """
    # Удаляем все текущие специальности
    delete_success = delete_record("master_specialties", "master_id = :master_id", {"master_id": master_id})
    
    if not delete_success:
        return False
    
    # Добавляем новые специальности
    all_success = True
    for specialty_id in specialty_ids:
        success = insert_record("master_specialties", {
            "master_id": master_id,
            "specialty_id": specialty_id
        })
        if not success:
            all_success = False
    
    return all_success

def create_new_master(data):
    """
    Создание нового мастера
    """
    # Добавляем дату создания
    data['created_at'] = datetime.now().isoformat()
    
    # Сохраняем специальности и удаляем их из данных
    specialties = data.pop('specialties', [])
    
    # Создаем мастера
    success = insert_record("masters", data)
    
    if not success:
        return False
    
    # Получаем ID нового мастера
    new_master = execute_query("""
        SELECT id FROM masters
        WHERE telegram_id = :telegram_id
        ORDER BY created_at DESC
        LIMIT 1
    """, {"telegram_id": data['telegram_id']})
    
    if new_master.empty:
        return False
    
    master_id = new_master.iloc[0]['id']
    
    # Добавляем специальности
    if specialties:
        update_master_specialties(master_id, specialties)
    
    return True

def update_existing_master(master_id, data):
    """
    Обновление существующего мастера
    """
    # Сохраняем специальности и удаляем их из данных
    specialties = data.pop('specialties', None)
    
    # Обновляем мастера
    success = update_record("masters", data, f"id = {master_id}")
    
    if not success:
        return False
    
    # Обновляем специальности, если они были переданы
    if specialties is not None:
        update_master_specialties(master_id, specialties)
    
    return True

st.title("Управление мастерами")

# Вкладки
tab1, tab2 = st.tabs(["Список мастеров", "Редактирование мастера"])

# Вкладка "Список мастеров"
with tab1:
    # Фильтры
    st.subheader("Фильтры")
    col1, col2 = st.columns(2)
    
    with col1:
        name_filter = st.text_input("Имя мастера")
    
    with col2:
        specialty_filter = st.selectbox(
            "Специальность",
            options=["Все"] + list(get_all_specialties()["name"]),
            index=0
        )
    
    # Получение данных с учетом фильтров
    if specialty_filter == "Все" and not name_filter:
        # Без фильтров
        masters_df = get_all_masters()
    else:
        # С фильтрами
        query = """
            SELECT m.id, m.telegram_id, m.name, m.phone, m.rating, m.created_at,
                   COUNT(DISTINCT ms.specialty_id) as specialties_count,
                   COUNT(DISTINCT o.id) as orders_count
            FROM masters m
            LEFT JOIN master_specialties ms ON m.id = ms.master_id
            LEFT JOIN specialties s ON ms.specialty_id = s.id
            LEFT JOIN orders o ON m.id = o.master_id
        """
        
        where_clauses = []
        params = {}
        
        if name_filter:
            where_clauses.append("m.name LIKE :name")
            params["name"] = f"%{name_filter}%"
        
        if specialty_filter != "Все":
            where_clauses.append("s.name = :specialty")
            params["specialty"] = specialty_filter
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += """
            GROUP BY m.id, m.telegram_id, m.name, m.phone, m.rating, m.created_at
            ORDER BY m.id
        """
        
        masters_df = execute_query(query, params)
    
    # Отображение таблицы мастеров
    st.subheader("Список мастеров")
    
    if not masters_df.empty:
        # Форматирование даты
        if 'created_at' in masters_df.columns:
            masters_df['created_at'] = pd.to_datetime(masters_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Переименовываем столбцы для отображения
        display_df = masters_df.rename(columns={
            'id': 'ID',
            'telegram_id': 'Telegram ID',
            'name': 'Имя',
            'phone': 'Телефон',
            'rating': 'Рейтинг',
            'created_at': 'Дата создания',
            'specialties_count': 'Специальности',
            'orders_count': 'Заказы'
        })
        
        # Отображаем таблицу
        st.dataframe(display_df, use_container_width=True)
        
        # Добавляем кнопки действий под таблицей
        st.write("Действия с мастерами:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            master_id_view = st.number_input("Выберите ID мастера для просмотра", min_value=1, step=1)
            if st.button("Просмотреть"):
                st.session_state.master_id = master_id_view
                st.session_state.master_action = "view"
                st.experimental_rerun()
        
        with col2:
            master_id_edit = st.number_input("Выберите ID мастера для редактирования", min_value=1, step=1)
            if st.button("Редактировать"):
                st.session_state.master_id = master_id_edit
                st.session_state.master_action = "edit"
                st.experimental_rerun()
        
        with col3:
            master_id_delete = st.number_input("Выберите ID мастера для удаления", min_value=1, step=1)
            if st.button("Удалить", type="primary", use_container_width=True):
                # Подтверждение удаления
                st.session_state.master_id = master_id_delete
                st.session_state.master_action = "delete"
                st.experimental_rerun()
        
        # Кнопка для добавления нового мастера
        st.write("""
        ---
        Добавление нового мастера:
        """)
        if st.button("Добавить нового мастера", use_container_width=True):
            st.session_state.master_action = "new"
            st.experimental_rerun()
    else:
        st.info("Мастера не найдены")

# Вкладка "Редактирование мастера"
with tab2:
    # Проверяем, есть ли действие в сессии
    if 'master_action' in st.session_state and 'master_id' in st.session_state:
        action = st.session_state.master_action
        master_id = st.session_state.master_id
        
        # Действие "Просмотр"
        if action == "view":
            master_details = get_master_details(master_id)
            if master_details:
                st.subheader(f"Информация о мастере: {master_details['master']['name']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("### Основная информация")
                    st.write(f"**ID:** {master_details['master']['id']}")
                    st.write(f"**Telegram ID:** {master_details['master']['telegram_id']}")
                    st.write(f"**Имя:** {master_details['master']['name']}")
                    st.write(f"**Телефон:** {master_details['master']['phone']}")
                    st.write(f"**Рейтинг:** {master_details['master']['rating']}")
                    
                    # Кнопка для редактирования
                    if st.button("Редактировать мастера"):
                        st.session_state.master_action = "edit"
                        st.experimental_rerun()
                
                with col2:
                    st.write("### Специальности")
                    if not master_details['specialties'].empty:
                        for _, specialty in master_details['specialties'].iterrows():
                            st.write(f"- {specialty['name']}")
                    else:
                        st.info("У мастера нет специальностей")
                
                st.write("### Последние заказы")
                if not master_details['orders'].empty:
                    # Форматирование даты
                    master_details['orders']['created_at'] = pd.to_datetime(master_details['orders']['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                    
                    # Переименовываем столбцы для отображения
                    display_orders = master_details['orders'].rename(columns={
                        'id': 'ID',
                        'created_at': 'Дата',
                        'status': 'Статус',
                        'price': 'Цена',
                        'client_name': 'Клиент',
                        'specialty_name': 'Специальность'
                    })
                    
                    st.dataframe(display_orders, use_container_width=True)
                else:
                    st.info("У мастера нет заказов")
                
                # Кнопка для возврата к списку
                if st.button("Вернуться к списку"):
                    del st.session_state.master_action
                    del st.session_state.master_id
                    st.experimental_rerun()
            else:
                st.error(f"Мастер с ID {master_id} не найден")
                if st.button("Вернуться к списку"):
                    del st.session_state.master_action
                    del st.session_state.master_id
                    st.experimental_rerun()
        
        # Действие "Редактирование"
        elif action == "edit":
            st.subheader(f"Редактирование мастера ID: {master_id}")
            
            # Получаем данные мастера
            master_data = get_record_by_id("masters", "id", master_id)
            
            if not master_data.empty:
                master = master_data.iloc[0]
                
                # Получаем текущие специальности мастера
                master_specialties = get_master_specialties(master_id)
                
                # Получаем все специальности
                all_specialties = get_all_specialties()
                
                with st.form("edit_master_form"):
                    name = st.text_input("Имя", value=master['name'])
                    telegram_id = st.number_input("Telegram ID", value=int(master['telegram_id']), min_value=1)
                    phone = st.text_input("Телефон", value=master['phone'] if pd.notna(master['phone']) else "")
                    rating = st.slider("Рейтинг", min_value=0.0, max_value=5.0, value=float(master['rating']) if pd.notna(master['rating']) else 0.0, step=0.1)
                    
                    st.write("### Специальности")
                    
                    # Создаем множественный выбор специальностей
                    specialty_options = {row['id']: row['name'] for _, row in all_specialties.iterrows()}
                    selected_specialties = st.multiselect(
                        "Выберите специальности",
                        options=list(specialty_options.keys()),
                        format_func=lambda x: specialty_options[x],
                        default=master_specialties
                    )
                    
                    submitted = st.form_submit_button("Сохранить")
                    
                    if submitted:
                        # Подготавливаем данные для обновления
                        update_data = {
                            "name": name,
                            "telegram_id": telegram_id,
                            "phone": phone,
                            "rating": rating,
                            "specialties": selected_specialties
                        }
                        
                        # Обновляем мастера
                        if update_existing_master(master_id, update_data):
                            st.success(f"Мастер {name} успешно обновлен")
                            # Возвращаемся к режиму просмотра
                            st.session_state.master_action = "view"
                            st.experimental_rerun()
                        else:
                            st.error("Ошибка при обновлении мастера")
                
                # Кнопка для возврата к списку
                if st.button("Отмена"):
                    del st.session_state.master_action
                    del st.session_state.master_id
                    st.experimental_rerun()
            else:
                st.error(f"Мастер с ID {master_id} не найден")
                if st.button("Вернуться к списку"):
                    del st.session_state.master_action
                    del st.session_state.master_id
                    st.experimental_rerun()
        
        # Действие "Добавление"
        elif action == "new":
            st.subheader("Добавление нового мастера")
            
            # Получаем все специальности
            all_specialties = get_all_specialties()
            
            with st.form("add_master_form"):
                name = st.text_input("Имя")
                telegram_id = st.number_input("Telegram ID", min_value=1)
                phone = st.text_input("Телефон")
                rating = st.slider("Рейтинг", min_value=0.0, max_value=5.0, value=0.0, step=0.1)
                
                st.write("### Специальности")
                
                # Создаем множественный выбор специальностей
                specialty_options = {row['id']: row['name'] for _, row in all_specialties.iterrows()}
                selected_specialties = st.multiselect(
                    "Выберите специальности",
                    options=list(specialty_options.keys()),
                    format_func=lambda x: specialty_options[x]
                )
                
                submitted = st.form_submit_button("Создать")
                
                if submitted:
                    if not name or not telegram_id:
                        st.error("Имя и Telegram ID обязательны для заполнения")
                    else:
                        # Подготавливаем данные для создания
                        new_master_data = {
                            "name": name,
                            "telegram_id": telegram_id,
                            "phone": phone if phone else None,
                            "rating": rating,
                            "specialties": selected_specialties
                        }
                        
                        # Создаем мастера
                        if create_new_master(new_master_data):
                            st.success(f"Мастер {name} успешно создан")
                            # Возвращаемся к списку
                            del st.session_state.master_action
                            if 'master_id' in st.session_state:
                                del st.session_state.master_id
                            st.experimental_rerun()
                        else:
                            st.error("Ошибка при создании мастера")
            
            # Кнопка для возврата к списку
            if st.button("Отмена"):
                del st.session_state.master_action
                if 'master_id' in st.session_state:
                    del st.session_state.master_id
                st.experimental_rerun()
        
        # Действие "Удаление"
        elif action == "delete":
            st.subheader(f"Удаление мастера ID: {master_id}")
            
            # Получаем данные мастера
            master_data = get_record_by_id("masters", "id", master_id)
            
            if not master_data.empty:
                master = master_data.iloc[0]
                
                st.warning(f"Вы уверены, что хотите удалить мастера {master['name']} (ID: {master_id})?")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Да, удалить", type="primary"):
                        # Сначала удаляем связи со специальностями
                        delete_record("master_specialties", "master_id = :master_id", {"master_id": master_id})
                        
                        # Затем удаляем самого мастера
                        if delete_record("masters", "id = :id", {"id": master_id}):
                            st.success(f"Мастер {master['name']} успешно удален")
                            # Возвращаемся к списку
                            del st.session_state.master_action
                            del st.session_state.master_id
                            st.experimental_rerun()
                        else:
                            st.error("Ошибка при удалении мастера")
                
                with col2:
                    if st.button("Отмена", use_container_width=True):
                        del st.session_state.master_action
                        del st.session_state.master_id
                        st.experimental_rerun()
            else:
                st.error(f"Мастер с ID {master_id} не найден")
                if st.button("Вернуться к списку"):
                    del st.session_state.master_action
                    del st.session_state.master_id
                    st.experimental_rerun()
    else:
        st.info("Выберите мастера из списка для просмотра или редактирования, или создайте нового мастера.")
