"""Handlers for мастер role: setup zones, create bids and track clients."""
import datetime
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from app.bot.keyboards import (
    categories_selection_keyboard,
    master_main_menu_keyboard,
    role_keyboard,
    specialties_selection_keyboard,
    tracking_actions_keyboard,
    tracking_orders_keyboard,
)
from app.bot.states import (
    BidCreate,
    MasterCategorySetup,
    MasterSpecialtySetup,
)
from app.models import Bid, MasterCategory, Order, Specialty, User, master_categories, master_specialties
from core.db import SessionFactory

logger = logging.getLogger("bot.master")

router = Router()


@router.message(Command("help_master"))
async def cmd_help_master(message: Message) -> None:
    await message.answer(
        "Вы мастер. Используйте /start чтобы выбрать роль."
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


@router.message(F.text == "📋 Новые заказы")
async def nearby_orders_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки просмотра новых заказов."""
    tg_id = message.from_user.id

    async with SessionFactory() as session:
        # Получаем мастера
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            await message.answer("Пользователь не найден. Используйте /start для начала работы.")
            return

        # Получаем заказы со статусом "new" и "assigned"
        # Получаем все заказы со статусом "new"
        new_orders_query = select(Order).where(
            Order.status == "new",
            # Исключаем заказы самого мастера, если он вдруг создал заказ как клиент
            Order.client_id != user.id
        ).order_by(Order.created_at.desc())

        # Получаем заказы со статусом "assigned", назначенные этому мастеру
        assigned_orders_query = select(Order).where(
            Order.master_id == user.id,
            Order.status == "assigned"
        ).order_by(Order.created_at.desc())

        # Выполняем оба запроса
        new_orders = (await session.execute(new_orders_query)).scalars().all()
        assigned_orders = (await session.execute(assigned_orders_query)).scalars().all()

        # Получаем ставки мастера, чтобы отметить заказы, на которые он уже сделал ставку
        bids = (await session.execute(
            select(Bid.order_id).where(Bid.master_id == user.id)
        )).scalars().all()

        bid_order_ids = set(bids)

        # Structured debug logging
        logger.info(
            "master_nearby_orders",
            extra={
                "user_id": tg_id,
                "chat_id": message.chat.id if message.chat else None,
                "new_found": len(new_orders),
                "assigned_found": len(assigned_orders),
                "bids_made": len(bid_order_ids),
            },
        )

    # Сначала показываем заказы, назначенные мастеру
    if assigned_orders:
        await message.answer("🟡 Заказы в работе:")
        for order in assigned_orders[:5]:  # Ограничиваем до 5 заказов
            order_text = (
                f"📦 Заказ #{order.id} (В работе)\n"
                f"Категория: {order.category}\n"
                # Районы удалены из модели
                f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Подробнее", callback_data=f"view_order:{order.id}")],
                [InlineKeyboardButton(text="Завершить", callback_data=f"complete_order:{order.id}")]
            ])

            await message.answer(order_text, reply_markup=keyboard)

    # Затем показываем новые заказы
    if new_orders:
        await message.answer("🔵 Новые заказы:")
        for order in new_orders[:10]:  # Ограничиваем до 10 заказов
            # Отмечаем, сделал ли мастер ставку на этот заказ
            has_bid = order.id in bid_order_ids
            bid_status = "✓ Ставка сделана" if has_bid else "Ставка не сделана"

            order_text = (
                f"📦 Заказ #{order.id}\n"
                f"Категория: {order.category}\n"
                f"Статус ставки: {bid_status}\n"
                f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

            keyboard_buttons = [
                [InlineKeyboardButton(text="Подробнее", callback_data=f"view_order:{order.id}")]
            ]

            # Добавляем кнопку ставки только если мастер еще не делал ставку
            if not has_bid:
                keyboard_buttons.append([InlineKeyboardButton(text="Сделать ставку", callback_data=f"bid:{order.id}")])
            else:
                keyboard_buttons.append([InlineKeyboardButton(text="Изменить ставку", callback_data=f"edit_bid_order:{order.id}")])

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await message.answer(order_text, reply_markup=keyboard)

    # Если нет ни новых, ни назначенных заказов
    if not new_orders and not assigned_orders:
        await message.answer("Пока нет новых заказов, и у вас нет заказов в работе.")


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
        await message.answer("У вас пока нет ставок. Найдите заказы в разделе 'Новые заказы'.")
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
            f"Цена: {bid.price} KZT\n"
            f"Дата ставки: {bid.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подробнее", callback_data=f"view_bid:{bid.id}")]
        ])

        await message.answer(bid_text, reply_markup=keyboard)


@router.message(F.text == "📦 Мои заказы")
async def my_orders_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки просмотра заказов мастера."""
    tg_id = message.from_user.id

    async with SessionFactory() as session:
        # Получаем мастера
        master = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not master or master.role != "master":
            await message.answer("Вы не зарегистрированы как мастер. Используйте /start для начала работы.")
            return

        # Получаем заказы мастера всех статусов
        orders_query = select(Order).where(
            Order.master_id == master.id
        ).order_by(Order.created_at.desc())

        orders = (await session.execute(orders_query)).scalars().all()

    if not orders:
        await message.answer("У вас пока нет заказов. Найдите заказы в разделе 'Новые заказы'.")
        return

    await message.answer("📦 Ваши заказы:")

    # Группируем заказы по статусу
    active_orders = [order for order in orders if order.status in ["assigned", "inprogress"]]
    completed_orders = [order for order in orders if order.status == "done"]

    # Показываем активные заказы
    if active_orders:
        await message.answer("🔵 Активные заказы:")
        for order in active_orders[:5]:  # Ограничиваем до 5 заказов
            order_text = (
                f"📦 Заказ #{order.id} (В работе)\n"
                f"Категория: {order.category}\n"
                f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Отслеживать", callback_data=f"track_order:{order.id}")],
                [InlineKeyboardButton(text="✅ Завершить", callback_data=f"complete_order:{order.id}")]
            ])

            await message.answer(order_text, reply_markup=keyboard)

    # Показываем завершенные заказы
    if completed_orders:
        await message.answer("✅ Завершенные заказы:")
        for order in completed_orders[:3]:  # Показываем только 3 последних завершенных заказа
            order_text = (
                f"📦 Заказ #{order.id} (Завершен)\n"
                f"Категория: {order.category}\n"
                f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

            await message.answer(order_text)


@router.message(F.text == "👤 Профиль")
async def profile_button(message: Message) -> None:
    """Обработчик кнопки 'Профиль' в главном меню мастера."""
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


@router.message(F.text == "⚙️ Настройки")
async def settings_button(message: Message) -> None:
    """Обработчик кнопки настроек."""
    tg_id = message.from_user.id

    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте /start для начала работы.")
            return

        settings_text = (
            f"⚙️ Настройки профиля:\n\n"
            f"Имя: {user.name or 'Не указано'}\n"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить роль", callback_data="change_role")]
        ])

        await message.answer(settings_text, reply_markup=keyboard)


