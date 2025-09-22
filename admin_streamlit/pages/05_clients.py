"""
Страница управления клиентами.
"""
import streamlit as st
import pandas as pd
import sys
import os
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
    page_title="Клиенты | GoodRobot Admin",
    page_icon="🤖",
    layout="wide",
)

# Аутентификация
if not check_auth():
    st.stop()

# Вспомогательные функции
def get_all_clients():
    """
    Получение списка всех клиентов
    """
    return execute_query("""
        SELECT c.id, c.telegram_id, c.name, c.phone, c.created_at,
               COUNT(DISTINCT o.id) as orders_count
        FROM clients c
        LEFT JOIN orders o ON c.id = o.client_id
        GROUP BY c.id, c.telegram_id, c.name, c.phone, c.created_at
        ORDER BY c.id
    """)

def get_client_details(client_id):
    """
    Получение детальной информации о клиенте
    """
    client_data = get_record_by_id("clients", "id", client_id)
    if client_data.empty:
        return None
    
    # Получение заказов клиента
    orders = execute_query("""
        SELECT o.id, o.created_at, o.status, o.price,
               m.name as master_name, s.name as specialty_name
        FROM orders o
        LEFT JOIN masters m ON o.master_id = m.id
        LEFT JOIN specialties s ON o.specialty_id = s.id
        WHERE o.client_id = :client_id
        ORDER BY o.created_at DESC
        LIMIT 10
    """, {"client_id": client_id})
    
    return {
        "client": client_data.iloc[0].to_dict(),
        "orders": orders
    }

def create_new_client(data):
    """
    Создание нового клиента
    """
    # Добавляем дату создания
    data['created_at'] = datetime.now().isoformat()
    
    # Создаем клиента
    return insert_record("clients", data)

def update_existing_client(client_id, data):
    """
    Обновление существующего клиента
    """
    return update_record("clients", data, f"id = {client_id}")

st.title("Управление клиентами")

# Вкладки
tab1, tab2 = st.tabs(["Список клиентов", "Редактирование клиента"])

