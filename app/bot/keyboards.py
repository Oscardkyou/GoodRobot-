"""Inline keyboards for bot flows."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def add_back_button(keyboard: InlineKeyboardMarkup, callback_data: str = "back") -> InlineKeyboardMarkup:
    """Добавляет кнопку 'Назад' к любой клавиатуре."""
    keyboard_dict = keyboard.model_dump()
    keyboard_dict['inline_keyboard'].append([InlineKeyboardButton(text="« Назад", callback_data=callback_data)])
    return InlineKeyboardMarkup.model_validate(keyboard_dict)


def role_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Я клиент", callback_data="role:client"),
            InlineKeyboardButton(text="Я мастер", callback_data="role:master"),
        ],
        [InlineKeyboardButton(text="Я партнёр", callback_data="role:partner")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


CATEGORIES = [
    "Электрика",
    "Сантехника",
    "Бытовая техника",
    "Клининг",
    "Строительные работы",
]


def categories_keyboard(with_back: bool = True) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, name in enumerate(CATEGORIES, start=1):
        row.append(InlineKeyboardButton(text=name, callback_data=f"category:{name}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    
    if with_back:
        return add_back_button(keyboard, "back:main")
    return keyboard


# Районы были удалены из системы


# Районы были удалены из системы


# Районы были удалены из системы


# Районы были удалены из системы


def confirm_keyboard(with_back: bool = False) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data="confirm:yes"),
                InlineKeyboardButton(text="Отмена", callback_data="confirm:no"),
            ]
        ]
    )
    
    if with_back:
        return add_back_button(keyboard, "back:confirm")
    return keyboard


def media_keyboard(with_back: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура для шага загрузки медиа (фото/видео)."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Готово", callback_data="media:done"),
                InlineKeyboardButton(text="Пропустить", callback_data="media:skip"),
            ]
        ]
    )
    if with_back:
        return add_back_button(keyboard, "back:address")
    return keyboard


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Основное меню бота с кнопками для клиентов."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Создать заказ"), KeyboardButton(text="📋 Мои заказы")],
            [KeyboardButton(text="👨‍🔧 Профиль"), KeyboardButton(text="🔍 Поиск")],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True
    )


def master_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню мастера с основными действиями."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Заказы поблизости"), KeyboardButton(text="💰 Мои ставки")],
            [KeyboardButton(text="🔍 Отслеживание клиентов"), KeyboardButton(text="📝 Мои заказы")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True
    )


def partner_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для партнерского дашборда."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="partner:stats"),
                InlineKeyboardButton(text="💰 Выплаты", callback_data="partner:payouts"),
            ],
            [
                InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="partner:link"),
                InlineKeyboardButton(text="👥 Рефералы", callback_data="partner:referrals"),
            ],
        ]
    )
    return keyboard


def tracking_orders_keyboard(orders) -> InlineKeyboardMarkup:
    """Клавиатура для выбора заказа для отслеживания."""
    buttons = []
    for order in orders:
        buttons.append([InlineKeyboardButton(
            text=f"Заказ #{order.id}: {order.category}", 
            callback_data=f"track_order:{order.id}"
        )])
    
    # Добавляем кнопку возврата в меню
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tracking_actions_keyboard(order_id) -> InlineKeyboardMarkup:
    """Клавиатура действий для отслеживания заказа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Запросить обновление геолокации", callback_data=f"request_location:{order_id}")],
        [InlineKeyboardButton(text="🗺️ Показать на карте", callback_data=f"show_map:{order_id}")],
        [InlineKeyboardButton(text="📱 Связаться с клиентом", callback_data=f"contact_client:{order_id}")],
        [InlineKeyboardButton(text="« Назад к заказам", callback_data="tracking:list")]
    ])


def location_update_request_keyboard(master_id) -> InlineKeyboardMarkup:
    """Клавиатура для клиента с запросом обновления геолокации."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Обновить геолокацию", callback_data=f"update_location:{master_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_location:{master_id}")]
    ])