@router.message(F.text == "📍 Отслеживание")
async def tracking_clients_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки отслеживания заказов."""
    tg_id = message.from_user.id

    async with SessionFactory() as session:
        # Получаем мастера
        master = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not master or master.role != "master":
            await message.answer("Вы не зарегистрированы как мастер. Используйте /start для начала работы.")
            return

        # Получаем активные заказы мастера
        orders_query = select(Order).where(
            Order.master_id == master.id,
            Order.status.in_(["assigned", "inprogress"])
        ).order_by(Order.created_at.desc())

        orders = (await session.execute(orders_query)).scalars().all()

    if not orders:
        await message.answer(
            "У вас нет активных заказов для отслеживания. \n"
            "Вы можете отслеживать только заказы, которые находятся в работе."
        )
        return

    await message.answer(
        "Выберите заказ для отслеживания:",
        reply_markup=tracking_orders_keyboard(orders)
    )


@router.message(F.text == "📊 Активные заказы")
async def active_orders_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки просмотра активных заказов."""
    tg_id = message.from_user.id

    async with SessionFactory() as session:
        # Получаем мастера
        master = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not master or master.role != "master":
            await message.answer("Вы не зарегистрированы как мастер. Используйте /start для начала работы.")
            return

        # Получаем активные заказы мастера
        orders_query = select(Order).where(
            Order.master_id == master.id,
            Order.status.in_(["assigned", "inprogress"])
        ).order_by(Order.created_at.desc())

        orders = (await session.execute(orders_query)).scalars().all()

    if not orders:
        await message.answer("У вас нет активных заказов в работе.")
        return

    await message.answer("📊 Ваши активные заказы:")

    for order in orders:
        # Проверяем наличие информации о последнем обновлении геолокации
        location_info = ""
        if order.location_updated_at:
            time_diff = datetime.datetime.now() - order.location_updated_at
            if time_diff.total_seconds() < 3600:  # Меньше часа
                location_info = f"\n📍 Геолокация обновлена {int(time_diff.total_seconds() // 60)} мин. назад"
            else:
                location_info = f"\n📍 Геолокация обновлена {order.location_updated_at.strftime('%d.%m.%Y %H:%M')}"

        order_text = (
            f"📦 Заказ #{order.id}\n"
            f"Категория: {order.category}\n"
            f"Адрес: {order.address or '—'}\n"
            f"Статус: {order.status}\n"
            f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}{location_info}"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Отслеживать", callback_data=f"track_order:{order.id}")],
            [InlineKeyboardButton(text="✅ Завершить", callback_data=f"complete_order:{order.id}")]
        ])

        await message.answer(order_text, reply_markup=keyboard)


