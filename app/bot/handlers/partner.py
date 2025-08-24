"""Partner role handlers - referral system and partner dashboard."""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from sqlalchemy import select, func

from app.bot.states import PartnerSetup
from app.models import Partner, User, Payout, Order
from core.db import SessionFactory
from app.bot.keyboards import main_menu_keyboard, add_back_button


logger = logging.getLogger("bot.partner")


router = Router()


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    """Показать главное меню партнера с кнопками."""
    await state.clear()
    await message.answer(
        "Главное меню партнера:",
        reply_markup=main_menu_keyboard()
    )


@router.message(F.text == "📊 Дашборд")
async def dashboard_button(message: Message) -> None:
    """Обработчик кнопки дашборда."""
    await cmd_partner_dashboard(message)


@router.message(F.text == "🔗 Реферальная ссылка")
async def ref_link_button(message: Message) -> None:
    """Обработчик кнопки реферальной ссылки."""
    # Делегируем существующей команде, чтобы избежать дублирования
    logger.info("partner_button:link", extra={"user_id": message.from_user.id})
    await cmd_partner_link(message)


@router.message(F.text == "💳 Выплаты")
async def payouts_button(message: Message) -> None:
    """Обработчик кнопки выплат."""
    logger.info("partner_button:payouts", extra={"user_id": message.from_user.id})
    await cmd_partner_payouts(message)


@router.message(F.text == "❓ Помощь")
async def help_button(message: Message) -> None:
    """Обработчик кнопки помощи."""
    help_text = (
        "📖 Помощь по использованию бота (режим партнера):\n\n"
        "Команды:\n"
        "/start - Начать работу с ботом\n"
        "/menu - Открыть главное меню\n"
        "/partner_stats - Показать статистику по рефералам\n"
        "/partner_link - Получить реферальную ссылку\n\n"
        "Как работает партнерская программа:\n"
        "1. Получите свою реферальную ссылку\n"
        "2. Приглашайте мастеров и клиентов по вашей ссылке\n"
        "3. Получайте % от каждого заказа приглашенных вами пользователей\n"
        "4. Отслеживайте статистику и выплаты в разделе 'Дашборд'\n\n"
        "Выплаты:\n"
        "- Выплаты производятся автоматически после завершения заказа\n"
        "- Вы можете запросить выплату в разделе 'Выплаты'\n"
    )
    
    await message.answer(help_text)


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
        
        # Добавляем кнопку для изменения роли
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить роль", callback_data="change_role")]
        ])
        
        await message.answer(profile_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("back:"))
