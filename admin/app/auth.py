from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from typing import Optional, List
import os

from app.models.user import User
from admin.app.database import get_db
from admin.app.schemas import TokenData
from core.config import get_settings

# Получаем настройки
settings = get_settings()

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Настройка OAuth2 с Bearer токеном
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={"admin": "Полный доступ к админ-панели"}
)

def verify_password(plain_password, hashed_password):
    """Проверяет соответствие пароля хешу"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Создает хеш пароля"""
    return pwd_context.hash(password)

async def authenticate_user(username: str, password: str, db: AsyncSession):
    """Аутентифицирует пользователя по имени и паролю"""
    query = select(User).filter(User.username == username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    if not user.is_active:
        return False
    if user.role != "admin":
        return False
    
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создает JWT токен"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)  # Устанавливаем время жизни токена в 30 минут
    
    to_encode.update({"exp": expire})
    # Используем секретный ключ из переменных окружения
    secret_key = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
    algorithm = "HS256"
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    
    return encoded_jwt

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Получает текущего пользователя по токену"""
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        # Используем те же значения, что и при создании токена
        secret_key = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
        algorithm = "HS256"
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except JWTError:
        raise credentials_exception
    
    query = select(User).filter(User.username == token_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Пользователь неактивен")
    
    # Проверяем, что у пользователя есть необходимые разрешения
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
                headers={"WWW-Authenticate": authenticate_value},
            )
    
    return user

async def get_current_admin(
    current_user: User = Security(get_current_user, scopes=["admin"])
):
    """Проверяет, что текущий пользователь - администратор"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return current_user