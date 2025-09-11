"""Handlers for tracking clients and location updates."""
import datetime
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from sqlalchemy import select

from app.bot.keyboards import (
    location_update_request_keyboard,
    tracking_actions_keyboard,
    tracking_orders_keyboard,
)
from app.bot.states import ClientActions, MasterActions
from app.models import Order, User
from core.db import SessionFactory

logger = logging.getLogger("bot.tracking")

router = Router()


@router.callback_query(F.data.startswith("request_location:"))
async def request_location_update(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик запроса обновления геолокации клиента."""
    try:
        order_id: int = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    tg_id: int = callback.from_user.id
    async with SessionFactory() as session:
        # Получаем мастера
        master: User | None = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not master or master.role != "master":
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        # Получаем заказ
        order: Order | None = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        # Проверяем, что заказ назначен этому мастеру
        if order.master_id != master.id:
            await callback.answer("Этот заказ не назначен вам", show_alert=True)
            return

        # Получаем клиента
        client: User | None = (await session.execute(select(User).where(User.id == order.client_id))).scalars().first()
        if not client or not client.tg_id:
            await callback.answer("Клиент не найден или не имеет Telegram ID", show_alert=True)
            return

        # Отправляем запрос клиенту на обновление геолокации
        try:
            await callback.bot.send_message(
                chat_id=client.tg_id,
                text=(
                    f"📍 Мастер {master.name or 'Ваш мастер'} запрашивает обновление вашей геолокации "
                    f"для заказа #{order.id}.\n\n"
                    f"Пожалуйста, поделитесь вашим текущим местоположением."
                ),
                reply_markup=location_update_request_keyboard(master.id)
            )

            # Сообщаем мастеру, что запрос отправлен
            await callback.message.answer(
                f"✅ Запрос на обновление геолокации отправлен клиенту {client.name or 'клиенту'}.\n"
                f"Вы получите уведомление, когда клиент обновит свою геолокацию."
            )

            logger.info(
                "location_update_requested",
                extra={
                    "master_id": master.id,
                    "client_id": client.id,
                    "order_id": order.id,
                }
            )
        except Exception as e:
            logger.error(
                "failed_to_send_location_request",
                extra={
                    "master_id": master.id,
                    "client_id": client.id,
                    "order_id": order.id,
                    "error": str(e)
                }
            )
            await callback.answer("Не удалось отправить запрос клиенту", show_alert=True)
            return

    await callback.answer("Запрос отправлен клиенту")


@router.callback_query(F.data.startswith("show_map:"))
async def show_client_location(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать местоположение клиента на карте."""
    try:
        order_id: int = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    tg_id: int = callback.from_user.id
    async with SessionFactory() as session:
        # Получаем мастера
        master: User | None = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not master or master.role != "master":
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        # Получаем заказ
        order: Order | None = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        # Проверяем, что заказ назначен этому мастеру
        if order.master_id != master.id:
            await callback.answer("Этот заказ не назначен вам", show_alert=True)
            return

        # Проверяем наличие координат
        if not order.latitude or not order.longitude:
            await callback.answer("Геолокация клиента не доступна", show_alert=True)
            return

        # Отправляем местоположение
        try:
            await callback.message.answer_location(
                latitude=order.latitude,
                longitude=order.longitude
            )

            # Добавляем информацию о времени обновления
            location_time_info: str = ""
            if order.location_updated_at:
                time_diff: datetime.timedelta = datetime.datetime.now() - order.location_updated_at
                if time_diff.total_seconds() < 3600:  # Меньше часа
                    location_time_info = f"Геолокация обновлена {int(time_diff.total_seconds() // 60)} мин. назад"
                else:
                    location_time_info = f"Геолокация обновлена {order.location_updated_at.strftime('%d.%m.%Y %H:%M')}"
            else:
                location_time_info = "Время обновления геолокации неизвестно"

            await callback.message.answer(f"📍 {location_time_info}")

        except Exception as e:
            logger.error(
                "failed_to_send_location",
                extra={
                    "master_id": master.id,
                    "order_id": order.id,
                    "error": str(e)
                }
            )
            await callback.answer("Не удалось отправить местоположение", show_alert=True)
            return

    await callback.answer()


@router.callback_query(F.data.startswith("contact_client:"))
async def contact_client(callback: CallbackQuery, state: FSMContext) -> None:
    """Связаться с клиентом."""
    try:
        order_id: int = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    tg_id: int = callback.from_user.id
    async with SessionFactory() as session:
        # Получаем мастера
        master: User | None = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not master or master.role != "master":
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        # Получаем заказ
        order: Order | None = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        # Проверяем, что заказ назначен этому мастеру
        if order.master_id != master.id:
            await callback.answer("Этот заказ не назначен вам", show_alert=True)
            return

        # Получаем клиента
        client: User | None = (await session.execute(select(User).where(User.id == order.client_id))).scalars().first()
        if not client:
            await callback.answer("Клиент не найден", show_alert=True)
            return

        # Отправляем контактную информацию
        contact_info: str = (
            f"📱 Контактная информация клиента:\n\n"
            f"Имя: {client.name or 'Не указано'}\n"
        )

        # Добавляем номер телефона, если есть
        if hasattr(client, 'phone') and client.phone:
            contact_info += f"Телефон: {client.phone}\n"
        else:
            contact_info += "Телефон: Не указан\n"

        # Добавляем Telegram username, если есть
        if hasattr(client, 'username') and client.username:
            contact_info += f"Telegram: @{client.username}\n"

        # Добавляем кнопку для отправки сообщения клиенту через бота
        keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Отправить сообщение клиенту",
                callback_data=f"message_client:{order.id}"
            )],
            [InlineKeyboardButton(
                text="« Назад к отслеживанию",
                callback_data=f"track_order:{order.id}"
            )]
        ])

        await callback.message.answer(contact_info, reply_markup=keyboard)

    await callback.answer()


