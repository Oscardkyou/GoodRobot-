"""
Database utilities for Streamlit admin panel.
"""
import streamlit as st
import pandas as pd
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import sys
import os
import traceback

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.config import get_settings

# Настройка логгера
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

settings = get_settings()

@st.cache_resource
def get_connection():
    """
    Получение соединения с базой данных.
    Использует st.cache_resource для кеширования соединения.
    """
    # 1) Переменная окружения DATABASE_URL имеет высший приоритет
    env_url = os.getenv('DATABASE_URL')
    if env_url:
        # Нормализуем драйвер на psycopg2 для sync-движка
        url = env_url.replace('postgresql+asyncpg', 'postgresql+psycopg2')
        if 'postgresql+' not in url:
            url = url.replace('postgresql://', 'postgresql+psycopg2://')
        return create_engine(url)

    # 2) Если задан DSN в настройках (Settings.postgres_dsn)
    pg_dsn = getattr(settings, 'postgres_dsn', None)
    if pg_dsn:
        url = pg_dsn.replace('postgresql+asyncpg', 'postgresql+psycopg2')
        if 'postgresql+' not in url:
            url = url.replace('postgresql://', 'postgresql+psycopg2://')
        return create_engine(url)

    # 3) Сборка URL из отдельных параметров (Settings.postgres_*)
    host = getattr(settings, 'postgres_host', 'localhost')
    port = getattr(settings, 'postgres_port', 5432)
    db = getattr(settings, 'postgres_db', 'postgres')
    user = getattr(settings, 'postgres_user', 'postgres')
    password = getattr(settings, 'postgres_password', '')

    # Явно указываем драйвер psycopg2 (пакет psycopg2-binary)
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)

def get_session():
    """
    Получение сессии SQLAlchemy.
    """
    engine = get_connection()
    Session = sessionmaker(bind=engine)
    return Session()

@st.cache_data(ttl=60)  # Кеширование результатов на 60 секунд
def execute_query(query, params=None):
    """
    Выполнение SQL-запроса и возврат результата в виде DataFrame.
    
    Args:
        query (str): SQL-запрос
        params (dict, optional): Параметры запроса
        
    Returns:
        pandas.DataFrame: Результат запроса
    """
    try:
        engine = get_connection()
        if params:
            return pd.read_sql(text(query), engine, params=params)
        else:
            return pd.read_sql(query, engine)
    except Exception as e:
        logger.error(f"Error executing query: {e}\n{traceback.format_exc()}")
        st.error(f"Ошибка выполнения запроса: {e}")
        return pd.DataFrame()

def execute_action(query, params=None):
    """
    Выполнение SQL-запроса, который изменяет данные (INSERT, UPDATE, DELETE).
    
    Args:
        query (str): SQL-запрос
        params (dict, optional): Параметры запроса
        
    Returns:
        bool: True, если запрос выполнен успешно, иначе False
    """
    session = get_session()
    try:
        if params:
            session.execute(text(query), params)
        else:
            session.execute(text(query))
        session.commit()
        # Очищаем кеш после изменения данных
        execute_query.clear()
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Error executing action: {e}\n{traceback.format_exc()}")
        st.error(f"Ошибка выполнения запроса: {e}")
        return False
    finally:
        session.close()

def get_table_schema(table_name):
    """
    Получение схемы таблицы.
    
    Args:
        table_name (str): Название таблицы
        
    Returns:
        dict: Схема таблицы с типами колонок
    """
    try:
        engine = get_connection()
        inspector = inspect(engine)
        
        if not inspector.has_table(table_name):
            st.warning(f"Таблица {table_name} не найдена")
            return {}
        
        columns = inspector.get_columns(table_name)
        primary_keys = inspector.get_pk_constraint(table_name).get('constrained_columns', [])
        foreign_keys = []
        
        for fk in inspector.get_foreign_keys(table_name):
            foreign_keys.extend([(col, fk['referred_table'], fk['referred_columns'][i]) 
                               for i, col in enumerate(fk['constrained_columns'])])
        
        schema = {
            'columns': {col['name']: col['type'] for col in columns},
            'primary_keys': primary_keys,
            'foreign_keys': foreign_keys
        }
        
        return schema
    except Exception as e:
        logger.error(f"Error getting table schema: {e}\n{traceback.format_exc()}")
        st.error(f"Ошибка получения схемы таблицы: {e}")
        return {}

def get_tables_list():
    """
    Получение списка таблиц в БД.
    
    Returns:
        list: Список названий таблиц
    """
    try:
        engine = get_connection()
        inspector = inspect(engine)
        return inspector.get_table_names()
    except Exception as e:
        logger.error(f"Error getting tables list: {e}\n{traceback.format_exc()}")
        st.error(f"Ошибка получения списка таблиц: {e}")
        return []

def insert_record(table_name, data):
    """
    Добавление новой записи в таблицу.
    
    Args:
        table_name (str): Название таблицы
        data (dict): Данные для вставки
        
    Returns:
        bool: True, если запись добавлена успешно, иначе False
    """
    columns = ', '.join(data.keys())
    placeholders = ', '.join([f':{key}' for key in data.keys()])
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    
    return execute_action(query, data)

def update_record(table_name, data, condition):
    """
    Обновление записи в таблице.
    
    Args:
        table_name (str): Название таблицы
        data (dict): Данные для обновления
        condition (str): Условие для обновления
        
    Returns:
        bool: True, если запись обновлена успешно, иначе False
    """
    set_clause = ', '.join([f"{key} = :{key}" for key in data.keys()])
    query = f"UPDATE {table_name} SET {set_clause} WHERE {condition}"
    
    return execute_action(query, data)

def delete_record(table_name, condition, params=None):
    """
    Удаление записи из таблицы.
    
    Args:
        table_name (str): Название таблицы
        condition (str): Условие для удаления
        params (dict, optional): Параметры для условия
        
    Returns:
        bool: True, если запись удалена успешно, иначе False
    """
    query = f"DELETE FROM {table_name} WHERE {condition}"
    
    return execute_action(query, params)

def get_record_by_id(table_name, id_column, record_id):
    """
    Получение записи по ID.
    
    Args:
        table_name (str): Название таблицы
        id_column (str): Название колонки ID
        record_id: Значение ID
        
    Returns:
        pandas.DataFrame: Запись из таблицы
    """
    query = f"SELECT * FROM {table_name} WHERE {id_column} = :id"
    return execute_query(query, {"id": record_id})
