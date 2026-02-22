"""AI chat handler: answers questions, creates entries, and deletes entries."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Union

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.ai.chat_service import AIChatService
from app.ai.context_builder import ChatContextBuilder
from app.bot import texts
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.states.exchange import AIChatStates
from app.config import get_settings
from app.database.session import db_manager
from app.schemas.entry import EntryCreate
from app.security.telegram_auth import is_bot_user_allowed
from app.services.entry_service import EntryService

router = Router()


def _fmt(value: Union[Decimal, int, float], currency: str) -> str:
    return f"{Decimal(value):,.2f} {currency}".replace(",", " ")


async def _ensure_allowed(message: Message) -> bool:
    settings = get_settings()
    user_id = message.from_user.id if message.from_user else None
    if user_id is None or not is_bot_user_allowed(user_id, settings):
        await message.answer("Access denied.")
        return False
    return True


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
        "🤖 AI yordamchi tayyor.\n\n"
        "Nima qila olaman:\n"
        "📝 Entry yaratish: 'Ali 1000 usd berdi'\n"
        "🗑 O'chirish: '#5 ni o'chir'\n"
        "📊 Savol: 'balansni ko'rsat'\n\n"
        "Chiqish uchun /start yoki ❌ Cancel bosing."
    )


@router.message(AIChatStates.waiting_question)
async def handle_ai_chat_question(message: Message, state: FSMContext) -> None:
    """Process operator message: answer question, create entry, or delete entry."""

    if not await _ensure_allowed(message):
        return

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

        result = await chat_service.answer(question=question, context=context)
        await thinking_msg.delete()

        action = result.get("action", "text")
        data = result.get("data", {})

        if action == "create_entry":
            await _handle_create_entry(message, state, data)

        elif action == "delete_entry":
            await _handle_delete_entry(message, state, data)

        else:
            # Plain text answer
            msg = data.get("message", str(data))
            await message.answer(f"🤖 {msg}")

    except Exception as exc:  # noqa: BLE001
        await thinking_msg.delete()
        await message.answer(f"❌ Xato: {exc}")


async def _handle_create_entry(message: Message, state: FSMContext, data: dict) -> None:
    """Show AI-parsed entry for confirmation before saving."""

    try:
        amount = Decimal(str(data.get("amount", 0)))
        raw_currency = str(data.get("currency_code", ""))
        flow_direction = str(data.get("flow_direction", "")).upper()
        client_name = str(data.get("client_name", "")).strip()
        note = str(data.get("note", "")).strip() or None

        from app.utils.currency import normalize_currency
        currency_code = normalize_currency(raw_currency)

        if amount <= 0 or currency_code is None or flow_direction not in {"INFLOW", "OUTFLOW"}:
            await message.answer("❌ AI noto'g'ri ma'lumot qaytardi. Qayta urinib ko'ring.")
            return

        if not client_name:
            await message.answer("❌ Client nomi topilmadi. Qayta yozing.")
            return

    except (InvalidOperation, ValueError):
        await message.answer("❌ AI noto'g'ri ma'lumot qaytardi. Qayta urinib ko'ring.")
        return

    direction = "📥 KIRIM" if flow_direction == "INFLOW" else "📤 CHIQIM"
    summary = (
        f"📝 Entry yaratilsinmi?\n\n"
        f"{direction}\n"
        f"Amount: {_fmt(amount, currency_code)}\n"
        f"Client: {client_name}\n"
        f"Note: {note or '-'}"
    )

    # Save parsed data to FSM state
    await state.update_data(
        ai_create={
            "amount": str(amount),
            "currency_code": currency_code,
            "flow_direction": flow_direction,
            "client_name": client_name,
            "note": note,
        }
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="aichat_create_yes")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="aichat_create_no")],
        ]
    )
    await message.answer(summary, reply_markup=keyboard)


async def _handle_delete_entry(message: Message, state: FSMContext, data: dict) -> None:
    """Show entry details for confirmation before soft delete."""

    entry_id = data.get("entry_id")
    if not entry_id or not str(entry_id).isdigit():
        await message.answer("❌ Entry ID topilmadi. Qayta urinib ko'ring.")
        return

    entry_id = int(entry_id)
    service = EntryService()

    async with db_manager.session_factory() as session:
        entry = await service.get_entry_by_id(session, entry_id)

    if entry is None:
        await message.answer(f"❌ Entry #{entry_id} topilmadi yoki allaqachon o'chirilgan.")
        return

    direction = "📥 KIRIM" if entry.flow_direction == "INFLOW" else "📤 CHIQIM"
    summary = (
        f"🗑 O'chirmoqchimisiz?\n\n"
        f"#{entry.id} | {direction}\n"
        f"Amount: {_fmt(entry.amount, entry.currency_code)}\n"
        f"Client: {entry.client_name}\n"
        f"Note: {entry.note or '-'}\n"
        f"Sana: {entry.created_at.strftime('%d.%m.%Y %H:%M')}"
    )

    await state.update_data(ai_delete_id=entry_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Ha, o'chir", callback_data="aichat_delete_yes")],
            [InlineKeyboardButton(text="❌ Yo'q", callback_data="aichat_delete_no")],
        ]
    )
    await message.answer(summary, reply_markup=keyboard)


# --- Callback handlers ---

@router.callback_query(F.data == "aichat_create_yes")
async def confirm_ai_create(callback, state: FSMContext):
    """Create entry after AI chat confirmation."""

    data = await state.get_data()
    parsed = data.get("ai_create")
    if not parsed:
        await callback.message.answer("❌ Ma'lumot topilmadi.")
        await callback.answer()
        return

    try:
        payload = EntryCreate(
            amount=Decimal(parsed["amount"]),
            currency_code=parsed["currency_code"],
            flow_direction=parsed["flow_direction"],
            client_name=parsed["client_name"],
            note=parsed.get("note"),
        )
        service = EntryService()
        async with db_manager.session_factory() as session:
            entry = await service.create_entry(
                session=session,
                payload=payload,
                created_by_telegram_id=callback.from_user.id,
            )
        await callback.message.answer(
            f"✅ Entry #{entry.id} saqlandi!\n"
            f"{_fmt(entry.amount, entry.currency_code)} | {entry.flow_direction} | {entry.client_name}"
        )
    except Exception as exc:  # noqa: BLE001
        await callback.message.answer(f"❌ Xatolik: {exc}")

    await state.update_data(ai_create=None)
    await callback.answer()


@router.callback_query(F.data == "aichat_create_no")
async def cancel_ai_create(callback, state: FSMContext):
    """Cancel AI chat entry creation."""

    await state.update_data(ai_create=None)
    await callback.message.answer("Entry yaratish bekor qilindi.")
    await callback.answer()


@router.callback_query(F.data == "aichat_delete_yes")
async def confirm_ai_delete(callback, state: FSMContext):
    """Execute soft delete after AI chat confirmation."""

    data = await state.get_data()
    entry_id = data.get("ai_delete_id")
    if not entry_id:
        await callback.message.answer("❌ Ma'lumot topilmadi.")
        await callback.answer()
        return

    service = EntryService()
    async with db_manager.session_factory() as session:
        entry = await service.soft_delete_entry(session, entry_id)

    if entry:
        await callback.message.answer(
            f"✅ Entry #{entry_id} o'chirildi (soft delete).\n"
            f"Qayta tiklash: /restore {entry_id}"
        )
    else:
        await callback.message.answer(f"❌ Entry #{entry_id} topilmadi.")

    await state.update_data(ai_delete_id=None)
    await callback.answer()


@router.callback_query(F.data == "aichat_delete_no")
async def cancel_ai_delete(callback, state: FSMContext):
    """Cancel AI chat delete."""

    await state.update_data(ai_delete_id=None)
    await callback.message.answer("O'chirish bekor qilindi.")
    await callback.answer()
