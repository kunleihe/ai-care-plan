from __future__ import annotations

from abc import ABC, abstractmethod

from django.conf import settings


class BaseLLMService(ABC):
    def __init__(self, *, model: str, temperature: float = 0.3):
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError


class OpenAIService(BaseLLMService):
    def __init__(
        self,
        *,
        api_key: str,
        model: str | None = None,
        temperature: float = 0.3,
    ):
        super().__init__(
            model=model or getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini'),
            temperature=temperature,
        )
        self.api_key = api_key

    def generate_text(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ''


class ClaudeService(BaseLLMService):
    def __init__(
        self,
        *,
        api_key: str,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ):
        super().__init__(
            model=model or getattr(settings, 'CLAUDE_MODEL', 'claude-3-5-sonnet-latest'),
            temperature=temperature,
        )
        self.api_key = api_key
        self.max_tokens = max_tokens or getattr(settings, 'CLAUDE_MAX_TOKENS', 2000)

    def generate_text(self, prompt: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{'role': 'user', 'content': prompt}],
        )

        text_parts = [
            block.text for block in response.content
            if getattr(block, 'type', None) == 'text'
        ]
        return ''.join(text_parts)


def get_llm_service(provider: str | None = None) -> BaseLLMService:
    provider_name = (provider or getattr(settings, 'LLM_PROVIDER', 'openai')).lower()
    temperature = getattr(settings, 'LLM_TEMPERATURE', 0.3)

    if provider_name == 'openai':
        return OpenAIService(
            api_key=getattr(settings, 'OPENAI_API_KEY', ''),
            model=getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini'),
            temperature=temperature,
        )

    if provider_name == 'claude':
        return ClaudeService(
            api_key=getattr(settings, 'ANTHROPIC_API_KEY', ''),
            model=getattr(settings, 'CLAUDE_MODEL', 'claude-3-5-sonnet-latest'),
            temperature=temperature,
            max_tokens=getattr(settings, 'CLAUDE_MAX_TOKENS', 2000),
        )

    raise ValueError(f'Unsupported LLM provider: {provider_name}')
