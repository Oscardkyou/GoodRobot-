"""Client (заказчик) handlers and order creation flow."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from sqlalchemy import select

from app.bot.keyboards import (
    categories_keyboard,
    confirm_keyboard,
    role_keyboard,
    zones_keyboard,
    main_menu_keyboard,
    add_back_button,
)
from app.bot.states import MasterSetup, OrderCreate
from app.models import Order, User, Partner
from core.db import SessionFactory

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Greet user, ensure DB record, propose role selection."""
    tg_id = message.from_user.id
    
    # Check for referral code in start command
    args = message.text.split()
    referral_code = None
    if len(args) > 1:
        referral_code = args[1]
    
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            user = User(tg_id=tg_id, name=message.from_user.full_name or None)
            
            # Handle referral
            if referral_code:
                referrer = (await session.execute(
                    select(User).join(Partner, Partner.user_id == User.id)
                    .where(Partner.referral_code == referral_code.upper())
                )).scalars().first()
                if referrer:
                    user.referrer_id = referrer.id
                    
            session.add(user)
            await session.commit()
            
            # Send notification to referrer
            if referral_code and referrer:
                try:
                    await message.bot.send_message(
                        chat_id=referrer.tg_id,
                        text=f"🎉 Новый пользователь зарегистрировался по вашей реферальной ссылке!"
                    )
                except Exception:
                    pass

    await state.clear()
    await message.answer(
        "Здравствуйте! Я помогу найти мастера. Выберите вашу роль:",
        reply_markup=role_keyboard(),
    )


@router.callback_query(F.data.startswith("role:"))
async def choose_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = callback.data.split(":", 1)[1]
    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if user:
            user.role = role
            await session.commit()

    if role == "client":
        await callback.message.edit_text(
            "Отлично! Вы клиент. Выберите категорию заявки:",
            reply_markup=categories_keyboard(with_back=False),
        )
        await callback.message.answer(
            "Используйте /menu для вызова главного меню в любой момент.",
            reply_markup=main_menu_keyboard()
        )
        await state.set_state(OrderCreate.category)
    elif role == "master":
        from app.bot.keyboards import zones_keyboard_master
        await callback.message.edit_text(
            "Вы выбрали роль Мастер. Укажите районы обслуживания (можно выбрать несколько):",
            reply_markup=zones_keyboard_master(),
        )
        await state.set_state(MasterSetup.zones)
    elif role == "partner":
        # Create partner record if not exists
        async with SessionFactory() as session:
            user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
            partner = (await session.execute(
                select(Partner).where(Partner.user_id == user.id)
            )).scalars().first()
            if not partner:
                partner = Partner(
                    user_id=user.id,
                    slug=f"partner_{user.tg_id}",
                    referral_code=f"REF{user.tg_id:08d}"
                )
                session.add(partner)
                await session.commit()
        
        await callback.message.edit_text(
            "🤝 Отлично! Вы партнер. Используйте команды:\n"
            "/partner_dashboard - ваш дашборд\n"
            "/partner_link - реферальная ссылка\n"
            "/partner_stats - статистика\n"
            "/partner_payouts - история выплат"
        )
    await callback.answer()


@router.callback_query(OrderCreate.category, F.data.startswith("cat:"))
async def create_pick_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    await callback.message.edit_text(
        f"Категория: {category}\nТеперь выберите район:",
        reply_markup=zones_keyboard(with_back=True),
    )
    await state.set_state(OrderCreate.zone)
    await callback.answer()


@router.callback_query(OrderCreate.zone, F.data.startswith("zone:"))
async def create_pick_zone(callback: CallbackQuery, state: FSMContext) -> None:
    zone = callback.data.split(":", 1)[1]
    await state.update_data(zone=zone)
    await callback.message.edit_text(
        f"Район: {zone}\nТеперь отправьте адрес (текстом):"
    )
    await state.set_state(OrderCreate.address)
    await callback.answer()


@router.message(OrderCreate.address)
async def create_address(message: Message, state: FSMContext) -> None:
    await state.update_data(address=message.text.strip())
    await message.answer("Опишите проблему/задачу (текстом):")
    await state.set_state(OrderCreate.description)


@router.message(OrderCreate.description)
async def create_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    data = await state.get_data()
    summary = (
        "Проверьте заявку:\n"
        f"Категория: {data.get('category')}\n"
        f"Район: {data.get('zone')}\n"
        f"Адрес: {data.get('address')}\n"
        f"Описание: {data.get('description')}\n"
    )
    await message.answer(summary, reply_markup=confirm_keyboard(with_back=True))
    await state.set_state(OrderCreate.confirm)


