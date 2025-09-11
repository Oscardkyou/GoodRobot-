"""Chat handlers: start/exit chat sessions and relay messages between client and master.

MVP flow:
- Clients and Masters open chat from main menu ("💬 Чат") or from tracking via "open_chat:{order_id}".
- Chat session is created (or reused if active) bound to an Order and users.
- Messages are relayed via the bot; supported: text, photo, video, voice, document.
- Users can close chat via inline button; status switches to 'closed'.

Safety notes:
- We store minimal message metadata (text or file_id) in DB.
- We ensure role validation and that order belongs to users.
"""
from __future__ import annotations

import datetime
import logging
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import and_, select

from app.bot.states import ClientActions, MasterActions
from app.models import ChatMessage, ChatSession, Order, User
from core.db import SessionFactory

logger = logging.getLogger("bot.chat")

router = Router()


# ===== Keyboards =====

def chat_actions_keyboard(session_id: int, order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Закрыть чат", callback_data=f"close_chat:{session_id}")],
            [InlineKeyboardButton(text="« Назад к заказу", callback_data=f"track_order:{order_id}")],
        ]
    )


def chat_orders_keyboard(orders) -> InlineKeyboardMarkup:
    buttons = []
    for order in orders:
        buttons.append([
            InlineKeyboardButton(text=f"Заказ #{order.id}: {order.category}", callback_data=f"open_chat:{order.id}")
        ])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ===== Entry points =====

@router.message(F.text == "💬 Чат")
async def chat_menu(message: Message, state: FSMContext) -> None:
    """Show list of active/in-progress orders for the user to open chat."""
    tg_id = message.from_user.id
    async with SessionFactory() as session:
        user: Optional[User] = (
            await session.execute(select(User).where(User.tg_id == tg_id))
        ).scalars().first()
        if not user:
            await message.answer("Пользователь не найден. Нажмите /start")
            return

        if user.role == "master":
            orders = (
                await session.execute(
                    select(Order)
                    .where(
                        and_(
                            Order.master_id == user.id,
                            Order.status.in_(["assigned"]),
                        )
                    )
                    .order_by(Order.created_at.desc())
                )
            ).scalars().all()
        else:  # client and others
            orders = (
                await session.execute(
                    select(Order)
                    .where(
                        and_(
                            Order.client_id == user.id,
                            Order.status.in_(["assigned"]),
                        )
                    )
                    .order_by(Order.created_at.desc())
                )
            ).scalars().all()

    if not orders:
        await message.answer("Нет активных заказов для чата.")
        return

    await message.answer("Выберите заказ для чата:", reply_markup=chat_orders_keyboard(orders))


@router.callback_query(F.data.startswith("open_chat:"))
async def open_chat(callback: CallbackQuery, state: FSMContext) -> None:
    """Create or reuse active chat session for order and move user into waiting_message state."""
    try:
        order_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный ID заказа", show_alert=True)
        return

    tg_id = callback.from_user.id

    async with SessionFactory() as session:
        user: Optional[User] = (
            await session.execute(select(User).where(User.tg_id == tg_id))
        ).scalars().first()
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        order: Optional[Order] = (
            await session.execute(select(Order).where(Order.id == order_id))
        ).scalars().first()
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        # Validate membership
        if user.role == "master":
            if order.master_id != user.id:
                await callback.answer("Заказ не назначен вам", show_alert=True)
                return
            other: Optional[User] = (
                await session.execute(select(User).where(User.id == order.client_id))
            ).scalars().first()
        else:  # client
            if order.client_id != user.id:
                await callback.answer("Это не ваш заказ", show_alert=True)
                return
            other = (
                await session.execute(select(User).where(User.id == order.master_id))
            ).scalars().first()

        if not other or not other.tg_id:
            await callback.answer("Второй участник недоступен", show_alert=True)
            return

        # Find or create active session
        session_obj: Optional[ChatSession] = (
            await session.execute(
                select(ChatSession).where(
                    ChatSession.order_id == order.id, ChatSession.status == "active"
                )
            )
        ).scalars().first()
        if not session_obj:
            session_obj = ChatSession(
                order_id=order.id,
                client_id=order.client_id,
                master_id=order.master_id,
                status="active",
                started_at=datetime.datetime.utcnow(),
                last_activity_at=datetime.datetime.utcnow(),
            )
            session.add(session_obj)
            await session.flush()  # get PK
            await session.commit()

    # Set FSM state and context
    if user.role == "master":
        await state.set_state(MasterActions.waiting_message)
    else:
        await state.set_state(ClientActions.waiting_message)
    await state.update_data(
        chat_session_id=session_obj.id,
        order_id=order.id,
        peer_tg_id=other.tg_id,
    )

    # Notify and present controls
    try:
        await callback.message.answer(
            (
                "Чат открыт. Отправляйте сообщения.\n"
                "Можно отправлять текст, фото, видео, голосовые и документы."
            ),
            reply_markup=chat_actions_keyboard(session_obj.id, order.id),
        )
    except Exception:
        pass

    await callback.answer("Чат открыт")


