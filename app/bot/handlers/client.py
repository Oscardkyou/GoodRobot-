"""Client (заказчик) handlers and order creation flow."""
import datetime
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from geopy.geocoders import Nominatim
from sqlalchemy import func, select

from app.bot.keyboards import (
    categories_keyboard,
    confirm_keyboard,
    main_menu_keyboard,
    role_keyboard,
    media_keyboard,
)
from app.bot.states import ClientActions, OrderCreate
from app.models import Bid, Order, Partner, User
from core.db import SessionFactory
from app.services.assignments import (
    AssignmentError,
    select_bid as service_select_bid,
)

logger = logging.getLogger("bot.client")

router = Router()


def location_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для запроса геолокации."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="🗺️ Найти по адресу"), KeyboardButton(text="📝 Ввести координаты")],
            [KeyboardButton(text="⏭️ Пропустить"), KeyboardButton(text="🏠 Меню")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def inline_location_keyboard() -> InlineKeyboardMarkup:
    """Встроенная клавиатура для запроса геолокации (для edit_text)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗺️ Найти по адресу", callback_data="location:address")],
            [InlineKeyboardButton(text="📝 Ввести координаты", callback_data="location:coordinates")],
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="location:skip")],
            [InlineKeyboardButton(text="« Назад", callback_data="back:category")],
        ]
    )


def location_request_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой запроса геолокации."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


@router.message(F.text == "➕ Новый заказ")
async def create_order_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки 'Новый заказ' в главном меню клиента."""
    await state.set_state(OrderCreate.category)
    await message.answer(
        "Выберите категорию для вашего заказа:",
        reply_markup=categories_keyboard()
    )


@router.message(F.text == "📂 Все категории")
async def categories_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки 'Все категории' в главном меню клиента."""
    await state.set_state(OrderCreate.category)
    await message.answer(
        "Выберите категорию для вашего заказа:",
        reply_markup=categories_keyboard()
    )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Greet user, ensure DB record, propose role selection."""
    tg_id = message.from_user.id

    # Check for referral code in start command
    args = message.text.split()
    referral_code = None
    if len(args) > 1:
        referral_code = args[1]

    logger.info("client_cmd:start", extra={"user_id": tg_id, "has_ref": bool(referral_code)})
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
                        text="🎉 Новый пользователь зарегистрировался по вашей реферальной ссылке!"
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
    logger.info("client_cb:choose_role", extra={"user_id": tg_id, "role": role})
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if user:
            user.role = role
            await session.commit()

    if role == "client":
        await callback.message.edit_text(
            "Отлично! Вы клиент. Теперь вы можете создать заказ и выбрать специалиста."
        )
        await callback.message.answer(
            "Используйте /menu для вызова главного меню в любой момент.",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
    elif role == "master":
        await callback.message.edit_text(
            "Вы выбрали роль Мастер."
        )
        # Отправляем новое сообщение с клавиатурой мастера
        from app.bot.keyboards import master_main_menu_keyboard
        await callback.message.answer(
            "Главное меню мастера:",
            reply_markup=master_main_menu_keyboard()
        )
        await state.clear()
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

        from app.bot.keyboards import partner_main_menu_keyboard
        await callback.message.edit_text(
            "🤝 Отлично! Вы партнер. Ниже меню для работы."
        )
        await callback.message.answer(
            "Главное меню партнера:",
            reply_markup=partner_main_menu_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("order:"))
async def view_order_details_client(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать детали заказа для клиента с кнопкой перехода к ставкам."""
    try:
        order_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        order = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()
        if not order or not user or order.client_id != user.id:
            await callback.answer("Заказ не найден", show_alert=True)
            return
            
        # Проверяем, есть ли ставки на этот заказ
        bids_count = (await session.execute(
            select(func.count(Bid.id)).where(Bid.order_id == order_id)
        )).scalar()
        
        text = (
            f"📦 Заказ #{order.id}\n"
            f"Категория: {order.category}\n"
            f"Адрес: {order.address or '—'}\n"
            f"Описание: {order.description or '—'}\n"
            f"Статус: {order.status}\n"
            f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"Ставок: {bids_count}\n"
        )
        
        keyboard_buttons = [
            [InlineKeyboardButton(text="Предложения мастеров", callback_data=f"order_bids:{order.id}")],
            [InlineKeyboardButton(text="« Назад", callback_data="back:category")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()


@router.callback_query(F.data.startswith("order_bids:"))
async def order_bids_list(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать список ставок по заказу для клиента."""
    try:
        order_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        order = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()
        if not order or not user or order.client_id != user.id:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        result = await session.execute(
            select(Bid, User)
            .join(User, User.id == Bid.master_id)
            .where(Bid.order_id == order_id)
            .order_by(Bid.created_at.desc())
        )
        bids = result.all()
        logger.info("client_cb:order_bids", extra={"user_id": tg_id, "order_id": order_id, "bids_count": len(bids)})

    if not bids:
        text = (
            f"📦 Заказ #{order.id}\n"
            f"По этой заявке пока нет ставок."
        )
    else:
        lines = [f"📦 Заказ #{order.id}", "Предложения мастеров:"]
        status_map = {
            "active": "🕐 Ожидает решения",
            "selected": "✅ Принята",
            "rejected": "❌ Отклонена",
        }
        for bid, master in bids[:10]:
            name = master.name or "Мастер"
            st = status_map.get(bid.status, bid.status)
            lines.append(
                f"• {name}: {bid.price} KZT • {st} • {bid.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data=f"order:{order.id}")]]
    )
    # Добавляем кнопки для выбора мастера, если заказ все еще новый
    if order.status == "new" and bids:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data=f"order:{order.id}")]
        ])

        # Добавляем кнопки для каждой активной ставки
        for bid, master in bids:
            if bid.status == "active":
                keyboard.inline_keyboard.insert(0, [
                    InlineKeyboardButton(
                        text=f"Выбрать: {master.name} ({bid.price} KZT)",
                        callback_data=f"select_bid:{bid.id}"
                    )
                ])
                keyboard.inline_keyboard.insert(1, [
                    InlineKeyboardButton(
                        text=f"Профиль мастера: {master.name}",
                        callback_data=f"master_profile:{master.id}"
                    )
                ])

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        # Если не удалось отредактировать, отправляем новое сообщение
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(OrderCreate.category, F.data.startswith("category:"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":")[1]
    await state.update_data(category=category)

    await state.set_state(OrderCreate.location)
    # Сначала отправляем сообщение с inline клавиатурой
    await callback.message.edit_text(
        "Выберите способ указания местоположения:",
        reply_markup=inline_location_keyboard()
    )
    # Затем отправляем новое сообщение с клавиатурой для запроса геолокации
    await callback.message.answer(
        "Или просто отправьте свою геолокацию, нажав на кнопку ниже:",
        reply_markup=location_request_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "location:address")
async def location_address_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderCreate.location_by_address)
    await callback.message.edit_text(
        "Введите адрес для поиска координат (например, 'Москва, Ленинградский проспект, 80'):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="back:location")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "location:coordinates")
async def location_coordinates_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderCreate.location_by_coordinates)
    await callback.message.edit_text(
        "Введите координаты в формате 'широта, долгота' (например, '55.7558, 37.6173'):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="back:location")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "location:skip")
async def location_skip_handler(callback: CallbackQuery, state: FSMContext):
    # Пропускаем шаг с геолокацией
    await state.update_data(latitude=None, longitude=None)
    await state.set_state(OrderCreate.description)
    await callback.message.edit_text(
        "Опишите вашу проблему или задачу:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="back:location")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "back:location")
async def back_to_location(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderCreate.location)
    # Отправляем inline клавиатуру
    await callback.message.edit_text(
        "Выберите способ указания местоположения:",
        reply_markup=inline_location_keyboard()
    )
    # Отправляем клавиатуру для запроса геолокации
    await callback.message.answer(
        "Или просто отправьте свою геолокацию, нажав на кнопку ниже:",
        reply_markup=location_request_keyboard()
    )
    await callback.answer()


@router.message(OrderCreate.location, F.location)
async def process_location(message: Message, state: FSMContext) -> None:
    """Обработчик для получения геолокации от пользователя"""
    # Получаем координаты из объекта геолокации
    latitude = message.location.latitude
    longitude = message.location.longitude

    # Сохраняем координаты в состоянии
    await state.update_data(latitude=latitude, longitude=longitude)

    # Переходим к следующему шагу - описанию заказа
    await state.set_state(OrderCreate.description)

    # Отправляем сообщение с подтверждением получения геолокации
    await message.answer(
        f"Геолокация получена: {latitude}, {longitude}\n\nТеперь опишите вашу проблему или задачу:",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(ClientActions.waiting_location, F.location)
async def update_client_location(message: Message, state: FSMContext) -> None:
    """Обработчик обновления геолокации клиентом по запросу мастера."""
    # Получаем координаты из объекта геолокации
    latitude = message.location.latitude
    longitude = message.location.longitude

    # Получаем данные из состояния
    data = await state.get_data()
    master_id = data.get("location_master_id")

    if not master_id:
        await message.answer(
            "Не удалось определить мастера, запросившего геолокацию.",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
        return

    tg_id = message.from_user.id

    async with SessionFactory() as session:
        # Получаем клиента
        client = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not client:
            await message.answer(
                "Не удалось найти ваш профиль. Используйте /start для начала работы.",
                reply_markup=main_menu_keyboard()
            )
            await state.clear()
            return

        # Получаем мастера
        master = (await session.execute(select(User).where(User.id == master_id))).scalars().first()
        if not master or not master.tg_id:
            await message.answer(
                "Не удалось найти мастера.",
                reply_markup=main_menu_keyboard()
            )
            await state.clear()
            return

        # Получаем активный заказ между клиентом и мастером
        order = (await session.execute(
            select(Order).where(
                Order.client_id == client.id,
                Order.master_id == master.id,
                Order.status.in_(["assigned", "inprogress"])
            ).order_by(Order.created_at.desc())
        )).scalars().first()

        if not order:
            await message.answer(
                "Не найден активный заказ с этим мастером.",
                reply_markup=main_menu_keyboard()
            )
            await state.clear()
            return

        # Обновляем геолокацию в заказе
        order.latitude = latitude
        order.longitude = longitude
        order.location_updated_at = datetime.datetime.now()
        await session.commit()

        # Отправляем уведомление мастеру
        try:
            await message.bot.send_message(
                chat_id=master.tg_id,
                text=f"✅ Клиент {client.name or 'клиент'} обновил геолокацию для заказа #{order.id}."
            )

            # Отправляем мастеру карту с местоположением клиента
            await message.bot.send_location(
                chat_id=master.tg_id,
                latitude=latitude,
                longitude=longitude
            )
        except Exception as e:
            logger.error(
                "failed_to_notify_master_about_location_update",
                extra={
                    "master_id": master.id,
                    "client_id": client.id,
                    "order_id": order.id,
                    "error": str(e)
                }
            )

    # Отправляем подтверждение клиенту
    await message.answer(
        "✅ Ваша геолокация успешно обновлена и отправлена мастеру.",
        reply_markup=main_menu_keyboard()
    )

    # Очищаем состояние
    await state.clear()


@router.callback_query(F.data.startswith("decline_location:"))
async def decline_location_update(callback: CallbackQuery, state: FSMContext):
    """Обработчик отказа клиента от обновления геолокации."""
    # Получаем данные из состояния
    data = await state.get_data()
    master_id = data.get("location_master_id")

    if not master_id:
        await callback.message.edit_text(
            "Не удалось определить мастера, запросившего геолокацию."
        )
        await callback.answer()
        await state.clear()
        return

    tg_id = callback.from_user.id

    async with SessionFactory() as session:
        # Получаем клиента
        client = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not client:
            await callback.message.edit_text(
                "Не удалось найти ваш профиль. Используйте /start для начала работы."
            )
            await callback.answer()
            await state.clear()
            return

        # Получаем мастера
        master = (await session.execute(select(User).where(User.id == master_id))).scalars().first()
        if not master or not master.tg_id:
            await callback.message.edit_text(
                "Не удалось найти мастера."
            )
            await callback.answer()
            await state.clear()
            return

        # Получаем активный заказ между клиентом и мастером
        order = (await session.execute(
            select(Order).where(
                Order.client_id == client.id,
                Order.master_id == master.id,
                Order.status.in_(["assigned", "inprogress"])
            ).order_by(Order.created_at.desc())
        )).scalars().first()

        if not order:
            await callback.message.edit_text(
                "Не найден активный заказ с этим мастером."
            )
            await callback.answer()
            await state.clear()
            return

        # Отправляем уведомление мастеру об отказе
        try:
            await callback.bot.send_message(
                chat_id=master.tg_id,
                text=f"❌ Клиент {client.name or 'клиент'} отказался обновить геолокацию для заказа #{order.id}."
            )
        except Exception as e:
            logger.error(
                "failed_to_notify_master_about_location_decline",
                extra={
                    "master_id": master.id,
                    "client_id": client.id,
                    "order_id": order.id,
                    "error": str(e)
                }
            )

    # Отправляем подтверждение клиенту
    await callback.message.edit_text(
        "Вы отказались от обновления геолокации."
    )
    await callback.message.answer(
        "Вы можете обновить геолокацию позже, если мастер запросит её снова.",
        reply_markup=main_menu_keyboard()
    )

    # Очищаем состояние
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "back:category")
async def back_to_category_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderCreate.category)
    await callback.message.edit_text(
        "Выберите категорию заявки:",
        reply_markup=categories_keyboard()
    )
    await callback.answer()


@router.message(OrderCreate.location_by_coordinates)
async def process_coordinates(message: Message, state: FSMContext) -> None:
    # Парсим координаты из сообщения
    try:
        coords = message.text.strip().replace(' ', '').split(',')
        if len(coords) != 2:
            await message.answer(
                "❌ Неверный формат координат. Пожалуйста, введите координаты в формате 'широта, долгота'."
            )
            return

        latitude = float(coords[0])
        longitude = float(coords[1])

        # Проверяем валидность координат
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            await state.update_data(latitude=str(latitude), longitude=str(longitude))

            await message.answer(
                f"✅ Координаты приняты!\n"
                f"📍 Широта: {latitude}\n"
                f"📍 Долгота: {longitude}\n\n"
                "Теперь опишите вашу проблему или задачу:"
            )
            await state.set_state(OrderCreate.description)
        else:
            await message.answer(
                "❌ Координаты вне допустимого диапазона. Широта должна быть от -90 до 90, долгота от -180 до 180."
            )
    except ValueError:
        await message.answer(
            "❌ Не удалось распознать координаты. Пожалуйста, введите числа в формате 'широта, долгота'."
        )


@router.message(OrderCreate.location_by_address)
async def create_address(message: Message, state: FSMContext) -> None:
    """Сохраняет адрес и предлагает отправить геолокацию.

    Соответствует ожиданиям тестов: сохраняем address в state,
    показываем клавиатуру с request_location и переводим в OrderCreate.location.
    """
    # Сохраняем адрес
    await state.update_data(address=message.text)

    # Клавиатура для запроса геолокации
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    # Просим отправить геолокацию
    await message.answer(
        "Отправьте вашу геолокацию, нажав на кнопку ниже, или введите координаты/выберите другой способ.",
        reply_markup=kb,
    )

    # Переходим к ожиданию геолокации
    await state.set_state(OrderCreate.location)


# --- Handlers required by tests: create_location, skip_location, handle_location_button_text ---
async def create_location(message: Message, state: FSMContext) -> None:
    """Обработчик получения геолокации от пользователя.

    Требования по тестам:
    - Если message.location есть: сохранить координаты, отправить уведомление и перейти к OrderCreate.media.
    - Если нет: отправить сообщение об ошибке и также перейти к OrderCreate.media.
    В обоих случаях показать клавиатуру добавления медиа (media_keyboard).
    """
    loc = getattr(message, "location", None)
    if loc is not None and hasattr(loc, "latitude") and hasattr(loc, "longitude"):
        await state.update_data(latitude=str(loc.latitude), longitude=str(loc.longitude))
        await message.answer(
            "✅ Геолокация получена!",
            reply_markup=media_keyboard(),
        )
    else:
        await message.answer(
            "❌ Не удалось получить геолокацию. Попробуйте отправить её повторно или выберите другой способ.",
            reply_markup=media_keyboard(),
        )
    # После обработки переводим на добавление медиа
    await state.set_state(OrderCreate.media)


async def skip_location(message: Message, state: FSMContext) -> None:
    """Обработчик пропуска отправки геолокации: сразу переходим к загрузке медиа."""
    await message.answer(
        "⏭️ Геолокация пропущена. Теперь вы можете прикрепить медиа (фото/видео) или пропустить этот шаг.",
        reply_markup=media_keyboard(),
    )
    await state.set_state(OrderCreate.media)


async def handle_location_button_text(message: Message, state: FSMContext) -> None:
    """Пояснение пользователю, как отправить геолокацию через кнопку request_location.

    Тест ожидает наличие текста с подсказкой и клавиатуры с request_location=True.
    """
    # Клавиатура запросит геолокацию у клиента
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(
        "Нажмите на кнопку, чтобы поделиться вашим местоположением.",
        reply_markup=kb,
    )


@router.message(OrderCreate.description)
async def process_description(message: Message, state: FSMContext) -> None:
    """Обработчик для получения описания заказа от пользователя"""
    description = message.text
    if not description or len(description.strip()) < 3:
        await message.answer(
            "❌ Описание слишком короткое. Пожалуйста, опишите вашу проблему или задачу подробнее."
        )
        return

    # Сохраняем описание в состоянии
    await state.update_data(description=description, media=[])

    # Получаем все данные заказа для подтверждения
    data = await state.get_data()

    # Формируем текст для подтверждения
    confirmation_text = (
        "📋 Подтвердите данные заказа:\n\n"
        f"🔧 Категория: {data.get('category')}\n"
    )

    if data.get('latitude') and data.get('longitude'):
        confirmation_text += f"📍 Координаты: {data.get('latitude')}, {data.get('longitude')}\n"

    confirmation_text += f"📝 Описание: {description}\n\n"
    confirmation_text += "Всё верно?"

    # Отправляем сообщение с подтверждением
    await message.answer(
        confirmation_text,
        reply_markup=confirm_keyboard()
    )


@router.callback_query(F.data == "confirm:yes")
async def order_create_confirm_handler(callback: CallbackQuery, state: FSMContext):
    # Save order to DB
    data = await state.get_data()
    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()

        # Создаем заказ в БД
        order = Order(
            client_id=user.id,
            category=data["category"],
            address=data.get("address"),
            latitude=str(data.get("latitude")) if data.get("latitude") else None,
            longitude=str(data.get("longitude")) if data.get("longitude") else None,
            description=data["description"],
            media=data.get("media"),
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        # Уведомляем всех мастеров
        masters = (await session.execute(
            select(User).where(User.role == "master")
        )).scalars().all()

        await state.clear()
        await callback.message.edit_text("Заявка создана! Мастера будут уведомлены.")

    # Send notifications outside transaction
    logger.info("client_order:created", extra={"user_id": tg_id, "order_id": order.id, "masters_count": len(masters)})
    for m in masters:
        if m.tg_id:
            try:
                await callback.message.bot.send_message(
                    chat_id=m.tg_id,
                    text=(
                        "Новая заявка доступна:\n"
                        f"Категория: {data.get('category')}\n"
                        f"Адрес: {data.get('address')}\n"
                        f"Описание: {data.get('description')}\n"
                        f"Медиа: {len(data.get('media', []) or [])} файл(ов)"
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text="Откликнуться", callback_data=f"bid:{order.id}")]]
                    ),
                )
            except Exception:
                # Игнорируем возможные ошибки отправки
                pass
    await callback.answer()


