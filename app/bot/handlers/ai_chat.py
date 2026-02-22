"""AI chat handler: answers general operator questions about kassa state."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.ai.chat_service import AIChatService
from app.ai.context_builder import ChatContextBuilder
from app.bot import texts
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.states.exchange import AIChatStates
from app.config import get_settings
from app.database.session import db_manager

router = Router()


@router.message(F.text == texts.AI_CHAT)
async def start_ai_chat(message: Message, state: FSMContext) -> None:
    """Start AI chat mode."""

    settings = get_settings()
    chat_service = AIChatService.from_settings(settings)

    if chat_service is None:
        await message.answer(
            "AI chat sozlanmagan. .env faylida AI_PROVIDER va API kalitini tekshiring.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.clear()
    await state.set_state(AIChatStates.waiting_question)
    await message.answer(
        "🤖 AI yordamchi tayyor. Savolingizni yozing:\n"
        "Masalan: balansni ko'rsat, bugungi hisobot, so'nggi mijozlar, so'nggi operatsiya...\n\n"
        "Chiqish uchun /start yoki ❌ Cancel bosing."
    )


@router.message(AIChatStates.waiting_question)
async def handle_ai_chat_question(message: Message, state: FSMContext) -> None:
    """Answer operator question using AI with live DB context."""

    question = (message.text or "").strip()
    if not question:
        await message.answer("Savol bo'sh. Iltimos, qayta yozing.")
        return

    settings = get_settings()
    chat_service = AIChatService.from_settings(settings)

    if chat_service is None:
        await message.answer("AI chat ishlamayapti.", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    thinking_msg = await message.answer("⏳ Javob tayyorlanmoqda...")

    try:
        async with db_manager.session_factory() as session:
            context_builder = ChatContextBuilder(base_currency_code=settings.base_currency_code)
            context = await context_builder.build(session)

        answer = await chat_service.answer(question=question, context=context)
        await thinking_msg.delete()
        await message.answer(f"🤖 {answer}")

    except Exception as exc:  # noqa: BLE001
        await thinking_msg.delete()
        await message.answer(f"❌ Xato: {exc}")
