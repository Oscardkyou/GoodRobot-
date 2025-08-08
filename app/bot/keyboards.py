"""Inline keyboards for bot flows."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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


def categories_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, name in enumerate(CATEGORIES, start=1):
        row.append(InlineKeyboardButton(text=name, callback_data=f"cat:{name}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def zones_keyboard_master_full(selected: list[str] | None = None) -> InlineKeyboardMarkup:
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
    return InlineKeyboardMarkup(inline_keyboard=rows)


def zones_keyboard_master() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, name in enumerate(ZONES, start=1):
        row.append(InlineKeyboardButton(text=name, callback_data=f"mzone:{name}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


ZONES = [
    "Алмалинский",
    "Ауэзовский",
    "Бостандыкский",
    "Жетысуский",
    "Медеуский",
    "Наурызбай",
    "Турксибский",
]


def zones_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, name in enumerate(ZONES, start=1):
        row.append(InlineKeyboardButton(text=name, callback_data=f"zone:{name}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data="confirm:yes"),
                InlineKeyboardButton(text="Отмена", callback_data="confirm:no"),
            ]
        ]
    )
