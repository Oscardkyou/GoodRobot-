"""Handlers for мастер role: setup zones and create bids."""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from sqlalchemy import select

from app.bot.keyboards import (
    zones_keyboard_master_full,
    main_menu_keyboard,
    master_main_menu_keyboard,
    role_keyboard,
)
from app.bot.states import BidCreate, MasterSetup
from app.models import Bid, User, Order
from core.db import SessionFactory

logger = logging.getLogger("bot.master")

router = Router()


@router.message(Command("help_master"))
async def cmd_help_master(message: Message) -> None:
    await message.answer(
        "Вы мастер. Используйте /start чтобы выбрать роль и настроить районы обслуживания."
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    """Показать главное меню с кнопками."""
    tg_id = message.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or user.role != "master":
            return
    await state.clear()
    await message.answer(
        "Главное меню мастера:",
        reply_markup=master_main_menu_keyboard()
    )


@router.message(F.text == "📍 Заказы поблизости")
async def nearby_orders_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки просмотра заказов поблизости."""
    tg_id = message.from_user.id

    async with SessionFactory() as session:
        # Получаем мастера и его зоны
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or not user.zones:
            await message.answer("Вы не настроили зоны обслуживания. Используйте /setup для настройки.")
            return

        # Получаем заказы в зонах мастера со статусом "new"
        from app.models import Order

        orders = (await session.execute(
            select(Order).where(
                Order.zone.in_(user.zones),
                Order.status == "new"
            ).order_by(Order.created_at.desc())
        )).scalars().all()

        # Structured debug logging
        logger.info(
            "master_nearby_orders",
            extra={
                "user_id": tg_id,
                "chat_id": message.chat.id if message.chat else None,
                "zones": ",".join(user.zones) if user.zones else "",
                "found": len(orders),
            },
        )

    if not orders:
        await message.answer("В ваших районах пока нет новых заказов.")
        return

    # Показываем последние 5 заказов
    for order in orders[:10]:
        order_text = (
            f"📦 Заказ #{order.id}\n"
            f"Категория: {order.category}\n"
            f"Район: {order.zone}\n"
            f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подробнее", callback_data=f"view_order:{order.id}")],
            [InlineKeyboardButton(text="Сделать ставку", callback_data=f"bid:{order.id}")]
        ])

        await message.answer(order_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("view_order:"))
async def view_order_details(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать подробности заказа для мастера."""
    try:
        order_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    async with SessionFactory() as session:
        order = (
            await session.execute(select(Order).where(Order.id == order_id))
        ).scalars().first()

    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    text = (
        f"📦 Заказ #{order.id}\n"
        f"Категория: {order.category}\n"
        f"Район: {order.zone}\n"
        f"Адрес: {order.address or '—'}\n"
        f"Описание: {order.description or '—'}\n"
        f"Статус: {order.status}\n"
        f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сделать ставку", callback_data=f"bid:{order.id}")],
        [InlineKeyboardButton(text="« Назад", callback_data="back:main")]
    ])

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)
    # Отправим медиа вложения отдельными сообщениями (если есть)
    if order.media:
        for m in (order.media or [])[:10]:
            try:
                if isinstance(m, str) and m.startswith("photo:"):
                    await callback.message.answer_photo(m.split(":", 1)[1])
                elif isinstance(m, str) and m.startswith("video:"):
                    await callback.message.answer_video(m.split(":", 1)[1])
            except Exception:
                pass
    await callback.answer()


