"""AI parsing orchestration service."""

from __future__ import annotations

from typing import Optional

from app.ai.ai_client import BaseAIClient, GoogleAIClient, LocalLLMClient, OpenAIClient, OpenRouterClient
from app.ai.fallback_parser import RuleBasedAIParser
from app.ai.prompt_builder import build_transaction_parse_prompt
from app.ai.validation import AIParseValidator
from app.api.errors import ValidationError
from app.config import Settings
from app.schemas.ai import AIParsedEntry


class AIParserService:
    """Parse and validate operator natural-language entry messages."""

    def __init__(self, client: Optional[BaseAIClient]) -> None:
        self._client = client
        self._validator = AIParseValidator()
        self._fallback_parser = RuleBasedAIParser()

    @classmethod
    def from_settings(cls, settings: Settings) -> "AIParserService":
        """Factory selecting configured AI backend."""

        client: Optional[BaseAIClient] = None

        if settings.ai_provider == "openai" and settings.openai_api_key:
            client = OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)
        elif settings.ai_provider == "google" and settings.openai_api_key:
            client = GoogleAIClient(api_key=settings.openai_api_key, model=settings.openai_model)
        elif settings.ai_provider == "groq" and settings.groq_api_key:
            client = OpenAIClient(
                api_key=settings.groq_api_key,
                model=settings.groq_model,
                base_url="https://api.groq.com/openai/v1",
            )
        elif settings.ai_provider == "openrouter" and settings.openrouter_api_key:
            client = OpenRouterClient(
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
                base_url=settings.openrouter_base_url,
                referer=settings.openrouter_referer,
                title=settings.openrouter_title,
            )
        elif settings.ai_provider == "deepseek" and settings.deepseek_api_key:
            client = OpenAIClient(
                api_key=settings.deepseek_api_key,
                model=settings.deepseek_model,
                base_url=settings.deepseek_base_url,
            )
        elif settings.ai_provider == "local":
            client = LocalLLMClient(base_url=settings.local_llm_base_url, model=settings.local_llm_model)

        return cls(client)

    async def parse(self, text: str) -> AIParsedEntry:
        """Parse raw text to structured entry; fallback on provider failure."""

        text = text.strip()
        if not text:
            raise ValidationError("Input text is empty")

        if self._client is not None:
            try:
                prompt = build_transaction_parse_prompt()
                raw_payload = await self._client.parse_to_json(prompt=prompt, text=text)
                return self._validator.validate(raw_payload)
            except Exception as exc:  # noqa: BLE001
                print(f"AI Provider failed: {exc}")

        fallback_payload = self._fallback_parser.parse(text)
        return self._validator.validate(fallback_payload)
