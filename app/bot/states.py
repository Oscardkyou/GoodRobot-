"""FSM States used in bot flows."""
from aiogram.fsm.state import State, StatesGroup


class OrderCreate(StatesGroup):
    category = State()
    address = State()
    location = State()  # Состояние для выбора способа геолокации
    location_by_address = State()  # Геокодинг по адресу
    location_by_coordinates = State()  # Ввод координат вручную
    media = State()
    description = State()
    confirm = State()


class MasterSetup(StatesGroup):
    zones = State()


class BidCreate(StatesGroup):
    price = State()


class PartnerSetup(StatesGroup):
    payout_request = State()
    stats_filter = State()


class ClientActions(StatesGroup):
    waiting_location = State()  # Ожидание отправки геолокации клиентом
    waiting_message = State()  # Ожидание сообщения от клиента для мастера


class MasterActions(StatesGroup):
    waiting_message = State()  # Ожидание ввода сообщения от мастера для клиента
    tracking_client = State()  # Отслеживание клиента
