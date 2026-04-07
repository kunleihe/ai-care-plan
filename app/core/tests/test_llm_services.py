import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from core.llm import BaseLLMService, ClaudeService, OpenAIService, get_llm_service


class TestLLMServiceFactory(SimpleTestCase):
    @override_settings(
        LLM_PROVIDER='openai',
        OPENAI_API_KEY='test-openai-key',
        OPENAI_MODEL='gpt-4o-mini',
        LLM_TEMPERATURE=0.2,
    )
    def test_factory_returns_openai_service_from_settings(self):
        service = get_llm_service()

        self.assertIsInstance(service, OpenAIService)
        self.assertEqual(service.api_key, 'test-openai-key')
        self.assertEqual(service.model, 'gpt-4o-mini')
        self.assertEqual(service.temperature, 0.2)

    @override_settings(
        ANTHROPIC_API_KEY='test-claude-key',
        CLAUDE_MODEL='claude-3-5-sonnet-latest',
        CLAUDE_MAX_TOKENS=1234,
        LLM_TEMPERATURE=0.1,
    )
    def test_factory_returns_claude_service_from_provider_override(self):
        service = get_llm_service('claude')

        self.assertIsInstance(service, ClaudeService)
        self.assertEqual(service.api_key, 'test-claude-key')
        self.assertEqual(service.model, 'claude-3-5-sonnet-latest')
        self.assertEqual(service.max_tokens, 1234)
        self.assertEqual(service.temperature, 0.1)

    def test_factory_raises_for_unknown_provider(self):
        with self.assertRaises(ValueError):
            get_llm_service('local')


class TestOpenAIService(SimpleTestCase):
    @override_settings(OPENAI_MODEL='gpt-4o-mini')
    def test_generate_text_uses_openai_chat_completions(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content='openai result'))
        ]
        fake_openai_module = SimpleNamespace(OpenAI=MagicMock(return_value=mock_client))

        with patch.dict(sys.modules, {'openai': fake_openai_module}):
            service = OpenAIService(api_key='test-key')
            result = service.generate_text('hello')

        self.assertEqual(result, 'openai result')
        mock_client.chat.completions.create.assert_called_once_with(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': 'hello'}],
            temperature=0.3,
        )


class TestClaudeService(SimpleTestCase):
    @override_settings(CLAUDE_MODEL='claude-3-5-sonnet-latest', CLAUDE_MAX_TOKENS=2000)
    def test_generate_text_uses_anthropic_messages_api(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(type='text', text='claude result'),
        ]
        fake_anthropic_module = SimpleNamespace(
            Anthropic=MagicMock(return_value=mock_client)
        )

        with patch.dict(sys.modules, {'anthropic': fake_anthropic_module}):
            service = ClaudeService(api_key='test-key')
            result = service.generate_text('hello')

        self.assertEqual(result, 'claude result')
        mock_client.messages.create.assert_called_once_with(
            model='claude-3-5-sonnet-latest',
            max_tokens=2000,
            temperature=0.3,
            messages=[{'role': 'user', 'content': 'hello'}],
        )


class TestBaseLLMService(SimpleTestCase):
    def test_base_class_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            BaseLLMService(model='demo')