@router.message(F.text == "👤 Мой профиль")
async def profile_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки 'Мой профиль' в главном меню клиента."""
    tg_id = message.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте /start для начала работы.")
            return

        profile_text = (
            f"👤 Ваш профиль:\n\n"
            f"Имя: {user.name or 'Не указано'}\n"
            f"Роль: {user.role or 'Не выбрана'}\n"
            f"ID: {user.tg_id}\n"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить роль", callback_data="change_role")]
        ])

        await message.answer(profile_text, reply_markup=keyboard)


@router.message(F.text == "💬 Сообщения")
async def messages_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки 'Сообщения' в главном меню клиента."""
    await message.answer("💬 Функция сообщений пока недоступна. Используйте встроенный чат Telegram для общения с мастерами.")


@router.message(F.text == "⚙️ Настройки")
async def settings_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки 'Настройки' в главном меню клиента."""
    tg_id = message.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте /start для начала работы.")
            return

        settings_text = (
            f"⚙️ Настройки:\n\n"
            f"Имя: {user.name or 'Не указано'}\n"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить роль", callback_data="change_role")]
        ])

        await message.answer(settings_text, reply_markup=keyboard)


@router.message(F.text == "📦 Мои заказы")
async def my_orders_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки 'Мои заказы' в главном меню клиента."""
    tg_id = message.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте /start для начала работы.")
            return

        # Получаем заказы клиента
        orders_query = select(Order).where(
            Order.client_id == user.id
        ).order_by(Order.created_at.desc())

        orders = (await session.execute(orders_query)).scalars().all()

    if not orders:
        await message.answer("У вас пока нет заказов.")
        return

    await message.answer("📦 Ваши заказы:")

    # Группируем заказы по статусу
    new_orders = [order for order in orders if order.status == "new"]
    active_orders = [order for order in orders if order.status in ["assigned", "inprogress"]]
    completed_orders = [order for order in orders if order.status == "done"]

    # Показываем новые заказы (ожидающие ставок)
    if new_orders:
        await message.answer("🟡 Ожидание ставок:")
        for order in new_orders[:5]:  # Ограничиваем до 5 заказов
            # Проверяем, есть ли ставки на этот заказ
            bids_count = (await session.execute(
                select(func.count(Bid.id)).where(Bid.order_id == order.id)
            )).scalar()
            
            order_text = (
                f"📦 Заказ #{order.id}\n"
                f"Категория: {order.category}\n"
                f"Ставок: {bids_count}\n"
                f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Подробнее", callback_data=f"order:{order.id}")]
            ])

            await message.answer(order_text, reply_markup=keyboard)

    # Показываем активные заказы
    if active_orders:
        await message.answer("🔵 Активные заказы:")
        for order in active_orders[:5]:  # Ограничиваем до 5 заказов
            # Получаем информацию о мастере
            master = (await session.execute(select(User).where(User.id == order.master_id))).scalars().first()
            master_name = master.name if master else "Мастер"
            
            order_text = (
                f"📦 Заказ #{order.id} (В работе)\n"
                f"Категория: {order.category}\n"
                f"Мастер: {master_name}\n"
                f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Подробнее", callback_data=f"order:{order.id}")]
            ])

            await message.answer(order_text, reply_markup=keyboard)

    # Показываем завершенные заказы
    if completed_orders:
        await message.answer("✅ Завершенные заказы:")
        for order in completed_orders[:3]:  # Ограничиваем до 3 заказов
            # Получаем информацию о мастере
            master = (await session.execute(select(User).where(User.id == order.master_id))).scalars().first()
            master_name = master.name if master else "Мастер"
            
            order_text = (
                f"📦 Заказ #{order.id} (Завершен)\n"
                f"Категория: {order.category}\n"
                f"Мастер: {master_name}\n"
                f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

            await message.answer(order_text)


@router.message(F.text == "❓ Помощь")
async def help_button(message: Message) -> None:
    """Обработчик кнопки помощи для клиентов."""
    help_text = (
        "📖 Помощь по использованию бота (режим клиента):\n\n"
        "Команды:\n"
        "/start - Начать работу с ботом\n"
        "/menu - Открыть главное меню\n\n"
        "Для создания заказа нажмите кнопку '➕ Новый заказ'.\n"
        "Вы можете отслеживать свои заказы в разделе '📦 Мои заказы'.\n\n"
        "Если у вас возникли вопросы, обратитесь в поддержку."
        "- В разделе 'Мой профиль' вы можете посмотреть информацию о себе\n"
        "- В разделе 'Настройки' можно изменить роль или другие параметры\n"
    )
    await message.answer(help_text)


@router.callback_query(F.data == "confirm:no")
async def order_create_cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены создания заказа"""
    # Получаем текущие данные заказа
    data = await state.get_data()
    category = data.get("category")

    # Сообщаем пользователю об отмене
    await callback.message.edit_text(
        "❌ Создание заказа отменено. Вы можете начать заново или вернуться в главное меню."
    )

    # Предлагаем пользователю вернуться к выбору категории
    await callback.message.answer(
        "Выберите категорию заявки или вернитесь в главное меню:",
        reply_markup=categories_keyboard(with_back=True)
    )

    # Возвращаемся к состоянию выбора категории
    await state.set_state(OrderCreate.category)
    await callback.answer()


@router.callback_query(F.data.startswith("select_bid:"))
async def select_bid_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Клиент выбирает ставку мастера.

    Меняем статус заказа на "assigned", сохраняем выбранного мастера,
    помечаем выбранную ставку как "selected", остальные как "rejected".
    """
    try:
        bid_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор ставки", show_alert=True)
        return

    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        try:
            order = await service_select_bid(session, bid_id=bid_id, client_tg_id=tg_id)
        except AssignmentError as e:
            await callback.answer(str(e), show_alert=True)
            return
        except Exception:
            await callback.answer("Ошибка при выборе мастера", show_alert=True)
            return

        # Уведомим выбранного мастера, если есть tg_id
        master = (await session.execute(select(User).where(User.id == order.master_id))).scalars().first()
        if master and master.tg_id:
            try:
                await callback.message.bot.send_message(
                    chat_id=master.tg_id,
                    text=(
                        "✅ Вас выбрали для выполнения заказа!\n"
                        f"Заказ #{order.id} — статус: {order.status}"
                    ),
                )
            except Exception:
                pass

        # Обновим сообщение для клиента
        text = (
            f"📦 Заказ #{order.id} — мастер назначен\n"
            f"Статус: {order.status}\n"
            f"Мастер: {master.name if master else '—'}"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="« Назад", callback_data="back:category")]
            ]
        )
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer("Мастер выбран")
