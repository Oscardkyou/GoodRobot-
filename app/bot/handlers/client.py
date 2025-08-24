"""Client (заказчик) handlers and order creation flow."""
import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from sqlalchemy import select, func

from app.bot.keyboards import (
    categories_keyboard,
    confirm_keyboard,
    media_keyboard,
    role_keyboard,
    zones_keyboard,
    main_menu_keyboard,
    add_back_button,
)
from app.bot.states import MasterSetup, OrderCreate
from app.models import Order, User, Partner, Bid
from core.db import SessionFactory

logger = logging.getLogger("bot.client")

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
    logger.info("client_cb:choose_role", extra={"user_id": tg_id, "role": role})
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
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(OrderCreate.category, F.data.startswith("cat:"))
async def create_pick_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    logger.info("client_cb:pick_category", extra={"user_id": callback.from_user.id, "category": category})
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
    logger.info("client_cb:pick_zone", extra={"user_id": callback.from_user.id, "zone": zone})
    await callback.message.edit_text(
        f"Район: {zone}\nТеперь отправьте адрес (текстом):"
    )
    await state.set_state(OrderCreate.address)
    await callback.answer()


@router.message(OrderCreate.address)
async def create_address(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пожалуйста, отправьте адрес текстом.")
        return
    tg_id = message.from_user.id
    logger.info("client_msg:address", extra={"user_id": tg_id, "len": len(text)})
    await state.update_data(address=text)
    await message.answer(
        "Теперь можете загрузить фото/видео проблемы (можно несколько). Когда закончите — нажмите «Готово» или «Пропустить».",
        reply_markup=media_keyboard(with_back=True)
    )
    await state.set_state(OrderCreate.media)


@router.message(OrderCreate.media, F.photo)
async def create_media_photo(message: Message, state: FSMContext) -> None:
    """Сохраняем фото (берём максимальное качество)."""
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    media = list(data.get("media", []) or [])
    media.append(f"photo:{file_id}")
    await state.update_data(media=media)
    logger.info("client_msg:add_media", extra={"user_id": message.from_user.id, "type": "photo", "count": len(media)})
    await message.answer(
        "Фото добавлено. Можете отправить ещё фото/видео или нажмите «Готово».",
        reply_markup=media_keyboard(with_back=True)
    )


@router.message(OrderCreate.media, F.video)
async def create_media_video(message: Message, state: FSMContext) -> None:
    file_id = message.video.file_id
    data = await state.get_data()
    media = list(data.get("media", []) or [])
    media.append(f"video:{file_id}")
    await state.update_data(media=media)
    logger.info("client_msg:add_media", extra={"user_id": message.from_user.id, "type": "video", "count": len(media)})
    await message.answer(
        "Видео добавлено. Можете отправить ещё фото/видео или нажмите «Готово».",
        reply_markup=media_keyboard(with_back=True)
    )


@router.message(OrderCreate.media)
async def create_media_any(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Пришлите фото/видео или нажмите «Готово»/«Пропустить».",
        reply_markup=media_keyboard(with_back=True)
    )


@router.callback_query(OrderCreate.media, F.data == "media:done")
@router.callback_query(OrderCreate.media, F.data == "media:skip")
async def media_done_or_skip(callback: CallbackQuery, state: FSMContext) -> None:
    logger.info("client_cb:media_finish", extra={"user_id": callback.from_user.id, "action": callback.data})
    await callback.message.edit_text("Опишите проблему/задачу (текстом):")
    await state.set_state(OrderCreate.description)
    await callback.answer()


@router.message(OrderCreate.description)
async def create_description(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое описание для заказа.")
        return
    logger.info("client_msg:description", extra={"user_id": message.from_user.id, "len": len(message.text.strip())})
    await state.update_data(description=message.text.strip())
    data = await state.get_data()
    media_count = len(data.get("media", []) or [])
    summary = (
        "Проверьте заявку:\n"
        f"Категория: {data.get('category')}\n"
        f"Район: {data.get('zone')}\n"
        f"Адрес: {data.get('address')}\n"
        f"Медиа: {media_count} файл(ов)\n"
        f"Описание: {data.get('description')}\n"
    )
    await message.answer(summary, reply_markup=confirm_keyboard(with_back=True))
    await state.set_state(OrderCreate.confirm)


@router.callback_query(StateFilter(OrderCreate.category, OrderCreate.zone, OrderCreate.media, OrderCreate.description, OrderCreate.confirm), F.data.startswith("back:"))
async def handle_back_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик кнопки 'Назад' для всех состояний."""
    back_to = callback.data.split(":", 1)[1] if ":" in callback.data else "main"
    current_state = await state.get_state()
    
    logger.info("client_cb:back", extra={"user_id": callback.from_user.id, "back_to": back_to, "state": str(current_state)})
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
    elif back_to == "address" and current_state == OrderCreate.media:
        # Возврат к вводу адреса
        await callback.message.edit_text(
            "Теперь отправьте адрес (текстом):",
        )
        await state.set_state(OrderCreate.address)
        await callback.answer("Возврат к адресу")
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


@router.callback_query(F.data == "back:main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться в главное меню клиента вне FSM состояний создания заказа."""
    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or user.role != "client":
            # Пусть это обработают другие роутеры (например, мастер)
            return
    logger.info("client_cb:back_main", extra={"user_id": tg_id})
    await state.clear()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer("Возврат в главное меню")


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    """Показать главное меню с кнопками."""
    tg_id = message.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        # Обрабатываем меню только для клиентов; иначе передаем обработку другим роутерам
        if not user or user.role != "client":
            return
    logger.info("client_cmd:menu", extra={"user_id": tg_id})
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard()
    )


@router.message(F.text == "📝 Создать заказ")
async def create_order_button(message: Message, state: FSMContext) -> None:
    """Обработчик кнопки создания заказа."""
    logger.info("client_button:create_order", extra={"user_id": message.from_user.id})
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
        logger.info("client_button:my_orders", extra={"user_id": tg_id, "orders_count": len(orders)})
    
    if not orders:
        await message.answer("У вас пока нет заказов. Создайте новый заказ с помощью кнопки 'Создать заказ'.")
        return
        
    for order in orders[:5]:  # Показываем последние 5 заказов
        # Подсчёт количества ставок по заказу
        try:
            async with SessionFactory() as session:
                bids_count = (
                    await session.execute(
                        select(func.count(Bid.id)).where(Bid.order_id == order.id)
                    )
                ).scalar() or 0
        except Exception:
            bids_count = 0
        status_text = {
            "new": "🔵 Новый",
            "assigned": "🟡 В работе",
            "done": "🟢 Завершен",
            "cancelled": "🔴 Отменен",
        }.get(order.status, "🔵 Новый")
        
        order_text = (
            f"Заказ #{order.id}: {status_text}\n"
            f"Категория: {order.category}\n"
            f"Район: {order.zone}\n"
            f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"Ставки мастеров: {bids_count}\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подробнее", callback_data=f"order:{order.id}")]
        ])
        
        await message.answer(order_text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("order:"))