@router.message(F.text == "💬 Сообщения")
async def messages_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки 'Сообщения' в главном меню мастера."""
    await message.answer("💬 Функция сообщений пока недоступна. Используйте встроенный чат Telegram для общения с клиентами.")


@router.message(F.text == "❓ Помощь")
async def help_button(message: Message) -> None:
    """Обработчик кнопки помощи."""
    help_text = (
        "📖 Помощь по использованию бота (режим мастера):\n\n"
        "Команды:\n"
        "/start - Начать работу с ботом\n"
        "/menu - Открыть главное меню\n\n"
        "Как работать с заказами:\n"
        "1. Нажмите 'Новые заказы' для поиска доступных заказов\n"
        "2. Нажмите 'Сделать ставку' и укажите вашу цену\n"
        "3. Отслеживайте статус ваших ставок в разделе 'Мои ставки'\n\n"
        "Работа с заказами:\n"
        "1. Нажмите 'Мои заказы' для просмотра активных заказов\n"
        "2. Используйте 'Отслеживание' для мониторинга выполнения заказов\n"
        "3. Вы можете запросить обновление геолокации или посмотреть последнюю известную локацию\n\n"
        "Настройки профиля:\n"
        "- Вы можете изменить роль в любой момент\n"
        "- Настройте свои специализации и категории заказов\n"
    )
    await message.answer(help_text)


@router.message(F.text == "📂 Категории")
async def master_categories_entry(message: Message, state: FSMContext) -> None:
    """Показать выбор категорий заказов для мастера."""
    tg_id = message.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or user.role != "master":
            await message.answer("Вы не зарегистрированы как мастер. Используйте /start для начала работы.")
            return

        # Получаем текущие выбранные категории мастера
        result = await session.execute(
            select(master_categories.c.category).where(master_categories.c.user_id == user.id)
        )
        selected_categories = {row[0] for row in result.all()}

    # Получаем список всех доступных категорий
    all_categories = MasterCategory.CATEGORIES

    await state.set_state(MasterCategorySetup.selecting)
    await state.update_data(mcat_selected=list(selected_categories))
    await message.answer(
        "Выберите категории заказов, которые вы готовы выполнять (нажимайте, чтобы включать/выключать). "
        "Нажмите 'Готово' для сохранения.",
        reply_markup=categories_selection_keyboard(all_categories, selected_categories),
    )


@router.callback_query(MasterCategorySetup.selecting, F.data.startswith("mcat:toggle:"))
async def toggle_master_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Переключить выбранную категорию и обновить клавиатуру."""
    try:
        category = callback.data.split(":", 2)[2]
    except Exception:
        await callback.answer("Некорректная категория", show_alert=True)
        return

    data = await state.get_data()
    selected = set(data.get("mcat_selected", []))
    if category in selected:
        selected.remove(category)
    else:
        selected.add(category)
    await state.update_data(mcat_selected=list(selected))

    # Получаем список всех доступных категорий
    all_categories = MasterCategory.CATEGORIES

    # Обновляем только разметку клавиатуры
    try:
        await callback.message.edit_reply_markup(
            reply_markup=categories_selection_keyboard(all_categories, selected)
        )
    except Exception:
        await callback.message.answer(
            "Обновлено.",
            reply_markup=categories_selection_keyboard(all_categories, selected),
        )
    await callback.answer()


