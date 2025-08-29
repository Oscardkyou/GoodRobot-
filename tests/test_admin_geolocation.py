import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from admin.app.main import app
from admin.app.schemas import OrderResponse
from admin.app.routers.orders import get_orders, get_order
from app.models.order import Order


@pytest.fixture
def test_client():
    """Создает тестовый клиент FastAPI"""
    return TestClient(app)


@pytest.fixture
def mock_order_with_geolocation():
    """Создает мок заказа с геолокацией"""
    order = MagicMock(spec=Order)
    order.id = 1
    order.title = "Тестовый заказ"
    order.description = "Описание тестового заказа"
    order.price = 1000
    order.client_id = 123456789
    order.status = "new"
    order.address = "ул. Тестовая, 123"
    order.latitude = "43.238949"
    order.longitude = "76.889709"
    order.client = MagicMock()
    order.client.username = "test_user"
    return order


@pytest.mark.asyncio
async def test_get_orders_with_geolocation(mock_order_with_geolocation):
    """Тест получения списка заказов с геолокацией"""
    # Мокаем сессию базы данных
    session_mock = AsyncMock(spec=AsyncSession)
    
    # Настраиваем мок для execute
    execute_result = AsyncMock()
    execute_result.scalars.return_value.all.return_value = [mock_order_with_geolocation]
    session_mock.execute.return_value = execute_result
    
    # Вызываем функцию получения заказов
    result = await get_orders(
        session=session_mock,
        skip=0,
        limit=10,
        status=None,
        client_id=None,
        zone=None,
        category=None
    )
    
    # Проверяем, что в результате есть заказ с геолокацией
    assert len(result) == 1
    assert result[0].latitude == "43.238949"
    assert result[0].longitude == "76.889709"


@pytest.mark.asyncio
async def test_get_order_with_geolocation(mock_order_with_geolocation):
    """Тест получения детальной информации о заказе с геолокацией"""
    # Мокаем сессию базы данных
    session_mock = AsyncMock(spec=AsyncSession)
    
    # Настраиваем мок для execute
    execute_result = AsyncMock()
    execute_result.scalar_one_or_none.return_value = mock_order_with_geolocation
    session_mock.execute.return_value = execute_result
    
    # Вызываем функцию получения заказа
    result = await get_order(order_id=1, session=session_mock)
    
    # Проверяем, что в результате есть геолокация
    assert result.latitude == "43.238949"
    assert result.longitude == "76.889709"


def test_orders_api_with_geolocation(test_client):
    """Интеграционный тест API заказов с геолокацией"""
    # Мокаем зависимость для получения сессии
    app.dependency_overrides = {}
    
    # Мокаем ответ API
    mock_order_response = {
        "id": 1,
        "title": "Тестовый заказ",
        "description": "Описание тестового заказа",
        "price": 1000,
        "client_id": 123456789,
        "status": "new",
        "address": "ул. Тестовая, 123",
        "latitude": "43.238949",
        "longitude": "76.889709",
        "client_username": "test_user",
        "created_at": "2025-08-24T10:00:00",
        "updated_at": None
    }
    
    # Патчим функцию get_orders
    with patch("admin.app.routers.orders.get_orders") as mock_get_orders:
        mock_get_orders.return_value = [OrderResponse(**mock_order_response)]
        
        # Выполняем запрос к API
        response = test_client.get("/api/v1/orders/")
        
        # Проверяем ответ
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["latitude"] == "43.238949"
        assert data[0]["longitude"] == "76.889709"


def test_order_detail_api_with_geolocation(test_client):
    """Интеграционный тест API детальной информации о заказе с геолокацией"""
    # Мокаем зависимость для получения сессии
    app.dependency_overrides = {}
    
    # Мокаем ответ API
    mock_order_response = {
        "id": 1,
        "title": "Тестовый заказ",
        "description": "Описание тестового заказа",
        "price": 1000,
        "client_id": 123456789,
        "status": "new",
        "address": "ул. Тестовая, 123",
        "latitude": "43.238949",
        "longitude": "76.889709",
        "client_username": "test_user",
        "created_at": "2025-08-24T10:00:00",
        "updated_at": None
    }
    
    # Патчим функцию get_order
    with patch("admin.app.routers.orders.get_order") as mock_get_order:
        mock_get_order.return_value = OrderResponse(**mock_order_response)
        
        # Выполняем запрос к API
        response = test_client.get("/api/v1/orders/1")
        
        # Проверяем ответ
        assert response.status_code == 200
        data = response.json()
        assert data["latitude"] == "43.238949"
        assert data["longitude"] == "76.889709"
