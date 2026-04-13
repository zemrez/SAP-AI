"""LLM provider abstraction using litellm for multi-provider support."""

from __future__ import annotations

import json
import logging
from typing import Any

import litellm

from config import settings

logger = logging.getLogger(__name__)

# Map our config names to litellm model prefixes
_MODEL_MAP: dict[str, str] = {
    "gemini": "gemini/gemini-2.0-flash",
    "openai": "gpt-4o",
}


class LLMProviderError(Exception):
    """Raised when an LLM call fails."""


class LLMProvider:
    """Factory-style LLM provider that routes to Gemini or GPT-4o via litellm.

    Uses ``settings.LLM_PROVIDER`` to pick the backend and the corresponding
    API key from ``settings.GEMINI_API_KEY`` / ``settings.OPENAI_API_KEY``.
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or _MODEL_MAP.get(self.provider, "gemini/gemini-2.0-flash")
        self._configure_keys()

    def _configure_keys(self) -> None:
        """Push API keys into the litellm environment."""
        if self.provider == "gemini" and settings.GEMINI_API_KEY:
            litellm.api_key = settings.GEMINI_API_KEY
        elif self.provider == "openai" and settings.OPENAI_API_KEY:
            litellm.api_key = settings.OPENAI_API_KEY

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Generate a text completion from the LLM.

        Args:
            prompt: The user/task prompt.
            system_prompt: Optional system-level instruction.
            temperature: Sampling temperature (0.0-1.0).

        Returns:
            The generated text string.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                api_key=self._get_api_key(),
            )
            content: str = response.choices[0].message.content or ""
            return content.strip()
        except Exception as exc:
            logger.error("LLM generation failed (%s): %s", self.model, exc)
            raise LLMProviderError(f"LLM call failed: {exc}") from exc

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Generate a JSON response from the LLM.

        The prompt should instruct the model to return valid JSON.
        This method parses the response and returns it as a dict.
        """
        raw = await self.generate(prompt, system_prompt=system_prompt, temperature=0.1)

        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON response: %s", raw[:500])
            raise LLMProviderError(f"Invalid JSON from LLM: {exc}") from exc

    def _get_api_key(self) -> str | None:
        """Return the appropriate API key for the current provider."""
        if self.provider == "gemini":
            return settings.GEMINI_API_KEY or None
        if self.provider == "openai":
            return settings.OPENAI_API_KEY or None
        return None
