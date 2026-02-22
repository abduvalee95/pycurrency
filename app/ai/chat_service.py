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

    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> Optional["AIChatService"]:
        """Build chat service from settings. Returns None if no provider configured."""

        if settings.ai_provider == "groq":
            if settings.groq_api_key:
                client = AsyncOpenAI(
                    api_key=settings.groq_api_key,
                    base_url="https://api.groq.com/openai/v1",
                )
                return cls(client=client, model=settings.groq_model)

        if settings.ai_provider == "openai":
            if settings.openai_api_key:
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                return cls(client=client, model=settings.openai_model)

        if settings.ai_provider == "deepseek":
            if settings.deepseek_api_key:
                client = AsyncOpenAI(
                    api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url,
                )
                return cls(client=client, model=settings.deepseek_model)

        if settings.ai_provider == "openrouter":
            if settings.openrouter_api_key:
                client = AsyncOpenAI(
                    api_key=settings.openrouter_api_key,
                    base_url=settings.openrouter_base_url,
                )
                return cls(client=client, model=settings.openrouter_model)

        return None

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

            "2. YOZUV YARATISH - operator yangi entry yaratmoqchi bo'lsa "
            "(masalan: 'Ali 1000 usd berdi', '500 rub chiqim Bekdan', 'Isa ga 200 usd berdim'):\n"
            '{"action": "create_entry", "data": {"amount": 1000, "currency_code": "USD", '
            '"flow_direction": "INFLOW", "client_name": "Ali", "note": ""}}\n'
            "flow_direction qoidalari:\n"
            "- Pul KELSA (oldi, berdi, kirim, sotdi, keldi) = INFLOW\n"
            "- Pul KETSA (berdi+ga, chiqim, oldi+dan, chiqardi, ketdi) = OUTFLOW\n"
            "- 'berdim' = OUTFLOW (men berdim = pul ketdi)\n"
            "- 'berdi' = INFLOW (u berdi = pul keldi)\n"
            "currency_code faqat: USD, RUB, UZS\n\n"

            "3. O'CHIRISH - operator entry o'chirmoqchi bo'lsa "
            "(masalan: '#5 ni o'chir', 'entry 3 delete', '2-yozuvni o'chir'):\n"
            '{"action": "delete_entry", "data": {"entry_id": 5}}\n\n'

            "QOIDALAR:\n"
            "- Javob FAQAT JSON bo'lsin, boshqa matn yo'q\n"
            "- Agar savol bo'lsa, contextdagi ma'lumotlarga asoslanib javob ber\n"
            "- Agar so'ralgan ma'lumot contextda bo'lmasa, 'Ma'lumot topilmadi' de\n"
            "- Hech qachon o'zingizdan ma'lumot to'qima\n"
            "- Javob do'stona va professional bo'lsin\n"
            "- O'zbek yoki rus tilida javob ber\n\n"

            f"=== KASSA MA'LUMOTLARI (CONTEXT) ===\n{context}\n=========================\n"
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )

        raw = (response.choices[0].message.content or "").strip()
        return self._parse_response(raw)

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
            if isinstance(result, dict) and "action" in result:
                return result
        except json.JSONDecodeError:
            pass

        # Fallback: treat entire response as text
        return {"action": "text", "data": {"message": raw}}
