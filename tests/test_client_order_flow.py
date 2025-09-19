"""Тесты для клиентского флоу просмотра заказов и получения уведомлений о ставках."""
import asyncio
import datetime
import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, User as TelegramUser
from sqlalchemy import select

from app.bot.handlers.client import view_order_details_client, order_bids_list
from app.bot.handlers.master import submit_bid_price
from app.models import Bid, Order, User
from core.db import SessionFactory


@pytest.fixture
def telegram_user():
    """Фикстура для создания объекта пользователя Telegram."""
    user = MagicMock()
    user.id = 123456789
    user.full_name = "Test User"
    return user


@pytest.fixture
def callback_query(telegram_user):
    """Фикстура для создания объекта CallbackQuery."""
    callback = AsyncMock()
    callback.from_user = telegram_user
    callback.data = "order:1"
    callback.message = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    callback.bot = AsyncMock()
    return callback


@pytest.fixture
def message(telegram_user):
    """Фикстура для создания объекта Message."""
    msg = AsyncMock()
    msg.from_user = telegram_user
    msg.text = "1000"
    msg.answer = AsyncMock()
    msg.bot = AsyncMock()
    msg.bot.send_message = AsyncMock()
    return msg


@pytest.fixture
def fsm_context():
    """Фикстура для создания объекта FSMContext."""
    context = AsyncMock(spec=FSMContext)
    context.get_data = AsyncMock(return_value={"order_id": 1})
    context.set_state = AsyncMock()
    context.update_data = AsyncMock()
    context.clear = AsyncMock()
    return context


@pytest_asyncio.fixture
async def setup_db(test_db_session):
    """Создание тестовых данных в БД.
    Генерируем уникальные tg_id, чтобы избежать конфликтов при повторных запусках.
    """
    async with test_db_session() as session:
        # Уникальная база для tg_id
        base_tg = random.randint(1_000_000_000, 9_999_999_999)

        # Создаем клиента
        client = User(
            tg_id=base_tg,
            name="Test Client",
            role="client"
        )
        session.add(client)
        await session.flush()

        # Создаем мастера
        master = User(
            tg_id=base_tg + 1,
            name="Test Master",
            role="master"
        )
        session.add(master)
        await session.flush()

        # Создаем заказ
        order = Order(
            client_id=client.id,
            category="Тестовая категория",
            description="Тестовое описание",
            status="new",
            created_at=datetime.datetime.now()
        )
        session.add(order)
        await session.flush()

        # Создаем ставку
        bid = Bid(
            order_id=order.id,
            master_id=master.id,
            price=1000,
            status="active",
            created_at=datetime.datetime.now()
        )
        session.add(bid)
        await session.commit()

        return {
            "client": client,
            "master": master,
            "order": order,
            "bid": bid
        }


@pytest.mark.asyncio
async def test_view_order_details_client(callback_query, fsm_context, setup_db):
    """Тест просмотра деталей заказа клиентом."""
    # Настраиваем callback_query
    callback_query.data = f"order:{setup_db['order'].id}"
    callback_query.from_user.id = setup_db['client'].tg_id

    # Вызываем тестируемую функцию
    with patch("app.bot.handlers.client.SessionFactory", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=AsyncMock(
            execute=AsyncMock(side_effect=[
                # Мокаем результаты запросов
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['client'])),
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['order'])),
                AsyncMock(scalar=lambda: 1)  # Количество ставок
            ])
        )),
        __aexit__=AsyncMock()
    )):
        await view_order_details_client(callback_query, fsm_context)

    # Проверяем, что был вызван метод edit_text с правильными параметрами
    callback_query.message.edit_text.assert_called_once()
    # Проверяем, что текст содержит ID заказа
    assert f"Заказ #{setup_db['order'].id}" in callback_query.message.edit_text.call_args[0][0]
    # Проверяем, что текст содержит категорию
    assert f"Категория: {setup_db['order'].category}" in callback_query.message.edit_text.call_args[0][0]
    # Проверяем, что текст содержит количество ставок
    assert "Ставок: 1" in callback_query.message.edit_text.call_args[0][0]
    
    # Проверяем, что клавиатура содержит кнопку "Предложения мастеров"
    keyboard = callback_query.message.edit_text.call_args[1]["reply_markup"]
    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert any("Предложения мастеров" in button.text for row in keyboard.inline_keyboard for button in row)
    assert any(f"order_bids:{setup_db['order'].id}" in button.callback_data for row in keyboard.inline_keyboard for button in row)


