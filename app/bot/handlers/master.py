"""Handlers for мастер role: setup zones and create bids."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from sqlalchemy import select

from app.bot.keyboards import zones_keyboard_master_full
from app.bot.states import BidCreate, MasterSetup
from app.models import Bid, User
from core.db import SessionFactory

router = Router()


@router.message(Command("help_master"))
async def cmd_help_master(message: Message) -> None:
    await message.answer(
        "Вы мастер. Используйте /start чтобы выбрать роль и настроить районы обслуживания."
    )


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
        reply_markup=zones_keyboard_master_full(selected),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bid:"))
async def start_bid(callback: CallbackQuery, state: FSMContext) -> None:
    order_id = int(callback.data.split(":", 1)[1])
    await state.update_data(order_id=order_id)
    await state.set_state(BidCreate.price)
    await callback.message.answer("Введите вашу цену (только число, KZT):")
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