# Вкладка "Список клиентов"
with tab1:
    # Фильтры
    st.subheader("Фильтры")
    col1, col2 = st.columns(2)
    
    with col1:
        name_filter = st.text_input("Имя клиента")
    
    with col2:
        phone_filter = st.text_input("Телефон")
    
    # Получение данных с учетом фильтров
    if not name_filter and not phone_filter:
        # Без фильтров
        clients_df = get_all_clients()
    else:
        # С фильтрами
        query = """
            SELECT c.id, c.telegram_id, c.name, c.phone, c.created_at,
                   COUNT(DISTINCT o.id) as orders_count
            FROM clients c
            LEFT JOIN orders o ON c.id = o.client_id
        """
        
        where_clauses = []
        params = {}
        
        if name_filter:
            where_clauses.append("c.name LIKE :name")
            params["name"] = f"%{name_filter}%"
        
        if phone_filter:
            where_clauses.append("c.phone LIKE :phone")
            params["phone"] = f"%{phone_filter}%"
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += """
            GROUP BY c.id, c.telegram_id, c.name, c.phone, c.created_at
            ORDER BY c.id
        """
        
        clients_df = execute_query(query, params)
    
    # Отображение таблицы клиентов
    st.subheader("Список клиентов")
    
    if not clients_df.empty:
        # Форматирование даты
        if 'created_at' in clients_df.columns:
            clients_df['created_at'] = pd.to_datetime(clients_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Переименовываем столбцы для отображения
        display_df = clients_df.rename(columns={
            'id': 'ID',
            'telegram_id': 'Telegram ID',
            'name': 'Имя',
            'phone': 'Телефон',
            'created_at': 'Дата регистрации',
            'orders_count': 'Заказы'
        })
        
        # Отображаем таблицу
        st.dataframe(display_df, use_container_width=True)
        
        # Добавляем кнопки действий под таблицей
        st.write("Действия с клиентами:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            client_id_view = st.number_input("Выберите ID клиента для просмотра", min_value=1, step=1)
            if st.button("Просмотреть"):
                st.session_state.client_id = client_id_view
                st.session_state.client_action = "view"
                st.experimental_rerun()
        
        with col2:
            client_id_edit = st.number_input("Выберите ID клиента для редактирования", min_value=1, step=1)
            if st.button("Редактировать"):
                st.session_state.client_id = client_id_edit
                st.session_state.client_action = "edit"
                st.experimental_rerun()
        
        with col3:
            client_id_delete = st.number_input("Выберите ID клиента для удаления", min_value=1, step=1)
            if st.button("Удалить", type="primary", use_container_width=True):
                # Подтверждение удаления
                st.session_state.client_id = client_id_delete
                st.session_state.client_action = "delete"
                st.experimental_rerun()
        
        # Кнопка для добавления нового клиента
        st.write("""
        ---
        Добавление нового клиента:
        """)
        if st.button("Добавить нового клиента", use_container_width=True):
            st.session_state.client_action = "new"
            st.experimental_rerun()
    else:
        st.info("Клиенты не найдены")

# Вкладка "Редактирование клиента"
with tab2:
    # Проверяем, есть ли действие в сессии
    if 'client_action' in st.session_state and 'client_id' in st.session_state:
        action = st.session_state.client_action
        client_id = st.session_state.client_id
        
        # Действие "Просмотр"
        if action == "view":
            client_details = get_client_details(client_id)
            if client_details:
                st.subheader(f"Информация о клиенте: {client_details['client']['name']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("### Основная информация")
                    st.write(f"**ID:** {client_details['client']['id']}")
                    st.write(f"**Telegram ID:** {client_details['client']['telegram_id']}")
                    st.write(f"**Имя:** {client_details['client']['name']}")
                    st.write(f"**Телефон:** {client_details['client']['phone']}")
                    st.write(f"**Дата регистрации:** {pd.to_datetime(client_details['client']['created_at']).strftime('%Y-%m-%d %H:%M')}")
                    
                    # Кнопка для редактирования
                    if st.button("Редактировать клиента"):
                        st.session_state.client_action = "edit"
                        st.experimental_rerun()
                
                with col2:
                    st.write("### Статистика")
                    orders_count = len(client_details['orders'])
                    st.write(f"**Всего заказов:** {orders_count}")
                    
                    if orders_count > 0:
                        # Статусы заказов
                        statuses = client_details['orders']['status'].value_counts().to_dict()
                        st.write("**Статусы заказов:**")
                        for status, count in statuses.items():
                            st.write(f"- {status}: {count}")
                        
                        # Общая сумма заказов
                        total_spent = client_details['orders']['price'].sum()
                        st.write(f"**Общая сумма заказов:** {total_spent:.2f} руб.")
                
                st.write("### Последние заказы")
                if not client_details['orders'].empty:
                    # Форматирование даты
                    client_details['orders']['created_at'] = pd.to_datetime(client_details['orders']['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                    
                    # Переименовываем столбцы для отображения
                    display_orders = client_details['orders'].rename(columns={
                        'id': 'ID',
                        'created_at': 'Дата',
                        'status': 'Статус',
                        'price': 'Цена',
                        'master_name': 'Мастер',
                        'specialty_name': 'Специальность'
                    })
                    
                    st.dataframe(display_orders, use_container_width=True)
                else:
                    st.info("У клиента нет заказов")
                
                # Кнопка для возврата к списку
                if st.button("Вернуться к списку"):
                    del st.session_state.client_action
                    del st.session_state.client_id
                    st.experimental_rerun()
            else:
                st.error(f"Клиент с ID {client_id} не найден")
                if st.button("Вернуться к списку"):
                    del st.session_state.client_action
                    del st.session_state.client_id
                    st.experimental_rerun()
        
        # Действие "Редактирование"
        elif action == "edit":
            st.subheader(f"Редактирование клиента ID: {client_id}")
            
            # Получаем данные клиента
            client_data = get_record_by_id("clients", "id", client_id)
            
            if not client_data.empty:
                client = client_data.iloc[0]
                
                with st.form("edit_client_form"):
                    name = st.text_input("Имя", value=client['name'])
                    telegram_id = st.number_input("Telegram ID", value=int(client['telegram_id']), min_value=1)
                    phone = st.text_input("Телефон", value=client['phone'] if pd.notna(client['phone']) else "")
                    
                    submitted = st.form_submit_button("Сохранить")
                    
                    if submitted:
                        # Подготавливаем данные для обновления
                        update_data = {
                            "name": name,
                            "telegram_id": telegram_id,
                            "phone": phone
                        }
                        
                        # Обновляем клиента
                        if update_existing_client(client_id, update_data):
                            st.success(f"Клиент {name} успешно обновлен")
                            # Возвращаемся к режиму просмотра
                            st.session_state.client_action = "view"
                            st.experimental_rerun()
                        else:
                            st.error("Ошибка при обновлении клиента")
                
                # Кнопка для возврата к списку
                if st.button("Отмена"):
                    del st.session_state.client_action
                    del st.session_state.client_id
                    st.experimental_rerun()
            else:
                st.error(f"Клиент с ID {client_id} не найден")
                if st.button("Вернуться к списку"):
                    del st.session_state.client_action
                    del st.session_state.client_id
                    st.experimental_rerun()
        
        # Действие "Добавление"
        elif action == "new":
            st.subheader("Добавление нового клиента")
            
            with st.form("add_client_form"):
                name = st.text_input("Имя")
                telegram_id = st.number_input("Telegram ID", min_value=1)
                phone = st.text_input("Телефон")
                
                submitted = st.form_submit_button("Создать")
                
                if submitted:
                    if not name or not telegram_id:
                        st.error("Имя и Telegram ID обязательны для заполнения")
                    else:
                        # Подготавливаем данные для создания
                        new_client_data = {
                            "name": name,
                            "telegram_id": telegram_id,
                            "phone": phone if phone else None
                        }
                        
                        # Создаем клиента
                        if create_new_client(new_client_data):
                            st.success(f"Клиент {name} успешно создан")
                            # Возвращаемся к списку
                            del st.session_state.client_action
                            if 'client_id' in st.session_state:
                                del st.session_state.client_id
                            st.experimental_rerun()
                        else:
                            st.error("Ошибка при создании клиента")
            
            # Кнопка для возврата к списку
            if st.button("Отмена"):
                del st.session_state.client_action
                if 'client_id' in st.session_state:
                    del st.session_state.client_id
                st.experimental_rerun()
        
        # Действие "Удаление"
        elif action == "delete":
            st.subheader(f"Удаление клиента ID: {client_id}")
            
            # Получаем данные клиента
            client_data = get_record_by_id("clients", "id", client_id)
            
            if not client_data.empty:
                client = client_data.iloc[0]
                
                st.warning(f"Вы уверены, что хотите удалить клиента {client['name']} (ID: {client_id})?")
                st.warning("Внимание! Это действие также удалит все заказы клиента!")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Да, удалить", type="primary"):
                        # Сначала удаляем заказы клиента
                        delete_record("orders", "client_id = :client_id", {"client_id": client_id})
                        
                        # Затем удаляем самого клиента
                        if delete_record("clients", "id = :id", {"id": client_id}):
                            st.success(f"Клиент {client['name']} успешно удален")
                            # Возвращаемся к списку
                            del st.session_state.client_action
                            del st.session_state.client_id
                            st.experimental_rerun()
                        else:
                            st.error("Ошибка при удалении клиента")
                
                with col2:
                    if st.button("Отмена", use_container_width=True):
                        del st.session_state.client_action
                        del st.session_state.client_id
                        st.experimental_rerun()
            else:
                st.error(f"Клиент с ID {client_id} не найден")
                if st.button("Вернуться к списку"):
                    del st.session_state.client_action
                    del st.session_state.client_id
                    st.experimental_rerun()
    else:
        st.info("Выберите клиента из списка для просмотра или редактирования, или создайте нового клиента.")
