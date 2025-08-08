"""FSM States used in bot flows."""
from aiogram.fsm.state import State, StatesGroup


class OrderCreate(StatesGroup):
    category = State()
    zone = State()
    address = State()
    description = State()
    confirm = State()


class MasterSetup(StatesGroup):
    zones = State()


class BidCreate(StatesGroup):
    price = State()
