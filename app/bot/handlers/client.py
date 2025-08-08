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
)
from app.bot.states import MasterSetup, OrderCreate
from app.models import Order, User
from core.db import SessionFactory

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Greet user, ensure DB record, propose role selection."""
    tg_id = message.from_user.id
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            user = User(tg_id=tg_id, name=message.from_user.full_name or None)
            session.add(user)
            await session.commit()

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
            reply_markup=categories_keyboard(),
        )
        await state.set_state(OrderCreate.category)
    elif role == "master":
        from app.bot.keyboards import zones_keyboard_master
        await callback.message.edit_text(
            "Вы выбрали роль Мастер. Укажите районы обслуживания (можно выбрать несколько):",
            reply_markup=zones_keyboard_master(),
        )
        await state.set_state(MasterSetup.zones)
    else:
        await callback.message.edit_text("Вы выбрали роль Партнёр. Функционал скоро будет доступен.")
    await callback.answer()


@router.callback_query(OrderCreate.category, F.data.startswith("cat:"))
async def create_pick_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    await callback.message.edit_text(
        f"Категория: {category}\nТеперь выберите район:",
        reply_markup=zones_keyboard(),
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
    await message.answer(summary, reply_markup=confirm_keyboard())
    await state.set_state(OrderCreate.confirm)


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