@router.message(F.text == "💰 Мои ставки")
async def my_bids_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки просмотра своих ставок."""
    tg_id = message.from_user.id

    async with SessionFactory() as session:
        # Получаем мастера
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте /start для начала работы.")
            return

        # Получаем ставки мастера
        bids_query = (
            select(Bid, Order)
            .join(Order, Bid.order_id == Order.id)
            .where(Bid.master_id == user.id)
            .order_by(Bid.created_at.desc())
        )

        result = await session.execute(bids_query)
        bids_with_orders = result.all()

    if not bids_with_orders:
        await message.answer("У вас пока нет ставок. Найдите заказы в разделе 'Заказы поблизости'.")
        return

    # Показываем последние 5 ставок
    for bid, order in bids_with_orders[:5]:
        status_text = {
            "active": "🕐 Ожидает решения",
            "selected": "✅ Принята",
            "rejected": "❌ Отклонена",
        }.get(bid.status, "🕐 Ожидает решения")

        bid_text = (
            f"💰 Ставка на заказ #{order.id}: {status_text}\n"
            f"Категория: {order.category}\n"
            f"Район: {order.zone}\n"
            f"Цена: {bid.price} KZT\n"
            f"Дата ставки: {bid.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подробнее", callback_data=f"view_bid:{bid.id}")]
        ])

        await message.answer(bid_text, reply_markup=keyboard)


@router.message(F.text == "⚙️ Настройки")
async def settings_button(message: Message) -> None:
    """Обработчик кнопки настроек."""
    tg_id = message.from_user.id

    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте /start для начала работы.")
            return

        zones_text = ", ".join(user.zones) if user.zones else "Не указаны"

        settings_text = (
            f"⚙️ Настройки профиля:\n\n"
            f"Имя: {user.name or 'Не указано'}\n"
            f"Районы обслуживания: {zones_text}\n"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить районы", callback_data="setup_zones")],
            [InlineKeyboardButton(text="Изменить роль", callback_data="change_role")]
        ])

        await message.answer(settings_text, reply_markup=keyboard)


@router.message(F.text == "❓ Помощь")
async def help_button(message: Message) -> None:
    """Обработчик кнопки помощи."""
    help_text = (
        "📖 Помощь по использованию бота (режим мастера):\n\n"
        "Команды:\n"
        "/start - Начать работу с ботом\n"
        "/menu - Открыть главное меню\n"
        "/setup - Настроить районы обслуживания\n\n"
        "Как работать с заказами:\n"
        "1. Нажмите 'Заказы поблизости' для поиска заказов в ваших районах\n"
        "2. Нажмите 'Сделать ставку' и укажите вашу цену\n"
        "3. Отслеживайте статус ваших ставок в разделе 'Мои ставки'\n\n"
        "Настройки профиля:\n"
        "- Используйте раздел 'Настройки' для изменения районов обслуживания\n"
        "- Вы можете изменить роль в любой момент\n"
    )

    await message.answer(help_text)


@router.callback_query(F.data.startswith("back:"))
async def handle_back_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик кнопки 'Назад' для всех состояний мастера."""
    # Обрабатываем только если это мастер
    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or user.role != "master":
            return
    back_to = callback.data.split(":", 1)[1] if ":" in callback.data else "main"
    current_state = await state.get_state()

    if back_to == "main" or not current_state:
        # Возврат в главное меню
        await state.clear()
        # Отправляем новое сообщение с клавиатурой мастера
        await callback.message.answer(
            "Главное меню мастера:",
            reply_markup=master_main_menu_keyboard()
        )
        await callback.answer("Возврат в главное меню")
    elif back_to == "master_setup" and current_state == BidCreate.price:
        # Отмена создания ставки
        await state.clear()
        try:
            await callback.message.edit_text(
                "Создание ставки отменено."
            )
        except Exception:
            await callback.message.answer("Создание ставки отменено.")
        await callback.answer("Ставка отменена")
    elif back_to == "master_setup" and current_state == MasterSetup.zones:
        # Возврат к выбору роли
        await state.clear()
        await callback.message.answer(
            "Выберите вашу роль:",
            reply_markup=role_keyboard()
        )
        await callback.answer("Возврат к выбору роли")
    else:
        # Если не определено конкретное действие для текущего состояния
        await callback.answer("Действие недоступно в текущем состоянии")


