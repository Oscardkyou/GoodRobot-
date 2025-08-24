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
        row.append(InlineKeyboardButton(text=name, callback_data=f"cat:{name}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    
    if with_back:
        return add_back_button(keyboard, "back:main")
    return keyboard


def zones_keyboard_master_full(selected: list[str] | None = None, with_back: bool = True) -> InlineKeyboardMarkup:
    selected = selected or []
    sel = set(selected)
    rows = []
    row = []
    for i, name in enumerate(ZONES, start=1):
        label = f"✓ {name}" if name in sel else name
        row.append(InlineKeyboardButton(text=label, callback_data=f"mzone:{name}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(
        [
            InlineKeyboardButton(text=f"Готово ({len(sel)})", callback_data="mzone:done"),
            InlineKeyboardButton(text="Сброс", callback_data="mzone:clear"),
        ]
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    
    if with_back:
        return add_back_button(keyboard, "back:master_setup")
    return keyboard


def zones_keyboard_master(with_back: bool = True) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, name in enumerate(ZONES, start=1):
        row.append(InlineKeyboardButton(text=name, callback_data=f"mzone:{name}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    
    if with_back:
        return add_back_button(keyboard, "back:master_setup")
    return keyboard


ZONES = [
    "Алмалинский",
    "Ауэзовский",
    "Бостандыкский",
    "Жетысуский",
    "Медеуский",
    "Наурызбай",
    "Турксибский",
]


def zones_keyboard(with_back: bool = True) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, name in enumerate(ZONES, start=1):
        row.append(InlineKeyboardButton(text=name, callback_data=f"zone:{name}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    
    if with_back:
        return add_back_button(keyboard, "back:order_create")
    return keyboard


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