@router.callback_query(F.data.startswith("close_chat:"))
async def close_chat(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        session_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Некорректный ID чата", show_alert=True)
        return

    tg_id = callback.from_user.id
    now = datetime.datetime.utcnow()

    async with SessionFactory() as db:
        cs: Optional[ChatSession] = (
            await db.execute(select(ChatSession).where(ChatSession.id == session_id))
        ).scalars().first()
        if not cs:
            await callback.answer("Чат не найден", show_alert=True)
            return

        # Verify requester belongs to chat
        u: Optional[User] = (
            await db.execute(select(User).where(User.tg_id == tg_id))
        ).scalars().first()
        if not u or (u.id not in (cs.client_id, cs.master_id)):
            await callback.answer("Нет доступа к чату", show_alert=True)
            return

        cs.status = "closed"
        cs.closed_at = now
        cs.last_activity_at = now
        await db.commit()

        # Determine peer
        peer_id = cs.master_id if u.id == cs.client_id else cs.client_id
        peer: Optional[User] = (
            await db.execute(select(User).where(User.id == peer_id))
        ).scalars().first()

    await state.clear()

    # Notify both
    await callback.message.answer("Чат закрыт.")
    if peer and peer.tg_id:
        try:
            await callback.bot.send_message(peer.tg_id, "Чат был закрыт вторым участником.")
        except Exception:
            pass

    await callback.answer()


# ===== Relay helpers =====

async def persist_message(
    db_session,
    session_id: int,
    sender_id: int,
    receiver_id: int,
    message_type: str,
    content_text: Optional[str] = None,
    file_id: Optional[str] = None,
) -> None:
    msg = ChatMessage(
        session_id=session_id,
        sender_id=sender_id,
        receiver_id=receiver_id,
        message_type=message_type,
        content_text=content_text,
        file_id=file_id,
    )
    db_session.add(msg)
    # Update activity on session
    cs = (
        await db_session.execute(select(ChatSession).where(ChatSession.id == session_id))
    ).scalars().first()
    if cs:
        cs.last_activity_at = datetime.datetime.utcnow()
    await db_session.commit()


async def relay_to_peer(message: Message, state: FSMContext, role: str) -> None:
    data = await state.get_data()
    session_id = data.get("chat_session_id")
    peer_tg_id = data.get("peer_tg_id")
    order_id = data.get("order_id")

    if not session_id or not peer_tg_id:
        await message.answer("Чат не инициализирован. Откройте чат снова.")
        return

    sender_tg = message.from_user.id

    # Determine type and send
    sent_ok = False
    msg_type = "text"
    text: Optional[str] = None
    file_id: Optional[str] = None

    try:
        if message.text:
            text = message.text
            await message.bot.send_message(peer_tg_id, text)
            msg_type = "text"
            sent_ok = True
        elif message.photo:
            # largest size last
            file_id = message.photo[-1].file_id
            caption = message.caption or ""
            await message.bot.send_photo(peer_tg_id, file_id, caption=caption or None)
            msg_type = "photo"
            text = caption or None
            sent_ok = True
        elif message.video:
            file_id = message.video.file_id
            caption = message.caption or ""
            await message.bot.send_video(peer_tg_id, file_id, caption=caption or None)
            msg_type = "video"
            text = caption or None
            sent_ok = True
        elif message.voice:
            file_id = message.voice.file_id
            await message.bot.send_voice(peer_tg_id, file_id)
            msg_type = "voice"
            sent_ok = True
        elif message.document:
            file_id = message.document.file_id
            caption = message.caption or ""
            await message.bot.send_document(peer_tg_id, file_id, caption=caption or None)
            msg_type = "document"
            text = caption or None
            sent_ok = True
        else:
            await message.answer("Этот тип сообщения не поддерживается в чате.")
            return
    except Exception as e:
        logger.error("chat_relay_failed", extra={"error": str(e)})
        await message.answer("Не удалось отправить сообщение. Попробуйте позже.")
        return

    if not sent_ok:
        return

    # Persist in DB
    async with SessionFactory() as db:
        sender: Optional[User] = (
            await db.execute(select(User).where(User.tg_id == sender_tg))
        ).scalars().first()
        receiver: Optional[User] = (
            await db.execute(select(User).where(User.tg_id == peer_tg_id))
        ).scalars().first()
        if sender and receiver:
            await persist_message(
                db_session=db,
                session_id=session_id,
                sender_id=sender.id,
                receiver_id=receiver.id,
                message_type=msg_type,
                content_text=text,
                file_id=file_id,
            )

    # Keep controls visible for the sender
    try:
        await message.answer("✓ Отправлено", reply_markup=chat_actions_keyboard(session_id, order_id))
    except Exception:
        pass


# Masters relay
@router.message(MasterActions.waiting_message)
async def master_relay(message: Message, state: FSMContext) -> None:
    await relay_to_peer(message, state, role="master")


# Clients relay
@router.message(ClientActions.waiting_message)
async def client_relay(message: Message, state: FSMContext) -> None:
    await relay_to_peer(message, state, role="client")