@router.callback_query(F.data == "setup_zones")
async def setup_zones_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Войти в режим настройки зон мастера."""
    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
    selected = user.zones if user and user.zones else []
    await state.set_state(MasterSetup.zones)
    await callback.message.edit_text(
        "Выберите районы обслуживания:",
        reply_markup=zones_keyboard_master_full(selected=selected, with_back=True)
    )
    await callback.answer()


@router.callback_query(F.data == "change_role")
async def change_role_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать выбор роли."""
    await state.clear()
    await callback.message.edit_text(
        "Выберите вашу роль:",
        reply_markup=role_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_bid:"))
async def view_bid_details(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать подробности выбранной ставки мастера."""
    try:
        bid_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор ставки", show_alert=True)
        return

    async with SessionFactory() as session:
        result = await session.execute(
            select(Bid, Order).join(Order, Bid.order_id == Order.id).where(Bid.id == bid_id)
        )
        row = result.first()

    if not row:
        await callback.answer("Ставка не найдена", show_alert=True)
        return

    bid, order = row
    status_text = {
        "active": "🕐 Ожидает решения",
        "selected": "✅ Принята",
        "rejected": "❌ Отклонена",
    }.get(bid.status, bid.status)

    text = (
        f"💰 Ставка #{bid.id} по заказу #{order.id}\n"
        f"Статус: {status_text}\n"
        f"Цена: {bid.price} KZT\n"
        f"Комментарий: {bid.note or '—'}\n\n"
        f"📦 Заказ:\n"
        f"Категория: {order.category}\n"
        f"Район: {order.zone}\n"
        f"Адрес: {order.address or '—'}\n"
        f"Описание: {order.description or '—'}\n"
        f"Создан: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )

    # Кнопки действий зависят от статуса ставки
    buttons = []
    if bid.status == "active":
        buttons.append([InlineKeyboardButton(text="Изменить цену", callback_data=f"edit_bid:{bid.id}")])
        buttons.append([InlineKeyboardButton(text="Отменить ставку", callback_data=f"cancel_bid:{bid.id}")])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back:main")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_bid:"))
async def edit_bid_price(callback: CallbackQuery, state: FSMContext) -> None:
    """Инициировать изменение цены для своей активной ставки."""
    try:
        bid_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор ставки", show_alert=True)
        return

    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        bid = (await session.execute(select(Bid).where(Bid.id == bid_id))).scalars().first()

    if not user or not bid or bid.master_id != (user.id if user else None):
        await callback.answer("Ставка не найдена", show_alert=True)
        return
    if bid.status != "active":
        await callback.answer("Нельзя изменить эту ставку", show_alert=True)
        return

    await state.set_state(BidCreate.price)
    await state.update_data(edit_bid_id=bid_id)

    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Отмена", callback_data="back:master_setup")]
    ])

    try:
        await callback.message.edit_text(
            "Введите новую цену (только число, KZT):",
            reply_markup=cancel_keyboard,
        )
    except Exception:
        await callback.message.answer(
            "Введите новую цену (только число, KZT):",
            reply_markup=cancel_keyboard,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_bid:"))
async def cancel_bid(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена своей активной ставки (удаление)."""
    try:
        bid_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор ставки", show_alert=True)
        return

    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        bid = (await session.execute(select(Bid).where(Bid.id == bid_id))).scalars().first()
        if not user or not bid or bid.master_id != (user.id if user else None):
            await callback.answer("Ставка не найдена", show_alert=True)
            return
        if bid.status != "active":
            await callback.answer("Нельзя отменить эту ставку", show_alert=True)
            return
        # Удаляем ставку
        await session.delete(bid)
        await session.commit()

    try:
        await callback.message.edit_text("Ставка отменена.")
    except Exception:
        await callback.message.answer("Ставка отменена.")
    await callback.answer()


@router.callback_query(MasterSetup.zones, F.data.startswith("mzone:"))
async def master_pick_zones(callback: CallbackQuery, state: FSMContext) -> None:
    data = callback.data.split(":", 1)[1]
    selected = (await state.get_data()).get("mzones", [])

    if data == "done":
        tg_id = callback.from_user.id
        async with SessionFactory() as session:
            user = (
                await session.execute(select(User).where(User.tg_id == tg_id))
            ).scalars().first()
            if user:
                user.zones = selected
                await session.commit()
        await state.clear()
        await callback.message.edit_text(
            f"Готово! Вы выбрали районы: {', '.join(selected) if selected else 'не выбраны'}"
        )
        await callback.answer()
        return

    if data == "clear":
        selected = []
    else:
        if data in selected:
            selected = [z for z in selected if z != data]
        else:
            selected = selected + [data]

    await state.update_data(mzones=selected)
    await callback.message.edit_text(
        "Выберите районы обслуживания:",
        reply_markup=zones_keyboard_master_full(selected, with_back=True),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bid:"))
async def start_bid(callback: CallbackQuery, state: FSMContext) -> None:
    # Проверяем корректность заказа перед вводом цены
    try:
        order_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный ID заказа", show_alert=True)
        return

    async with SessionFactory() as session:
        order = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()

    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order.status != "new":
        await callback.answer("Нельзя сделать ставку: заказ уже не новый.", show_alert=True)
        return

    await state.update_data(order_id=order_id)
    await state.set_state(BidCreate.price)

    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Отмена", callback_data="back:master_setup")]
    ])

    await callback.message.answer(
        "Введите вашу цену (только число, KZT):",
        reply_markup=cancel_keyboard
    )
    await callback.answer()


@router.message(BidCreate.price)
async def submit_bid_price(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Пожалуйста, введите сумму числом, без пробелов и букв.")
        return
    price = int(text)

    data = await state.get_data()
    edit_bid_id = data.get("edit_bid_id")
    order_id = data.get("order_id")
    tg_id = message.from_user.id

    async with SessionFactory() as session:
        master = (
            await session.execute(select(User).where(User.tg_id == tg_id))
        ).scalars().first()
        if not master:
            await message.answer("Пользователь не найден. Нажмите /start.")
            await state.clear()
            return
        # Режим редактирования существующей ставки
        if edit_bid_id:
            bid = (
                await session.execute(select(Bid).where(Bid.id == edit_bid_id))
            ).scalars().first()
            if not bid or bid.master_id != master.id:
                await message.answer("Ставка не найдена или вам не принадлежит.")
                await state.clear()
                return
            if bid.status != "active":
                await message.answer("Нельзя изменить эту ставку.")
                await state.clear()
                return
            bid.price = price
            await session.commit()
            await message.answer("Цена ставки обновлена!")
        else:
            order = (
                await session.execute(select(Order).where(Order.id == order_id))
            ).scalars().first()
            if not order:
                await message.answer("Заказ не найден.")
                await state.clear()
                return
            if order.status != "new":
                await message.answer("Нельзя сделать ставку: заказ уже не новый.")
                await state.clear()
                return
            # Защита: мастер не может ставить на собственный заказ
            if order.client_id == master.id:
                await message.answer("Вы не можете делать ставку на собственный заказ.")
                await state.clear()
                return
            # Проверка зоны
            if master.zones and order.zone and order.zone not in master.zones:
                await message.answer("Этот заказ вне ваших зон обслуживания.")
                await state.clear()
                return

            # Проверяем, есть ли уже ставка мастера на этот заказ
            existing = (
                await session.execute(
                    select(Bid).where(Bid.order_id == order_id, Bid.master_id == master.id)
                )
            ).scalars().first()

            if existing:
                existing.price = price
                await session.commit()
                await message.answer("Ваша ставка обновлена!")
            else:
                bid = Bid(order_id=order_id, master_id=master.id, price=price)
                session.add(bid)
                await session.commit()
                await message.answer("Ставка отправлена! Ожидайте ответа клиента.")

    await state.clear()
