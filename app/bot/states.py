"""FSM States used in bot flows."""
from aiogram.fsm.state import State, StatesGroup


class OrderCreate(StatesGroup):
    category = State()
    zone = State()
    address = State()
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
