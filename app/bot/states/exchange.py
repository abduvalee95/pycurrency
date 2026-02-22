"""FSM states for entry and AI input flows."""

from aiogram.fsm.state import State, StatesGroup


class ManualEntryStates(StatesGroup):
    """States for manual entry creation."""

    waiting_amount = State()
    waiting_currency = State()
    waiting_flow = State()
    waiting_client = State()
    waiting_note = State()
    waiting_confirm = State()


class AIInputStates(StatesGroup):
    """States for AI parse and operator confirmation."""

    waiting_raw_text = State()
    waiting_client = State()
    waiting_confirm = State()


class AIChatStates(StatesGroup):
    """States for AI chat (free-form Q&A) mode."""

    waiting_question = State()
