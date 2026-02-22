"""Pluggable AI client adapters (OpenAI and local LLM)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Optional

import httpx
from openai import AsyncOpenAI

from app.api.errors import ValidationError


class BaseAIClient(ABC):
    """Interface for AI backends used by parser service."""

    @abstractmethod
    async def parse_to_json(self, *, prompt: str, text: str) -> dict:
        """Return parser result as JSON-compatible dict."""


def _extract_json_object(raw_text: str) -> dict:
    """Extract first JSON object from model output."""

    candidate = raw_text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()

    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValidationError("AI response is not valid JSON")
        candidate = candidate[start : end + 1]

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Failed to decode AI JSON response: {exc}") from exc

    if not isinstance(data, dict):
        raise ValidationError("AI response JSON must be an object")
    return data


class OpenAIClient(BaseAIClient):
    """OpenAI-compatible adapter with strict parsing prompt."""

    def __init__(self, *, api_key: str, model: str, base_url: Optional[str] = None, extra_headers: Optional[dict] = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, default_headers=extra_headers)
        self._model = model

    async def parse_to_json(self, *, prompt: str, text: str) -> dict:
        """Invoke OpenAI chat completion and parse JSON payload."""

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
        )

        message_content = response.choices[0].message.content or ""
        return _extract_json_object(message_content)


class LocalLLMClient(BaseAIClient):
    """OpenAI-compatible local LLM adapter (e.g., Ollama v1 endpoints)."""

    def __init__(self, *, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def parse_to_json(self, *, prompt: str, text: str) -> dict:
        """Invoke local model endpoint and parse JSON payload."""

        payload = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(f"{self._base_url}/chat/completions", json=payload)
            response.raise_for_status()
            body = response.json()

        try:
            content = body["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"Unexpected local LLM response shape: {body}") from exc

        return _extract_json_object(content)


class OpenRouterClient(BaseAIClient):
    """OpenRouter adapter with optional referer/title headers."""

    def __init__(self, *, api_key: str, model: str, base_url: str, referer: Optional[str], title: Optional[str]) -> None:
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        if referer:
            headers["HTTP-Referer"] = referer
        if title:
            headers["X-Title"] = title
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, default_headers=headers)
        self._model = model

    async def parse_to_json(self, *, prompt: str, text: str) -> dict:
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
        )
        message_content = response.choices[0].message.content or ""
        return _extract_json_object(message_content)


class GoogleAIClient(BaseAIClient):
    """Google Gemini adapter via REST API."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        # Ensure model name has proper prefix if missing, e.g. "gemini-pro" -> "models/gemini-pro"
        # API requires "models/" prefix or just the ID. Usually "gemini-pro" works in URL path if formatted correctly.
        # But safest is to use the model ID directly in URL.
        self._model = model

    async def parse_to_json(self, *, prompt: str, text: str) -> dict:
        """Invoke Google Gemini API and parse JSON payload."""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        
        # Construct payload for Gemini
        payload = {
            "contents": [{
                "parts": [{"text": f"{prompt}\n\nInput:\n{text}"}]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                url, 
                params={"key": self._api_key},
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise ValidationError(f"Google AI Error ({response.status_code}): {response.text}")
                
            data = response.json()

        try:
            # Extract text from response
            # Response structure: candidates[0].content.parts[0].text
            content = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValidationError(f"Unexpected Google AI response shape: {data}") from exc

        return _extract_json_object(content)
