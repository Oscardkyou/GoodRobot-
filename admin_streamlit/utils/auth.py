"""
Authentication utilities for Streamlit admin panel.
"""
import hashlib
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.config import get_settings

settings = get_settings()

def check_auth():
    """
    Проверка аутентификации пользователя.
    Возвращает True, если пользователь аутентифицирован, иначе False.
    """
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        
    if st.session_state.authenticated:
        return True
        
    st.title("GoodRobot Admin - Вход")
    
    username = st.text_input("Имя пользователя")
    password = st.text_input("Пароль", type="password")
    
    if st.button("Войти"):
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.success("Вход выполнен успешно!")
            st.rerun()
        else:
            st.error("Неверное имя пользователя или пароль")
            
    return st.session_state.authenticated
    
def authenticate(username, password):
    """
    Аутентификация пользователя в БД.
    Возвращает True, если учетные данные верны, иначе False.
    """
    try:
        # Получение соединения с БД
        # 1) DATABASE_URL из env имеет приоритет
        env_url = os.getenv('DATABASE_URL')
        if env_url:
            url = env_url.replace('postgresql+asyncpg', 'postgresql+psycopg2')
            if 'postgresql+' not in url:
                url = url.replace('postgresql://', 'postgresql+psycopg2://')
            engine = create_engine(url)
        else:
            # 2) DSN из настроек
            pg_dsn = getattr(settings, 'postgres_dsn', None)
            if pg_dsn:
                url = pg_dsn.replace('postgresql+asyncpg', 'postgresql+psycopg2')
                if 'postgresql+' not in url:
                    url = url.replace('postgresql://', 'postgresql+psycopg2://')
                engine = create_engine(url)
            else:
                # 3) Формируем URL из отдельных параметров
                host = getattr(settings, 'postgres_host', 'localhost')
                port = getattr(settings, 'postgres_port', 5432)
                db = getattr(settings, 'postgres_db', 'postgres')
                user = getattr(settings, 'postgres_user', 'postgres')
                password_db = getattr(settings, 'postgres_password', '')
                url = f"postgresql+psycopg2://{user}:{password_db}@{host}:{port}/{db}"
                engine = create_engine(url)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Проверка наличия таблицы admins
        try:
            has_admins_table = session.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'admins')")).scalar()
            if not has_admins_table:
                # Если таблицы нет, проверяем стандартные учетные данные
                default_username = getattr(settings, 'ADMIN_DEFAULT_USERNAME', 'admin')
                default_password = getattr(settings, 'ADMIN_DEFAULT_PASSWORD', 'admin123')
                
                if username == default_username and password == default_password:
                    st.info("Использованы стандартные учетные данные администратора")
                    return True
                return False
        except Exception as e:
            st.warning(f"Ошибка при проверке таблицы admins: {e}")
            # Пробуем использовать стандартные учетные данные
            default_username = getattr(settings, 'ADMIN_DEFAULT_USERNAME', 'admin')
            default_password = getattr(settings, 'ADMIN_DEFAULT_PASSWORD', 'admin123')
            
            if username == default_username and password == default_password:
                st.info("Использованы стандартные учетные данные администратора")
                return True
            return False
        
        # Хеширование пароля (должно соответствовать хешированию в основном приложении)
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Проверка учетных данных
        result = session.execute(
            text("SELECT id FROM admins WHERE username = :username AND password_hash = :password"),
            {"username": username, "password": hashed_password}
        ).scalar()
        
        # Проверка стандартных учетных данных, если в БД не найдено
        if result is None:
            default_username = getattr(settings, 'ADMIN_DEFAULT_USERNAME', 'admin')
            default_password = getattr(settings, 'ADMIN_DEFAULT_PASSWORD', 'admin123')
            
            if username == default_username and password == default_password:
                st.info("Использованы стандартные учетные данные администратора")
                return True
        
        return result is not None
    except Exception as e:
        st.error(f"Ошибка аутентификации: {e}")
        # Пробуем использовать стандартные учетные данные в случае ошибки
        default_username = getattr(settings, 'ADMIN_DEFAULT_USERNAME', 'admin')
        default_password = getattr(settings, 'ADMIN_DEFAULT_PASSWORD', 'admin123')
        
        if username == default_username and password == default_password:
            st.info("Использованы стандартные учетные данные администратора")
            return True
        return False
    finally:
        if 'session' in locals():
            session.close()
