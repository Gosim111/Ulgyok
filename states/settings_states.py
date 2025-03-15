from aiogram.fsm.state import State, StatesGroup

class SettingsState(StatesGroup):
    CustomIntel = State()
    CustomFreq = State()