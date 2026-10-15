"""Finite State Machine (FSM) states."""

from aiogram.fsm.state import State, StatesGroup


class AddAccountFSM(StatesGroup):
    token = State()
    name = State()


class CustomAlertFSM(StatesGroup):
    pct = State()