@router.callback_query(MasterCategorySetup.selecting, F.data == "mcat:done")
async def save_master_categories(callback: CallbackQuery, state: FSMContext) -> None:
    """Сохранить выбранные категории мастера."""
    tg_id = callback.from_user.id
    data = await state.get_data()
    selected_categories = set(data.get("mcat_selected", []))

    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or user.role != "master":
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        # Удаляем все текущие категории мастера
        await session.execute(
            master_categories.delete().where(master_categories.c.user_id == user.id)
        )

        # Добавляем выбранные категории
        if selected_categories:
            for category in selected_categories:
                await session.execute(
                    master_categories.insert().values(
                        user_id=user.id,
                        category=category
                    )
                )

        await session.commit()

    await state.clear()
    categories_text = ", ".join(selected_categories) if selected_categories else "—"
    try:
        await callback.message.edit_text(f"Сохранено. Ваши категории заказов: {categories_text}")
    except Exception:
        await callback.message.answer(f"Сохранено. Ваши категории заказов: {categories_text}")
    await callback.message.answer("Главное меню мастера:", reply_markup=master_main_menu_keyboard())
    await callback.answer("Сохранено")


@router.message(F.text == "🔧 Специализации")
async def master_specialties_entry(message: Message, state: FSMContext) -> None:
    """Показать выбор специализаций для мастера."""
    tg_id = message.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or user.role != "master":
            await message.answer("Вы не зарегистрированы как мастер. Используйте /start для начала работы.")
            return
        all_specs = (
            await session.execute(
                select(Specialty).where(Specialty.is_active == True).order_by(Specialty.name)
            )
        ).scalars().all()
        
        # Загружаем специальности пользователя явно через запрос вместо lazy-loading
        user_specs = (
            await session.execute(
                select(Specialty)
                .join(master_specialties)
                .where(master_specialties.c.user_id == user.id)
            )
        ).scalars().all()
        selected_ids = {s.id for s in user_specs}

    if not all_specs:
        await message.answer("Список специализаций пуст. Обратитесь к администратору.")
        return

    await state.set_state(MasterSpecialtySetup.selecting)
    await state.update_data(mspec_selected=list(selected_ids))
    await message.answer(
        "Выберите ваши специализации (нажимайте, чтобы включать/выключать). Нажмите 'Готово' для сохранения.",
        reply_markup=specialties_selection_keyboard(all_specs, selected_ids),
    )


@router.callback_query(MasterSpecialtySetup.selecting, F.data.startswith("mspec:toggle:"))
async def toggle_master_specialty(callback: CallbackQuery, state: FSMContext) -> None:
    """Переключить выбранную специализацию и обновить клавиатуру."""
    try:
        spec_id = int(callback.data.split(":", 2)[2])
    except Exception:
        await callback.answer("Некорректный идентификатор", show_alert=True)
        return

    data = await state.get_data()
    selected = set(data.get("mspec_selected", []))
    if spec_id in selected:
        selected.remove(spec_id)
    else:
        selected.add(spec_id)
    await state.update_data(mspec_selected=list(selected))

    async with SessionFactory() as session:
        all_specs = (
            await session.execute(
                select(Specialty).where(Specialty.is_active == True).order_by(Specialty.name)
            )
        ).scalars().all()

    # Обновляем только разметку клавиатуры
    try:
        await callback.message.edit_reply_markup(
            reply_markup=specialties_selection_keyboard(all_specs, selected)
        )
    except Exception:
        await callback.message.answer(
            "Обновлено.",
            reply_markup=specialties_selection_keyboard(all_specs, selected),
        )
    await callback.answer()