@router.callback_query(F.data.startswith("message_client:"))
async def start_message_to_client(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать отправку сообщения клиенту."""
    try:
        order_id: int = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    # Сохраняем ID заказа в состоянии
    await state.update_data(message_order_id=order_id)

    # Устанавливаем состояние ожидания ввода сообщения
    await state.set_state(MasterActions.waiting_message)

    # Отправляем инструкцию
    cancel_keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Отмена", callback_data=f"track_order:{order_id}")]
    ])

    await callback.message.answer(
        "Введите сообщение для клиента:",
        reply_markup=cancel_keyboard
    )

    await callback.answer()


@router.callback_query(F.data.startswith("track_order:"))
async def track_order(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать действия для отслеживания конкретного заказа."""
    try:
        order_id: int = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор заказа", show_alert=True)
        return

    tg_id: int = callback.from_user.id
    async with SessionFactory() as session:
        # Получаем мастера
        master: User | None = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not master or master.role != "master":
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        # Получаем заказ
        order: Order | None = (await session.execute(select(Order).where(Order.id == order_id))).scalars().first()
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        # Проверяем, что заказ назначен этому мастеру
        if order.master_id != master.id:
            await callback.answer("Этот заказ не назначен вам", show_alert=True)
            return

        # Получаем клиента
        client: User | None = (await session.execute(select(User).where(User.id == order.client_id))).scalars().first()
        if not client:
            await callback.answer("Клиент не найден", show_alert=True)
            return

    # Отображаем информацию о заказе и действия для отслеживания
    order_info: str = (
        f"📦 Заказ #{order.id}\n"
        f"Категория: {order.category}\n"
        f"Клиент: {client.name or 'Не указано'}\n"
        f"Статус: {order.status}\n"
    )

    # Добавляем информацию о геолокации, если есть
    if order.latitude and order.longitude:
        order_info += f"\nГеолокация: {order.latitude}, {order.longitude}"
        if order.location_updated_at:
            time_diff: datetime.timedelta = datetime.datetime.now() - order.location_updated_at
            if time_diff.total_seconds() < 3600:  # Меньше часа
                order_info += f"\nОбновлена {int(time_diff.total_seconds() // 60)} мин. назад"
            else:
                order_info += f"\nОбновлена {order.location_updated_at.strftime('%d.%m.%Y %H:%M')}"
    else:
        order_info += "\nГеолокация: Не указана"

    await callback.message.edit_text(
        order_info,
        reply_markup=tracking_actions_keyboard(order.id)
    )

    await callback.answer()


@router.callback_query(F.data == "tracking:list")
async def show_tracking_list(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать список заказов для отслеживания."""
    tg_id: int = callback.from_user.id

    async with SessionFactory() as session:
        # Получаем мастера
        master: User | None = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not master or master.role != "master":
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        # Получаем активные заказы мастера
        orders_query = select(Order).where(
            Order.master_id == master.id,
            Order.status.in_(["assigned", "inprogress"])
        ).order_by(Order.created_at.desc())

        orders: list[Order] = (await session.execute(orders_query)).scalars().all()

    if not orders:
        await callback.message.edit_text(
            "У вас нет активных заказов для отслеживания."
        )
        return

    await callback.message.edit_text(
        "Выберите заказ для отслеживания:",
        reply_markup=tracking_orders_keyboard(orders)
    )

    await callback.answer()


@router.callback_query(F.data.startswith("update_location:"))
async def client_update_location_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик кнопки обновления геолокации клиентом."""
    try:
        master_id: int = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор мастера", show_alert=True)
        return

    # Сохраняем ID мастера в состоянии
    await state.update_data(location_master_id=master_id)

    # Устанавливаем состояние ожидания геолокации
    await state.set_state(ClientActions.waiting_location)

    # Создаем клавиатуру с кнопкой отправки геолокации
    from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
    location_keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.answer(
        "Пожалуйста, нажмите кнопку ниже, чтобы отправить вашу текущую геолокацию:",
        reply_markup=location_keyboard
    )

    await callback.answer()


@router.callback_query(F.data.startswith("decline_location:"))
async def client_decline_location(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик отказа клиента обновить геолокацию."""
    try:
        master_id: int = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный идентификатор мастера", show_alert=True)
        return

    async with SessionFactory() as session:
        # Получаем мастера
        master: User | None = (await session.execute(select(User).where(User.id == master_id))).scalars().first()
        if not master or not master.tg_id:
            await callback.answer("Мастер не найден", show_alert=True)
            return

        # Получаем клиента
        client_tg_id: int = callback.from_user.id
        client: User | None = (await session.execute(select(User).where(User.tg_id == client_tg_id))).scalars().first()
        if not client:
            await callback.answer("Клиент не найден", show_alert=True)
            return

        # Отправляем уведомление мастеру
        try:
            await callback.bot.send_message(
                chat_id=master.tg_id,
                text=f"❌ Клиент {client.name or 'клиент'} отказался обновить геолокацию."
            )
        except Exception:
            logger.error(
                "failed_to_notify_master_about_decline",
                extra={
                    "master_id": master.id,
                    "client_id": client.id
                }
            )

    await callback.message.edit_text("Вы отказались обновлять геолокацию.")
    await callback.answer()
