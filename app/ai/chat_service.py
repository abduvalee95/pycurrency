"""General-purpose AI chat service for operator queries with action support."""

from __future__ import annotations

import json
from typing import Optional

from openai import AsyncOpenAI

from app.config import Settings


class AIChatService:
    """Answer free-form operator questions using LLM with injected context.
    
    Supports actions: create_entry, delete_entry, and plain text answers.
    """

    def __init__(self, client: AsyncOpenAI, model: str, fallbacks: list | None = None) -> None:
        self._client = client
        self._model = model
        self._fallbacks: list[tuple[AsyncOpenAI, str]] = fallbacks or []

    @classmethod
    def from_settings(cls, settings: Settings) -> Optional["AIChatService"]:
        """Build chat service from settings with automatic fallback chain."""

        def _client_for(provider: str) -> tuple[AsyncOpenAI, str] | None:
            if provider == "groq" and settings.groq_api_key:
                return AsyncOpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1"), settings.groq_model
            if provider == "openai" and settings.openai_api_key:
                return AsyncOpenAI(api_key=settings.openai_api_key), settings.openai_model
            if provider == "openrouter" and settings.openrouter_api_key:
                return AsyncOpenAI(api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url), settings.openrouter_model
            if provider == "deepseek" and settings.deepseek_api_key:
                return AsyncOpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url), settings.deepseek_model
            if provider == "google" and settings.google_api_key:
                return AsyncOpenAI(api_key=settings.google_api_key, base_url=settings.google_base_url), settings.google_model
            return None

        primary_pair = _client_for(settings.ai_provider)
        if primary_pair is None:
            return None

        # Build fallback chain from other configured providers
        all_providers = ["groq", "openrouter", "openai", "deepseek", "google"]
        fallbacks = []
        for p in all_providers:
            if p != settings.ai_provider:
                pair = _client_for(p)
                if pair:
                    fallbacks.append(pair)

        client, model = primary_pair
        return cls(client=client, model=model, fallbacks=fallbacks)

    async def answer(self, *, question: str, context: str) -> dict:
        """Answer operator question. Returns dict with 'action' and 'data' keys.
        
        Possible actions:
        - "text": plain text answer in data["message"]
        - "create_entry": entry data in data (amount, currency_code, flow_direction, client_name, note)
        - "delete_entry": entry id in data["entry_id"]
        """

        system_prompt = (
            "Siz valyuta ayirboshlash shoxobchasi (kassa) uchun AI yordamchisiz. "
            "Sizning vazifangiz operatorning savollariga javob berish yoki buyruqlarini bajarishdir.\n\n"

            "MUHIM: Javobingizni FAQAT JSON formatda bering. Boshqa hech narsa yozmang.\n\n"

            "3 xil amal (action) mavjud:\n\n"

            "1. SAVOL - operator savol bersa (balans, hisobot, mijozlar haqida):\n"
            '{"action": "text", "data": {"message": "javobingiz shu yerda"}}\n\n'

            "2. YOZUV YARATISH - operator yangi entry yaratmoqchi bo'lsa:\n"
            '{"action": "create_entry", "data": {"amount": 1000, "currency_code": "USD", '
            '"flow_direction": "INFLOW", "client_name": "Ali", "note": ""}}\n\n'

            "flow_direction QOIDALARI (JUDA MUHIM!):\n"
            "INFLOW (kassaga pul KIRDI):\n"
            "  - '[ism] berdi' = client pul berdi → INFLOW\n"
            "  - '[ism]dan oldim/oldik' = biz clientdan oldik → INFLOW\n"
            "  - '[ism] sotdi' = client bizga sotdi → INFLOW\n"
            "  - 'kirim' = INFLOW\n"
            "OUTFLOW (kassadan pul CHIQDI):\n"
            "  - '[ism]ga berdim/berdik' = biz clientga berdik → OUTFLOW\n"
            "  - '[ism] oldi' = client kassadan oldi → OUTFLOW\n"
            "  - 'chiqim' = OUTFLOW\n"
            "  - 'berdim' = men berdim = OUTFLOW\n\n"
            "⚠️ DIQQAT: '[ism] oldi' DOIM OUTFLOW! Chunki client kassadan pul OLDI.\n"
            "⚠️ '[ism] berdi' yoki shunchaki 'berdi' DOIM INFLOW (BUY)! Chunki kimdir kassaga pul BERDI (masalan: 'aliakaga 100$ berdi' -> INFLOW, client='aliaka').\n"
            "⚠️ 'berdim' so'zi DOIM OUTFLOW (SELL) bo'ladi! (masalan: 'aliakaga 100$ berdim' -> OUTFLOW, client='aliaka').\n\n"

            "IZOH (NOTE) QOIDASI:\n"
            "- Agar xabarda nuqta (.), vergul (,) yoki ikki nuqta (:) qatnashsa, ushbu belgidan keyin kelgan barcha matnni 'note' ga yozing.\n"
            "- LEKIN: Raqamlar orasidagi o'nlik kasrni (, yoki .) note deb hisoblamang! (Masalan '100,5' yozilsa, bu 100.5 miqdor, note emas).\n\n"

            "VALYUTA QOIDALARI:\n"
            "- 'som', 'сом', 'kgs' = KGS (asosiy valyuta)\n"
            "- 'so\\'m', 'sum', 'uzs' = UZS\n"
            "- 'dollar', '$', 'usd', 'дол' = USD\n"
            "- 'rubl', 'rub', 'руб' = RUB\n"
            "- 'evro', 'euro', 'eur', 'евро' = EUR\n"
            "- Agar valyuta ko'rsatilmasa = KGS (asosiy valyuta)\n"
            "Qo'llab-quvvatlanadigan valyutalar: USD, RUB, UZS, KGS, EUR\n\n"

            "MIJOZ ISMI: Xabardagi birinchi ism doim client_name sifatida olinsin.\n\n"

            "3. O'CHIRISH - operator entry o'chirmoqchi bo'lsa:\n"
            "Misol xabarlar: '#5 o'chir', '#5 ni o'chir', 'entry 3 delete', "
            "'3-ni o'chir', '5-yozuvni o'chir', 'delete 2', '1 ni ochir'\n"
            '{"action": "delete_entry", "data": {"entry_id": 5}}\n'
            "Agar xabarda '#' yoki 'entry' yoki raqam + 'o\\'chir/delete/ochir' bo'lsa = delete_entry\n\n"

            "QOIDALAR:\n"
            "- Javob FAQAT JSON bo'lsin, boshqa matn yo'q\n"
            "- Agar savol bo'lsa, contextdagi ma'lumotlarga asoslanib javob ber\n"
            "- Agar so'ralgan ma'lumot contextda bo'lmasa, 'Ma'lumot topilmadi' de\n"
            "- Hech qachon o'zingizdan ma'lumot to'qima\n"
            "- Javob do'stona va professional bo'lsin\n"
            "- O'zbek yoki rus tilida javob ber\n\n"

            f"=== KASSA MA'LUMOTLARI (CONTEXT) ===\n{context}\n=========================\n"
        )

        msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        clients_to_try = [(self._client, self._model)] + self._fallbacks

        last_error = None
        for client, model in clients_to_try:
            try:
                response = await client.chat.completions.create(
                    model=model,
                    temperature=0.1,
                    messages=msgs,
                )
                raw = (response.choices[0].message.content or "").strip()
                return self._parse_response(raw)

            except Exception as exc:
                err_str = str(exc)
                # Only retry on rate limit errors
                if "429" in err_str or "rate limit" in err_str.lower() or "quota" in err_str.lower():
                    last_error = exc
                    continue
                raise

        # All providers exhausted
        raise RuntimeError(f"All AI providers failed. Last error: {last_error}")

    @staticmethod
    def _parse_response(raw: str) -> dict:
        """Parse AI response JSON. Falls back to text action on parse failure."""

        # Clean markdown code blocks if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            result = json.loads(cleaned)
            if isinstance(result, dict):
                action = result.get("action")
                data = result.get("data")
                # Guard: action must be a valid non-null string
                if action not in {"text", "create_entry", "delete_entry"}:
                    return {"action": "text", "data": {"message": raw}}
                # Guard: data must be a dict (not None, not list)
                if not isinstance(data, dict):
                    return {"action": "text", "data": {"message": raw}}
                return result
        except json.JSONDecodeError:
            pass

        # Fallback: treat entire response as text
        return {"action": "text", "data": {"message": raw}}

