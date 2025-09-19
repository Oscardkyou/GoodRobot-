"""Тесты мастера: создание/редактирование/отмена ставки, завершение заказа, back-навигация."""
from __future__ import annotations

import datetime
import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup

from app.bot.handlers.master import (
    submit_bid_price,
    cancel_bid,
    complete_order,
    handle_back_button,
)
from app.bot.states import BidCreate
from app.models import Bid, Order, User


@pytest.fixture
def message():
    msg = AsyncMock()
    msg.from_user = MagicMock()
    msg.from_user.id = random.randint(10**9, 10**10 - 1)
    msg.text = "1000"
    msg.answer = AsyncMock()
    msg.bot = AsyncMock()
    msg.bot.send_message = AsyncMock()
    return msg


@pytest.fixture
def callback():
    cb = AsyncMock()
    cb.from_user = MagicMock()
    cb.from_user.id = random.randint(10**9, 10**10 - 1)
    cb.data = ""
    cb.message = AsyncMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    cb.bot = AsyncMock()
    return cb


@pytest.fixture
def fsm():
    ctx = AsyncMock(spec=FSMContext)
    ctx.get_data = AsyncMock(return_value={})
    ctx.set_state = AsyncMock()
    ctx.update_data = AsyncMock()
    ctx.clear = AsyncMock()
    ctx.get_state = AsyncMock(return_value=None)
    return ctx


@pytest.mark.asyncio
async def test_submit_bid_price_non_numeric(message, fsm):
    """Ввод нечислового значения должен вернуть сообщение об ошибке и не трогать БД."""
    message.text = "abc"
    await submit_bid_price(message, fsm)
    message.answer.assert_called_once()
    assert "Пожалуйста, введите сумму" in message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_submit_bid_price_own_order_forbidden(message, fsm):
    """Мастер не может делать ставку на собственный заказ."""
    base_tg = random.randint(10**9, 10**10 - 1)
    message.from_user.id = base_tg

    master = User(id=1, tg_id=base_tg, role="master", name="M")
    order = Order(id=10, client_id=1, category="cat", status="new", created_at=datetime.datetime.now())

    fsm.get_data = AsyncMock(return_value={"order_id": order.id})

    # Патчим SessionFactory
    with patch("app.bot.handlers.master.SessionFactory", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=AsyncMock(
            execute=AsyncMock(side_effect=[
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: master)),  # select(User)
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: order)),   # select(Order)
            ]),
            commit=AsyncMock(),
        )),
        __aexit__=AsyncMock()
    )):
        await submit_bid_price(message, fsm)

    message.answer.assert_called()
    assert "собственный заказ" in message.answer.call_args[0][0]
    fsm.clear.assert_called()


@pytest.mark.asyncio
async def test_submit_bid_price_edit_not_active(message, fsm):
    """Редактирование запрещено для не-активной ставки."""
    base_tg = random.randint(10**9, 10**10 - 1)
    message.from_user.id = base_tg

    master = User(id=2, tg_id=base_tg, role="master", name="M2")
    bid = Bid(id=5, order_id=20, master_id=2, price=500, status="rejected", created_at=datetime.datetime.now())

    fsm.get_data = AsyncMock(return_value={"edit_bid_id": bid.id})

    with patch("app.bot.handlers.master.SessionFactory", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=AsyncMock(
            execute=AsyncMock(side_effect=[
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: master)),  # select(User)
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: bid)),     # select(Bid by id)
            ]),
            commit=AsyncMock(),
        )),
        __aexit__=AsyncMock()
    )):
        await submit_bid_price(message, fsm)

    message.answer.assert_called()
    assert "Нельзя изменить эту ставку" in message.answer.call_args[0][0]
    fsm.clear.assert_called()


@pytest.mark.asyncio
async def test_submit_bid_price_existing_updates(message, fsm):
    """Повторная ставка обновляет существующую и отправляет уведомление клиенту."""
    base_tg = random.randint(10**9, 10**10 - 1)
    message.from_user.id = base_tg
    message.text = "1234"

    client = User(id=1, tg_id=base_tg + 100, role="client", name="C")
    master = User(id=2, tg_id=base_tg, role="master", name="M")
    order = Order(id=10, client_id=client.id, category="cat", status="new", created_at=datetime.datetime.now())
    existing = Bid(id=6, order_id=order.id, master_id=master.id, price=1000, status="active", created_at=datetime.datetime.now())

    fsm.get_data = AsyncMock(return_value={"order_id": order.id})

    # Патчим последовательность запросов как в submit_bid_price(existing)
    with patch("app.bot.handlers.master.SessionFactory", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=AsyncMock(
            execute=AsyncMock(side_effect=[
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: master)),   # select(User by tg)
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: order)),    # select(Order)
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: existing)), # existing bid
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: order)),    # select(Order) for notify
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: client)),   # select(User client) for notify
            ]),
            commit=AsyncMock(),
        )),
        __aexit__=AsyncMock()
    )):
        await submit_bid_price(message, fsm)

    message.answer.assert_called()
    assert "Ваша ставка обновлена" in message.answer.call_args[0][0]
    # проверим, что уведомление клиенту отправлено
    message.bot.send_message.assert_called_once()
    args, kwargs = message.bot.send_message.call_args
    assert kwargs["chat_id"] == client.tg_id
    assert isinstance(kwargs["reply_markup"], InlineKeyboardMarkup)


