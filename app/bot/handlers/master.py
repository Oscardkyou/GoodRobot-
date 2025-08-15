"""Handlers for мастер role: setup zones and create bids."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from sqlalchemy import select

from app.bot.keyboards import zones_keyboard_master_full, main_menu_keyboard
from app.bot.states import BidCreate, MasterSetup
from app.models import Bid, User
from core.db import SessionFactory

router = Router()


@router.message(Command("help_master"))
async def cmd_help_master(message: Message) -> None:
    await message.answer(
        "Вы мастер. Используйте /start чтобы выбрать роль и настроить районы обслуживания."
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    """Показать главное меню с кнопками."""
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard()
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
        orders = (await session.execute(
            select(Order).where(
                Order.zone.in_(user.zones),
                Order.status == "new"
            ).order_by(Order.created_at.desc())
        )).scalars().all()
    
    if not orders:
        await message.answer("В ваших районах пока нет новых заказов.")
        return
    
    # Показываем последние 5 заказов
    for order in orders[:5]:
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
            "pending": "🕐 Ожидает решения",
            "accepted": "✅ Принята",
            "rejected": "❌ Отклонена"
        }.get(bid.status, "🕐 Ожидает решения")
        
        bid_text = (
            f"💰 Ставка на заказ #{order.id}: {status_text}\n"
            f"Категория: {order.category}\n"
            f"Район: {order.zone}\n"
            f"Цена: {bid.price} руб.\n"
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
    back_to = callback.data.split(":", 1)[1] if ":" in callback.data else "main"
    current_state = await state.get_state()
    
    if back_to == "main" or not current_state:
        # Возврат в главное меню
        await state.clear()
        try:
            await callback.message.edit_text(
                "Главное меню мастера:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Заказы поблизости", callback_data="master:nearby_orders")],
                    [InlineKeyboardButton(text="Мои ставки", callback_data="master:my_bids")],
                    [InlineKeyboardButton(text="Настройки профиля", callback_data="master:profile")]
                ])
            )
        except Exception as e:
            # Если не можем изменить текст сообщения, отправляем новое
            await callback.message.answer(
                "Главное меню мастера:",
                reply_markup=main_menu_keyboard()
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
    elif back_to == "zones_setup" and current_state == MasterSetup.zones:
        # Возврат к выбору роли
        await state.clear()
        from app.bot.keyboards import role_keyboard
        try:
            await callback.message.edit_text(
                "Выберите вашу роль:",
                reply_markup=role_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "Выберите вашу роль:",
                reply_markup=role_keyboard()
            )
        await callback.answer("Возврат к выбору роли")
    else:
        # Если не определено конкретное действие для текущего состояния
        await callback.answer("Действие недоступно в текущем состоянии")


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
    order_id = int(callback.data.split(":", 1)[1])
    await state.update_data(order_id=order_id)
    await state.set_state(BidCreate.price)
    
    # Создаем клавиатуру с кнопкой отмены
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

        bid = Bid(order_id=order_id, master_id=master.id, price=price)
        session.add(bid)
        await session.commit()

    await message.answer("Ставка отправлена! Ожидайте ответа клиента.")
    await state.clear()