async def handle_back_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик кнопки 'Назад' для всех состояний партнера."""
    back_to = callback.data.split(":", 1)[1] if ":" in callback.data else "main"
    current_state = await state.get_state()
    
    if back_to == "main" or not current_state:
        # Возврат в главное меню партнера
        await state.clear()
        try:
            await callback.message.edit_text(
                "Главное меню партнера:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📊 Дашборд", callback_data="partner:dashboard")],
                    [InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="partner:link")],
                    [InlineKeyboardButton(text="💳 Выплаты", callback_data="partner:payouts")]
                ])
            )
        except Exception:
            # Если не можем изменить текст сообщения, отправляем новое
            await callback.message.answer(
                "Главное меню партнера:",
                reply_markup=main_menu_keyboard()
            )
        await callback.answer("Возврат в главное меню")
    elif back_to == "partner_dashboard":
        # Возврат к дашборду партнера
        try:
            await cmd_partner_dashboard(callback.message)
            await callback.answer("Возврат к дашборду")
        except Exception:
            await callback.answer("Ошибка при возврате к дашборду")
    elif back_to == "role_select":
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


@router.message(Command("help_partner"))
async def cmd_help_partner(message: Message) -> None:
    """Partner help command with available functions."""
    help_text = (
        "🤝 Партнерская система\n\n"
        "Доступные команды:\n"
        "/partner_stats - Статистика по рефералам\n"
        "/partner_link - Получить реферальную ссылку\n"
        "/partner_payouts - История выплат\n"
        "/partner_dashboard - Общая статистика"
    )
    await message.answer(help_text)


@router.message(Command("partner_link"))
async def cmd_partner_link(message: Message) -> None:
    """Generate and show partner referral link."""
    tg_id = message.from_user.id
    logger.info("partner_cmd:link", extra={"user_id": tg_id})
    
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or user.role != "partner":
            await message.answer("Вы не зарегистрированы как партнер. Используйте /start для выбора роли.")
            return
            
        partner = (await session.execute(select(Partner).where(Partner.user_id == user.id))).scalars().first()
        if not partner:
            # Create partner record
            partner = Partner(
                user_id=user.id,
                slug=f"partner_{user.tg_id}",
                referral_code=f"REF{user.tg_id:08d}"
            )
            session.add(partner)
            await session.commit()
            
        # Fetch bot username reliably via get_me()
        try:
            me = await message.bot.get_me()
            username = getattr(me, "username", None)
        except Exception:
            username = None

        referral_link = None
        if username:
            referral_link = f"https://t.me/{username}?start={partner.referral_code}"
        else:
            logger.warning(
                "partner_link:no_username",
                extra={"user_id": tg_id}
            )
        
    if referral_link:
        await message.answer(
            f"🔗 Ваша реферальная ссылка:\n{referral_link}\n\n"
            f"Код: {partner.referral_code}\n\n"
            f"Делитесь этой ссылкой и получайте 5% от заказов приведенных клиентов!"
        )
    else:
        await message.answer(
            f"Код: {partner.referral_code}\n\n"
            "Не удалось получить username бота для формирования ссылки. Откройте бота и введите код вручную."
        )


@router.message(Command("partner_stats"))
async def cmd_partner_stats(message: Message) -> None:
    """Show partner statistics."""
    tg_id = message.from_user.id
    logger.info("partner_cmd:stats", extra={"user_id": tg_id})
    
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or user.role != "partner":
            await message.answer("Вы не зарегистрированы как партнер.")
            return
            
        partner = (await session.execute(select(Partner).where(Partner.user_id == user.id))).scalars().first()
        if not partner:
            await message.answer("Партнерская запись не найдена.")
            return
            
        # Count referred users
        referred_users = (await session.execute(
            select(func.count(User.id)).where(User.referrer_id == user.id)
        )).scalar()
        
        # Count completed orders with commission
        completed_orders = (await session.execute(
            select(func.count(Payout.id))
            .join(Order, Payout.order_id == Order.id)
            .join(User, Order.client_id == User.id)
            .where(User.referrer_id == user.id)
            .where(Payout.status == "paid")
        )).scalar()
        
        total_earned = (await session.execute(
            select(func.coalesce(func.sum(Payout.amount_partner), 0))
            .join(Order, Payout.order_id == Order.id)
            .join(User, Order.client_id == User.id)
            .where(User.referrer_id == user.id)
            .where(Payout.status == "paid")
        )).scalar()
        
    stats_text = (
        f"📊 Ваша партнерская статистика:\n\n"
        f"👥 Приведено клиентов: {referred_users}\n"
        f"✅ Выполнено заказов: {completed_orders}\n"
        f"💰 Заработано: {total_earned} KZT\n"
        f"📈 Процент: 5% от каждого заказа"
    )
    await message.answer(stats_text)


@router.message(Command("partner_payouts"))
async def cmd_partner_payouts(message: Message) -> None:
    """Show partner payout history."""
    tg_id = message.from_user.id
    logger.info("partner_cmd:payouts", extra={"user_id": tg_id})
    
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or user.role != "partner":
            await message.answer("Вы не зарегистрированы как партнер.")
            return
            
        payouts = (await session.execute(
            select(Payout).join(Order, Payout.order_id == Order.id)
            .join(User, Order.client_id == User.id)
            .where(User.referrer_id == user.id)
            .order_by(Payout.created_at.desc())
            .limit(10)
        )).scalars().all()
        
    if not payouts:
        await message.answer("У вас еще нет выплат.")
        return
    
    status_human = {
        "pending": "🕐 Ожидает выплаты",
        "paid": "✅ Выплачено",
        "failed": "❌ Отклонена",
    }
    payouts_text = "💳 История выплат:\n\n"
    for payout in payouts:
        st = status_human.get(payout.status, payout.status)
        payouts_text += (
            f"Заказ #{payout.order_id}: {payout.amount_partner} KZT\n"
            f"Статус: {st}\n"
            f"Дата: {payout.created_at.strftime('%d.%m.%Y')}\n\n"
        )
    
    await message.answer(payouts_text)


@router.message(Command("partner_dashboard"))
async def cmd_partner_dashboard(message: Message) -> None:
    """Show comprehensive partner dashboard."""
    tg_id = message.from_user.id
    logger.info("partner_cmd:dashboard", extra={"user_id": tg_id})
    
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user or user.role != "partner":
            await message.answer("Вы не зарегистрированы как партнер.")
            return
            
        partner = (await session.execute(select(Partner).where(Partner.user_id == user.id))).scalars().first()
        if not partner:
            await message.answer("Партнерская запись не найдена.")
            return
            
        # Get comprehensive stats
        stats = await get_partner_statistics(session, user.id)
        
    dashboard_text = (
        f"🎯 Партнерский дашборд\n\n"
        f"🔗 Код: {partner.referral_code}\n"
        f"📊 Статистика:\n"
        f"  • Приведено клиентов: {stats['referred_users']}\n"
        f"  • Активных заказов: {stats['active_orders']}\n"
        f"  • Выполнено заказов: {stats['completed_orders']}\n"
        f"  • Ожидают оплаты: {stats['pending_payouts']}\n"
        f"\n💰 Финансы:\n"
        f"  • Всего заработано: {stats['total_earned']} KZT\n"
        f"  • Ожидает выплаты: {stats['pending_amount']} KZT\n"
        f"  • Средний чек: {stats['avg_order_value']} KZT"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Детальная статистика", callback_data="partner_detailed_stats")],
        [InlineKeyboardButton(text="🔗 Получить ссылку", callback_data="partner_get_link")],
        [InlineKeyboardButton(text="💳 Запросить выплату", callback_data="partner_request_payout")],
        [InlineKeyboardButton(text="« Назад", callback_data="back:main")]
    ])
    
    await message.answer(dashboard_text, reply_markup=keyboard)


async def get_partner_statistics(session, partner_user_id):
    """Get comprehensive partner statistics."""
    referred_users = (await session.execute(
        select(func.count(User.id)).where(User.referrer_id == partner_user_id)
    )).scalar()
    
    active_orders = (await session.execute(
        select(func.count(Order.id))
        .join(User, Order.client_id == User.id)
        .where(User.referrer_id == partner_user_id)
        .where(Order.status == "assigned")
    )).scalar()
    
    completed_orders = (await session.execute(
        select(func.count(Payout.id))
        .join(Order, Payout.order_id == Order.id)
        .join(User, Order.client_id == User.id)
        .where(User.referrer_id == partner_user_id)
        .where(Payout.status == "paid")
    )).scalar()
    
    pending_payouts = (await session.execute(
        select(func.count(Payout.id))
        .join(Order, Payout.order_id == Order.id)
        .join(User, Order.client_id == User.id)
        .where(User.referrer_id == partner_user_id)
        .where(Payout.status == "pending")
    )).scalar()
    
    total_earned = (await session.execute(
        select(func.coalesce(func.sum(Payout.amount_partner), 0))
        .join(Order, Payout.order_id == Order.id)
        .join(User, Order.client_id == User.id)
        .where(User.referrer_id == partner_user_id)
        .where(Payout.status == "paid")
    )).scalar()
    
    pending_amount = (await session.execute(
        select(func.coalesce(func.sum(Payout.amount_partner), 0))
        .join(Order, Payout.order_id == Order.id)
        .join(User, Order.client_id == User.id)
        .where(User.referrer_id == partner_user_id)
        .where(Payout.status == "pending")
    )).scalar()
    
    avg_order_value = (await session.execute(
        select(func.coalesce(func.avg(Payout.amount_partner * 20), 0))
        .join(Order, Payout.order_id == Order.id)
        .join(User, Order.client_id == User.id)
        .where(User.referrer_id == partner_user_id)
    )).scalar()
    
    return {
        'referred_users': referred_users,
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'pending_payouts': pending_payouts,
        'total_earned': total_earned,
        'pending_amount': pending_amount,
        'avg_order_value': int(avg_order_value) if avg_order_value else 0
    }


@router.callback_query(F.data == "partner_detailed_stats")
async def partner_detailed_stats(callback: CallbackQuery) -> None:
    """Show detailed partner statistics."""
    await callback.answer()
    await cmd_partner_stats(callback.message)


@router.callback_query(F.data == "partner_get_link")
async def partner_get_link_callback(callback: CallbackQuery) -> None:
    """Show partner link via callback."""
    await callback.answer()
    await cmd_partner_link(callback.message)


@router.callback_query(F.data == "partner_request_payout")
async def partner_request_payout(callback: CallbackQuery) -> None:
    """Handle payout request from partner."""
    await callback.answer()
    await callback.message.answer(
        "💳 Запрос на выплату отправлен администратору.\n"
        "Минимальная сумма для выплаты: 1000 KZT\n"
        "Выплаты производятся каждую пятницу."
    )