async def view_order_client(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать детали заказа для клиента (по кнопке 'Подробнее')."""
    try:
        order_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    tg_id = callback.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        order = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()
        bids_count = (
            await session.execute(select(func.count(Bid.id)).where(Bid.order_id == order_id))
        ).scalar() or 0

    logger.info("client_cb:view_order", extra={"user_id": tg_id, "order_id": order_id, "bids_count": int(bids_count or 0)})
    if not order or not user or order.client_id != user.id:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    status_text = {
        "new": "🔵 Новый",
        "assigned": "🟡 В работе",
        "done": "🟢 Завершен",
        "cancelled": "🔴 Отменен",
    }.get(order.status, order.status)

    text = (
        f"📦 Заказ #{order.id}\n"
        f"Статус: {status_text}\n"
        f"Категория: {order.category}\n"
        f"Район: {order.zone}\n"
        f"Адрес: {order.address or '—'}\n"
        f"Описание: {order.description or '—'}\n"
        f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"Ставки мастеров: {bids_count}\n"
    )

    keyboard_rows = []
    keyboard_rows.append([InlineKeyboardButton(text=f"Ставки ({bids_count})", callback_data=f"order_bids:{order.id}")])
    keyboard_rows.append([InlineKeyboardButton(text="« Назад", callback_data="back:main")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)

    # Отправляем медиа вложения отдельными сообщениями (если есть)
    if order.media:
        for m in (order.media or [])[:10]:  # ограничим до 10 вложений
            try:
                if isinstance(m, str) and m.startswith("photo:"):
                    await callback.message.answer_photo(m.split(":", 1)[1])
                elif isinstance(m, str) and m.startswith("video:"):
                    await callback.message.answer_video(m.split(":", 1)[1])
            except Exception:
                pass
    await callback.answer()

@router.message(F.text == "🔍 Поиск")
async def search_button(message: Message) -> None:
    """Обработчик кнопки поиска."""
    logger.info("client_button:search", extra={"user_id": message.from_user.id})
    await message.answer(
        "Функция поиска находится в разработке. Скоро вы сможете искать мастеров по категориям и районам."
    )


@router.message(F.text == "👨‍🔧 Профиль")
async def profile_button(message: Message) -> None:
    """Обработчик кнопки профиля."""
    tg_id = message.from_user.id
    
    logger.info("client_button:profile", extra={"user_id": tg_id})
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
    
    logger.info("client_button:help", extra={"user_id": message.from_user.id})
    await message.answer(help_text)


@router.callback_query(OrderCreate.confirm, F.data.startswith("confirm:"))
async def create_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    decision = callback.data.split(":", 1)[1]
    logger.info("client_cb:confirm", extra={"user_id": callback.from_user.id, "decision": decision})
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
            media=data.get("media"),
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
                    User.zones.any(data.get("zone"))
                )
            )
        ).scalars().all()

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
                        f"Район: {data.get('zone')}\n"
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
