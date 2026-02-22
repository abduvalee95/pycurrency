"""General-purpose AI chat service for operator queries."""

from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI

from app.config import Settings


class AIChatService:
    """Answer free-form operator questions using LLM with injected context."""

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

    async def answer(self, *, question: str, context: str) -> str:
        """Answer operator question using provided context data."""

        system_prompt = (
            "Siz valyuta ayirboshlash shoxobchasi (kassa) uchun AI yordamchisiz. "
            "Sizning vazifangiz operatorning savollariga aniq, qisqa va o'zbek tilida yoki rus tilida javob berishdir. "
            "Operator sizdan kassadagi holat, balans, oxirgi operatsiyalar yoki mijozlar haqida so'rashi mumkin. "
            "Quyida kassa bazasidan olingan eng so'nggi ma'lumotlar keltirilgan (Context). "
            "Javobni FAQAT shu ma'lumotlarga asoslanib bering. Agar so'ralgan ma'lumot contextda bo'lmasa, 'Ma'lumot topilmadi' deng. "
            "Hech qachon o'zingizdan ma'lumot to'qimang. "
            "Javobingiz do'stona va professional bo'lsin. "
            "Javobni oddiy matn shaklida yozing (markdown ishlatishingiz mumkin).\n\n"
            f"=== KASSA MA'LUMOTLARI (CONTEXT) ===\n{context}\n========================="
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )

        return (response.choices[0].message.content or "").strip()
