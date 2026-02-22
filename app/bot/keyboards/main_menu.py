"""Reply keyboard builders."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.bot import texts


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard with operator actions."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.NEW_ENTRY), KeyboardButton(text=texts.AI_ASSISTANT_INPUT)],
            [KeyboardButton(text=texts.REPORTS), KeyboardButton(text=texts.EXPORT_CSV)],
            [KeyboardButton(text=texts.CANCEL_OPERATION)],
        ],
        resize_keyboard=True,
    )