@pytest.mark.asyncio
async def test_cancel_bid_success(callback):
    """Успешная отмена активной ставки."""
    base_tg = random.randint(10**9, 10**10 - 1)
    callback.from_user.id = base_tg
    bid = Bid(id=9, order_id=77, master_id=3, price=500, status="active", created_at=datetime.datetime.now())
    user = User(id=3, tg_id=base_tg, role="master", name="M")
    callback.data = f"cancel_bid:{bid.id}"

    session_mock = AsyncMock(
        execute=AsyncMock(side_effect=[
            AsyncMock(scalars=lambda: AsyncMock(first=lambda: user)),  # select(User)
            AsyncMock(scalars=lambda: AsyncMock(first=lambda: bid)),   # select(Bid)
        ]),
        delete=AsyncMock(),
        commit=AsyncMock(),
    )

    with patch("app.bot.handlers.master.SessionFactory", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=session_mock),
        __aexit__=AsyncMock()
    )):
        await cancel_bid(callback, AsyncMock())

    callback.message.edit_text.assert_called_once()
    assert "Ставка отменена" in callback.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_complete_order_success(callback):
    """Мастер завершает свой назначенный заказ в статусе assigned, уведомление клиенту."""
    base_tg = random.randint(10**9, 10**10 - 1)
    callback.from_user.id = base_tg

    master = User(id=10, tg_id=base_tg, role="master", name="M10")
    client = User(id=11, tg_id=base_tg + 123, role="client", name="C11")
    order = Order(id=42, client_id=client.id, master_id=master.id, category="cat", status="assigned", created_at=datetime.datetime.now())

    # корректный callback data
    callback.data = f"complete_order:{order.id}"

    session_mock = AsyncMock(
        execute=AsyncMock(side_effect=[
            AsyncMock(scalars=lambda: AsyncMock(first=lambda: master)),  # select(User by tg)
            AsyncMock(scalars=lambda: AsyncMock(first=lambda: order)),   # select(Order)
            AsyncMock(scalars=lambda: AsyncMock(first=lambda: client)),  # select(User by id)
        ]),
        commit=AsyncMock(),
    )

    with patch("app.bot.handlers.master.SessionFactory", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=session_mock),
        __aexit__=AsyncMock()
    )):
        await complete_order(callback, AsyncMock())

    # Сообщение мастеру: допускаем либо edit_text, либо answer (в зависимости от контекста)
    assert callback.message.edit_text.called or callback.message.answer.called
    # Уведомление клиенту
    callback.bot.send_message.assert_called_once()
    args, kwargs = callback.bot.send_message.call_args
    assert kwargs["chat_id"] == client.tg_id
    assert isinstance(kwargs["reply_markup"], InlineKeyboardMarkup)


@pytest.mark.asyncio
async def test_back_cancel_bid_creation(callback, fsm):
    """back:master_setup при состоянии BidCreate.price отменяет создание ставки."""
    base_tg = random.randint(10**9, 10**10 - 1)
    callback.from_user.id = base_tg
    callback.data = "back:master_setup"

    user = User(id=100, tg_id=base_tg, role="master", name="M100")
    fsm.get_state = AsyncMock(return_value=BidCreate.price)

    with patch("app.bot.handlers.master.SessionFactory", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=AsyncMock(
            execute=AsyncMock(side_effect=[
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: user)),
            ])
        )),
        __aexit__=AsyncMock()
    )):
        await handle_back_button(callback, fsm)

    fsm.clear.assert_called_once()
    # Проверим текст об отмене
    assert any(
        "Создание ставки отменено" in str(arg)
        for call in [callback.message.edit_text.call_args, callback.message.answer.call_args]
        if call and call[0]
        for arg in call[0]
    )


@pytest.mark.asyncio
async def test_back_main_menu(callback, fsm):
    """back:main возвращает главное меню мастера."""
    base_tg = random.randint(10**9, 10**10 - 1)
    callback.from_user.id = base_tg
    callback.data = "back:main"

    user = User(id=200, tg_id=base_tg, role="master", name="M200")
    fsm.get_state = AsyncMock(return_value=None)

    with patch("app.bot.handlers.master.SessionFactory", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=AsyncMock(
            execute=AsyncMock(side_effect=[
                AsyncMock(scalars=lambda: AsyncMock(first=lambda: user)),
            ])
        )),
        __aexit__=AsyncMock()
    )):
        await handle_back_button(callback, fsm)

    callback.message.answer.assert_called_once()
    assert "Главное меню мастера" in callback.message.answer.call_args[0][0]