@router.callback_query(F.data.startswith("back:"))
async def handle_back_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик кнопки 'Назад' для всех состояний."""
    back_to = callback.data.split(":", 1)[1] if ":" in callback.data else "main"
    current_state = await state.get_state()
    
    if back_to == "main" or not current_state:
        # Возврат в главное меню
        await state.clear()
        await callback.message.edit_text(
            "Выберите категорию заявки:",
            reply_markup=categories_keyboard(with_back=False),
        )
        await state.set_state(OrderCreate.category)
        await callback.answer("Возврат в главное меню")
    elif back_to == "order_create" and current_state == OrderCreate.zone:
        # Возврат к выбору категории
        await callback.message.edit_text(
            "Выберите категорию заявки:",
            reply_markup=categories_keyboard(with_back=False),
        )
        await state.set_state(OrderCreate.category)
        await callback.answer("Возврат к выбору категории")
    elif back_to == "confirm" and current_state == OrderCreate.confirm:
        # Возврат к предыдущему шагу из подтверждения
        data = await state.get_data()
        await callback.message.edit_text(
            "Опишите проблему/задачу (текстом):",
        )
        await state.set_state(OrderCreate.description)
        await callback.answer("Возврат к описанию проблемы")
    else:
        # Если не определено конкретное действие для текущего состояния
        await callback.answer("Действие недоступно в текущем состоянии")
        return


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    """Показать главное меню с кнопками."""
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard()
    )


@router.message(F.text == "📝 Создать заказ")
async def create_order_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки создания заказа."""
    await state.clear()
    await message.answer(
        "Выберите категорию заявки:",
        reply_markup=categories_keyboard(with_back=False)
    )
    await state.set_state(OrderCreate.category)


@router.message(F.text == "📋 Мои заказы")
async def my_orders_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки просмотра заказов."""
    tg_id = message.from_user.id
    
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте /start для начала работы.")
            return
            
        orders = (await session.execute(
            select(Order).where(Order.client_id == user.id).order_by(Order.created_at.desc())
        )).scalars().all()
    
    if not orders:
        await message.answer("У вас пока нет заказов. Создайте новый заказ с помощью кнопки 'Создать заказ'.")
        return
        
    for order in orders[:5]:  # Показываем последние 5 заказов
        status_text = {
            "new": "🔵 Новый",
            "active": "🟡 В процессе",
            "completed": "🟢 Завершен",
            "cancelled": "🔴 Отменен"
        }.get(order.status, "🔵 Новый")
        
        order_text = (
            f"Заказ #{order.id}: {status_text}\n"
            f"Категория: {order.category}\n"
            f"Район: {order.zone}\n"
            f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подробнее", callback_data=f"order:{order.id}")]
        ])
        
        await message.answer(order_text, reply_markup=keyboard)


@router.message(F.text == "🔍 Поиск")
async def search_button(message: Message) -> None:
    """Обработчик кнопки поиска."""
    await message.answer(
        "Функция поиска находится в разработке. Скоро вы сможете искать мастеров по категориям и районам."
    )


@router.message(F.text == "👨‍🔧 Профиль")
async def profile_button(message: Message) -> None:
    """Обработчик кнопки профиля."""
    tg_id = message.from_user.id
    
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте /start для начала работы.")
            return
            
        role_text = {
            "client": "👤 Клиент",
            "master": "👨‍🔧 Мастер",
            "partner": "🤝 Партнер"
        }.get(user.role, "Не указана")
        
        profile_text = (
            f"📝 Ваш профиль:\n\n"
            f"Имя: {user.name or 'Не указано'}\n"
            f"Роль: {role_text}\n"
        )
        
        if user.role == "master" and user.zones:
            profile_text += f"Районы обслуживания: {', '.join(user.zones)}\n"
        
        # Добавляем кнопку для изменения роли
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить роль", callback_data="change_role")]
        ])
        
        await message.answer(profile_text, reply_markup=keyboard)


@router.message(F.text == "❓ Помощь")
async def help_button(message: Message) -> None:
    """Обработчик кнопки помощи."""
    help_text = (
        "📖 Помощь по использованию бота:\n\n"
        "Команды:\n"
        "/start - Начать работу с ботом\n"
        "/menu - Открыть главное меню\n\n"
        "Для клиентов:\n"
        "- Создавайте заказы и получайте предложения от мастеров\n"
        "- Просматривайте историю заказов\n\n"
        "Для мастеров:\n"
        "- Получайте уведомления о новых заказах\n"
        "- Делайте ставки на заказы\n\n"
        "Для партнеров:\n"
        "- Получайте реферальные ссылки\n"
        "- Отслеживайте статистику и выплаты\n"
    )
    
    await message.answer(help_text)


@router.callback_query(OrderCreate.confirm, F.data.startswith("confirm:"))
async def create_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    decision = callback.data.split(":", 1)[1]
    if decision == "no":
        await state.clear()
        await callback.message.edit_text("Заявка отменена.")
        await callback.answer()
        return

    # Save order to DB
    data = await state.get_data()
    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        order = Order(
            client_id=user.id,
            category=data.get("category"),
            zone=data.get("zone"),
            address=data.get("address"),
            description=data.get("description"),
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        # Notify masters serving this zone
        masters = (
            await session.execute(
                select(User).where(
                    User.role == "master",
                    User.zones.contains([data.get("zone")]),
                )
            )
        ).scalars().all()

    await state.clear()
    await callback.message.edit_text("Заявка создана! Мастера будут уведомлены.")

    # Send notifications outside transaction
    for m in masters:
        if m.tg_id:
            try:
                await callback.message.bot.send_message(
                    chat_id=m.tg_id,
                    text=(
                        "Новая заявка доступна:\n"
                        f"Категория: {data.get('category')}\n"
                        f"Район: {data.get('zone')}\n"
                        f"Адрес: {data.get('address')}\n"
                        f"Описание: {data.get('description')}"
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text="Откликнуться", callback_data=f"bid:{order.id}")]]
                    ),
                )
            except Exception:
                # Игнорируем возможные ошибки отправки
                pass
    await callback.answer()