@pytest.mark.asyncio
async def test_order_bids_list(callback_query, fsm_context, setup_db):
    """Тест просмотра списка ставок по заказу."""
    # Настраиваем callback_query
    callback_query.data = f"order_bids:{setup_db['order'].id}"
    callback_query.from_user.id = setup_db['client'].tg_id

    # Вызываем тестируемую функцию
    with patch("app.bot.handlers.client.SessionFactory", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=AsyncMock(
            execute=AsyncMock(side_effect=[
                # Мокаем результаты запросов
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['client'])),
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['order'])),
                AsyncMock(all=lambda: [(setup_db['bid'], setup_db['master'])])
            ])
        )),
        __aexit__=AsyncMock()
    )):
        await order_bids_list(callback_query, fsm_context)

    # Проверяем, что был вызван метод edit_text с правильными параметрами
    callback_query.message.edit_text.assert_called_once()
    # Проверяем, что текст содержит ID заказа
    assert f"Заказ #{setup_db['order'].id}" in callback_query.message.edit_text.call_args[0][0]
    # Проверяем, что текст содержит информацию о ставке
    assert f"{setup_db['master'].name}: {setup_db['bid'].price} KZT" in callback_query.message.edit_text.call_args[0][0]
    
    # Проверяем, что клавиатура содержит кнопку "Назад"
    keyboard = callback_query.message.edit_text.call_args[1]["reply_markup"]
    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert any("« Назад" in button.text for row in keyboard.inline_keyboard for button in row)


@pytest.mark.asyncio
async def test_submit_bid_price_notification(message, fsm_context, setup_db):
    """Тест отправки уведомления клиенту при создании ставки."""
    # Настраиваем message и context
    message.from_user.id = setup_db['master'].tg_id
    fsm_context.get_data = AsyncMock(return_value={"order_id": setup_db['order'].id})

    # Вызываем тестируемую функцию
    with patch("app.bot.handlers.master.SessionFactory", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=AsyncMock(
            execute=AsyncMock(side_effect=[
                # Мокаем результаты запросов
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['master'])),
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['order'])),
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: None)),  # Нет существующей ставки
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['order'])),
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['client']))
            ]),
            commit=AsyncMock(),
            add=AsyncMock()
        )),
        __aexit__=AsyncMock()
    )):
        await submit_bid_price(message, fsm_context)

    # Проверяем, что был вызван метод send_message для отправки уведомления клиенту
    message.bot.send_message.assert_called_once()
    # Проверяем, что сообщение отправлено клиенту
    assert message.bot.send_message.call_args[1]["chat_id"] == setup_db['client'].tg_id
    # Проверяем, что текст содержит информацию о новой ставке
    assert f"Новая ставка по вашему заказу #{setup_db['order'].id}" in message.bot.send_message.call_args[1]["text"]
    assert f"{message.text} KZT" in message.bot.send_message.call_args[1]["text"]
    
    # Проверяем, что клавиатура содержит кнопку "Посмотреть предложения"
    keyboard = message.bot.send_message.call_args[1]["reply_markup"]
    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert any("Посмотреть предложения" in button.text for row in keyboard.inline_keyboard for button in row)
    assert any(f"order_bids:{setup_db['order'].id}" in button.callback_data for row in keyboard.inline_keyboard for button in row)


@pytest.mark.asyncio
async def test_submit_bid_price_update_notification(message, fsm_context, setup_db):
    """Тест отправки уведомления клиенту при обновлении ставки."""
    # Настраиваем message и context
    message.from_user.id = setup_db['master'].tg_id
    fsm_context.get_data = AsyncMock(return_value={"order_id": setup_db['order'].id})

    # Вызываем тестируемую функцию
    with patch("app.bot.handlers.master.SessionFactory", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=AsyncMock(
            execute=AsyncMock(side_effect=[
                # Мокаем результаты запросов
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['master'])),
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['order'])),
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['bid'])),  # Существующая ставка
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['order'])),
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: setup_db['client']))
            ]),
            commit=AsyncMock()
        )),
        __aexit__=AsyncMock()
    )):
        await submit_bid_price(message, fsm_context)

    # Проверяем, что был вызван метод send_message для отправки уведомления клиенту
    message.bot.send_message.assert_called_once()
    # Проверяем, что сообщение отправлено клиенту
    assert message.bot.send_message.call_args[1]["chat_id"] == setup_db['client'].tg_id
    # Проверяем, что текст содержит информацию об обновлении ставки
    assert f"Ставка обновлена по вашему заказу #{setup_db['order'].id}" in message.bot.send_message.call_args[1]["text"]
    assert f"{message.text} KZT" in message.bot.send_message.call_args[1]["text"]