@router.callback_query(MasterSpecialtySetup.selecting, F.data == "mspec:done")
async def save_master_specialties(callback: CallbackQuery, state: FSMContext) -> None:
    """Сохранить выбранные специализации мастера."""
    tg_id = callback.from_user.id
    data = await state.get_data()
    selected_ids = set(data.get("mspec_selected", []))

    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or user.role != "master":
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        specs = []
        if selected_ids:
            specs = (
                await session.execute(select(Specialty).where(Specialty.id.in_(selected_ids)))
            ).scalars().all()

        user.specialties = specs
        await session.commit()

    await state.clear()
    names = ", ".join([s.name for s in specs]) if specs else "—"
    try:
        await callback.message.edit_text(f"Сохранено. Ваши специализации: {names}")
    except Exception:
        await callback.message.answer(f"Сохранено. Ваши специализации: {names}")
    await callback.message.answer("Главное меню мастера:", reply_markup=master_main_menu_keyboard())
    await callback.answer("Сохранено")


@router.callback_query(F.data.startswith("track_order:"))
async def track_order_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик выбора заказа для отслеживания."""
    try:
        order_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        # Получаем мастера
        master = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not master or master.role != "master":
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        # Получаем заказ
        order = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        # Проверяем, что заказ назначен этому мастеру
        if order.master_id != master.id:
            await callback.answer("Этот заказ не назначен вам", show_alert=True)
            return

        # Получаем клиента
        client = (await session.execute(select(User).where(User.id == order.client_id))).scalars().first()
        if not client:
            await callback.answer("Клиент не найден", show_alert=True)
            return

    # Формируем текст с информацией о заказе и клиенте
    location_info = ""
    if order.location_updated_at:
        time_diff = datetime.datetime.now() - order.location_updated_at
        if time_diff.total_seconds() < 3600:  # Меньше часа
            location_info = f"\n📍 Геолокация обновлена {int(time_diff.total_seconds() // 60)} мин. назад"
        else:
            location_info = f"\n📍 Геолокация обновлена {order.location_updated_at.strftime('%d.%m.%Y %H:%M')}"
    else:
        location_info = "\n📍 Геолокация не обновлялась"

    order_text = (
        f"🔍 Отслеживание заказа #{order.id}\n\n"
        f"Категория: {order.category}\n"
        f"Адрес: {order.address or '—'}\n"
        f"Клиент: {client.name or 'Не указано'}\n"
        f"Статус: {order.status}\n"
        f"Дата создания: {order.created_at.strftime('%d.%m.%Y %H:%M')}{location_info}"
    )

    # Отправляем информацию и клавиатуру действий
    try:
        await callback.message.edit_text(
            order_text,
            reply_markup=tracking_actions_keyboard(order.id)
        )
    except Exception:
        await callback.message.answer(
            order_text,
            reply_markup=tracking_actions_keyboard(order.id)
        )

    await callback.answer()


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
    # Удалено условие для MasterSetup.zones, так как больше не используется
    else:
        # Если не определено конкретное действие для текущего состояния
        await callback.answer("Действие недоступно в текущем состоянии")


# Обработчик setup_zones удален, так как районы больше не используются


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


@router.callback_query(F.data.startswith("complete_order:"))
async def complete_order(callback: CallbackQuery, state: FSMContext) -> None:
    """Завершить заказ мастером."""
    try:
        order_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    tg_id = callback.from_user.id
    logger.info("master_cb:complete_order", extra={"user_id": tg_id, "order_id": order_id})

    async with SessionFactory() as session:
        # Получаем мастера
        master = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not master:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

        # Получаем заказ
        order = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        # Проверяем, что заказ назначен этому мастеру
        if order.master_id != master.id:
            await callback.answer("Этот заказ не назначен вам", show_alert=True)
            return

        # Проверяем, что заказ в статусе "assigned"
        if order.status != "assigned":
            await callback.answer("Заказ не находится в работе", show_alert=True)
            return

        # Получаем клиента
        client = (await session.execute(select(User).where(User.id == order.client_id))).scalars().first()

        # Обновляем статус заказа
        order.status = "done"
        await session.commit()

    # Отправляем сообщение мастеру
    await callback.message.edit_text(
        f"Заказ #{order_id} отмечен как выполненный.\n"
        f"Клиент будет уведомлен о завершении заказа."
    )

    # Отправляем уведомление клиенту
    if client and client.tg_id:
        try:
            await callback.bot.send_message(
                chat_id=client.tg_id,
                text=(
                    f"✅ Ваш заказ #{order_id} выполнен!\n\n"
                    f"Мастер {master.name} отметил заказ как выполненный.\n"
                    f"Спасибо за использование нашего сервиса!"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Оценить работу", callback_data=f"rate_order:{order_id}")]
                ])
            )
        except Exception:
            logger.error("Failed to notify client", extra={"client_id": client.id, "order_id": order_id})

    await callback.answer("Заказ успешно завершен!", show_alert=True)


@router.callback_query(F.data.startswith("edit_bid_order:"))
async def edit_bid_by_order(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменить ставку по ID заказа."""
    try:
        order_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        # Получаем мастера
        master = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not master:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

        # Получаем ставку мастера на этот заказ
        bid = (await session.execute(
            select(Bid).where(Bid.order_id == order_id, Bid.master_id == master.id)
        )).scalars().first()

        if not bid:
            await callback.answer("Ставка не найдена", show_alert=True)
            return

    # Перенаправляем на обработчик изменения ставки
    await edit_bid_price(callback, state, bid_id=bid.id)


