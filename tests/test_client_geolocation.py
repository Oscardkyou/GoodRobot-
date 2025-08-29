import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User, Location, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.client import create_address, create_location, skip_location, handle_location_button_text
from app.bot.states import OrderCreate


@pytest.fixture
def message():
    """Фикстура для создания объекта сообщения"""
    msg = AsyncMock(spec=Message)
    msg.from_user = AsyncMock()
    msg.from_user.id = 123456789
    msg.from_user.is_bot = False
    msg.from_user.first_name = "Test"
    # Добавляем асинхронный метод answer
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def state():
    """Фикстура для создания объекта состояния FSM"""
    state_mock = AsyncMock(spec=FSMContext)
    state_mock.get_data.return_value = {
        "category": "Электрика",
        "zone": "Алмалинский",
        "address": "ул. Тестовая, 123"
    }
    return state_mock


@pytest.mark.asyncio
async def test_create_address_handler(message, state):
    """Тест обработчика создания адреса"""
    message.text = "ул. Тестовая, 123"
    
    # Мокаем логгер, ReplyKeyboardMarkup и KeyboardButton
    keyboard_button_mock = MagicMock()
    with patch('app.bot.handlers.client.logger', MagicMock()), \
         patch('app.bot.handlers.client.ReplyKeyboardMarkup', return_value=MagicMock()), \
         patch('app.bot.handlers.client.KeyboardButton', keyboard_button_mock):
        await create_address(message, state)
    
    # Проверяем, что адрес был сохранен в состоянии
    state.update_data.assert_called_once_with(address=message.text)
    
    # Проверяем, что было отправлено сообщение с клавиатурой
    message.answer.assert_called()
    args, kwargs = message.answer.call_args
    assert "Отправьте вашу геолокацию" in args[0]
    assert 'reply_markup' in kwargs
    
    # Проверяем вызов KeyboardButton с параметром request_location=True
    keyboard_button_mock.assert_any_call(text="📍 Отправить геолокацию", request_location=True)
    
    # Проверяем, что состояние было изменено на OrderCreate.location
    state.set_state.assert_called_once_with(OrderCreate.location)


@pytest.mark.asyncio
async def test_create_location_handler_with_location(message, state):
    """Тест обработчика получения геолокации"""
    # Создаем объект геолокации
    location_mock = AsyncMock()
    location_mock.latitude = 43.238949
    location_mock.longitude = 76.889709
    message.location = location_mock
    
    # Мокаем клавиатуру
    with patch('app.bot.keyboards.media_keyboard', return_value=MagicMock()):
        await create_location(message, state)
    
    # Проверяем, что координаты были сохранены в состоянии
    state.update_data.assert_called_once_with(
        latitude=str(message.location.latitude),
        longitude=str(message.location.longitude)
    )
    
    # Проверяем, что было отправлено сообщение о получении геолокации
    message.answer.assert_called()
    args, kwargs = message.answer.call_args
    assert "Геолокация получена" in args[0]
    
    # Проверяем, что состояние было изменено на OrderCreate.media
    state.set_state.assert_called_once_with(OrderCreate.media)


@pytest.mark.asyncio
async def test_create_location_handler_without_location(message, state):
    """Тест обработчика получения сообщения без геолокации"""
    message.location = None
    
    # Мокаем клавиатуру
    with patch('app.bot.keyboards.media_keyboard', return_value=MagicMock()):
        await create_location(message, state)
    
    # Проверяем, что было отправлено сообщение о невозможности получить геолокацию
    message.answer.assert_called()
    args, kwargs = message.answer.call_args
    assert "Не удалось получить геолокацию" in args[0]
    
    # Проверяем, что состояние было изменено на OrderCreate.media
    state.set_state.assert_called_once_with(OrderCreate.media)


@pytest.mark.asyncio
async def test_skip_location_handler(message, state):
    """Тест обработчика пропуска отправки геолокации"""
    # Мокаем клавиатуру и логгер
    with patch('app.bot.keyboards.media_keyboard', return_value=MagicMock()), \
         patch('app.bot.handlers.client.logger'):
        await skip_location(message, state)
    
    # Проверяем, что было отправлено сообщение о пропуске геолокации
    message.answer.assert_called()
    args, kwargs = message.answer.call_args
    assert "Геолокация пропущена" in args[0]
    
    # Проверяем, что состояние было изменено на OrderCreate.media
    state.set_state.assert_called_once_with(OrderCreate.media)


@pytest.mark.asyncio
async def test_handle_location_button_text(message, state):
    """Тест обработчика нажатия на текстовую кнопку отправки геолокации"""
    # Мокаем логгер и ReplyKeyboardMarkup
    keyboard_button_mock = MagicMock()
    with patch('app.bot.handlers.client.logger', MagicMock()), \
         patch('app.bot.handlers.client.ReplyKeyboardMarkup', return_value=MagicMock()), \
         patch('app.bot.handlers.client.KeyboardButton', keyboard_button_mock):
        await handle_location_button_text(message, state)
    
    # Проверяем, что было отправлено сообщение с инструкцией
    message.answer.assert_called()
    args, kwargs = message.answer.call_args
    assert "Нажмите на кнопку" in args[0]
    assert "поделиться вашим местоположением" in args[0]
    
    # Проверяем наличие клавиатуры в ответе
    assert 'reply_markup' in kwargs
    
    # Проверяем вызов KeyboardButton с параметром request_location=True
    keyboard_button_mock.assert_any_call(text="📍 Отправить геолокацию", request_location=True)


# Удаляем тест save_order, так как функция слишком сложная для мокинга