@router.callback_query(F.data.startswith("edit_bid:"))
async def edit_bid_price(callback: CallbackQuery, state: FSMContext, bid_id=None) -> None:
    """Инициировать изменение цены для своей активной ставки."""
    if bid_id is None:
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


# Обработчик master_pick_zones удален, так как районы больше не используются


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
            # Проверка зоны удалена, так как районы больше не используются

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
                
                # Уведомляем клиента об обновлении ставки
                try:
                    # Получаем заказ и клиента
                    order = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()
                    client = (await session.execute(select(User).where(User.id == order.client_id))).scalars().first()
                    
                    if client and client.tg_id:
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="Посмотреть предложения", callback_data=f"order_bids:{order.id}")]
                        ])
                        await message.bot.send_message(
                            chat_id=client.tg_id,
                            text=f"💰 Ставка обновлена по вашему заказу #{order.id}: {price} KZT от мастера {master.name or 'Мастер'}",
                            reply_markup=kb
                        )
                except Exception as e:
                    logger.error("Failed to notify client about bid update", extra={
                        "order_id": order_id, 
                        "client_id": order.client_id if order else None,
                        "error": str(e)
                    })
            else:
                bid = Bid(order_id=order_id, master_id=master.id, price=price)
                session.add(bid)
                await session.commit()
                await message.answer("Ставка отправлена! Ожидайте ответа клиента.")
                
                # Уведомляем клиента о новой ставке
                try:
                    # Получаем заказ и клиента
                    order = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()
                    client = (await session.execute(select(User).where(User.id == order.client_id))).scalars().first()
                    
                    if client and client.tg_id:
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="Посмотреть предложения", callback_data=f"order_bids:{order.id}")]
                        ])
                        await message.bot.send_message(
                            chat_id=client.tg_id,
                            text=f"💰 Новая ставка по вашему заказу #{order.id}: {price} KZT от мастера {master.name or 'Мастер'}",
                            reply_markup=kb
                        )
                except Exception as e:
                    logger.error("Failed to notify client about new bid", extra={
                        "order_id": order_id, 
                        "client_id": order.client_id if order else None,
                        "error": str(e)
                    })

    await state.clear()
