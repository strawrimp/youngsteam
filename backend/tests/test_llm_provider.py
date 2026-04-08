"""Tests for LLM Provider Service."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock settings before importing services
sys.modules["config"] = MagicMock()

from services.llm_provider_service import (
    LLMProviderService,
    LLMResponse,
    BaseLLMProvider,
    DeepSeekProvider,
    OpenAIProvider,
    GeminiProvider,
    OllamaProvider,
)


class MockProvider(BaseLLMProvider):
    """Mock provider for testing."""

    def __init__(self, name: str, should_fail: bool = False):
        self._name = name
        self.should_fail = should_fail
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    async def call(self, messages, **kwargs):
        self.call_count += 1

        if self.should_fail:
            raise Exception(f"{self._name} failed!")

        return LLMResponse(
            content=f"Response from {self._name}",
            provider=self._name,
            model="test-model",
            tokens_used=100,
            latency_ms=50,
        )


class TestLLMResponse:
    """Test LLMResponse dataclass."""

    def test_llm_response_creation(self):
        """Test LLMResponse creation."""
        response = LLMResponse(
            content="Test response",
            provider="test",
            model="test-model",
            tokens_used=100,
            latency_ms=50,
        )

        assert response.content == "Test response"
        assert response.provider == "test"
        assert response.model == "test-model"
        assert response.tokens_used == 100
        assert response.latency_ms == 50


class TestLLMProviderService:
    """Test suite for LLMProviderService."""

    @pytest.fixture
    def provider_service(self):
        """Create LLM provider service."""
        return LLMProviderService()

    # ==================== Provider Registration Tests ====================

    def test_register_provider(self, provider_service):
        """Test provider registration."""
        mock_provider = MockProvider("test")

        provider_service.register_provider("test", mock_provider)

        assert "test" in provider_service.providers
        assert provider_service.providers["test"] == mock_provider
        assert "test" in provider_service.fallback_order

    @pytest.mark.asyncio
    async def test_call_provider(self, provider_service):
        """Test calling a provider."""
        mock_provider = MockProvider("test")

        provider_service.register_provider("test", mock_provider)

        response = await provider_service.call(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert response.provider == "test"
        assert "Response from test" in response.content
        assert mock_provider.call_count == 1

    @pytest.mark.asyncio
    async def test_call_with_preferred_provider(self, provider_service):
        """Test calling with preferred provider."""
        mock1 = MockProvider("provider1")
        mock2 = MockProvider("provider2")

        provider_service.register_provider("provider1", mock1)
        provider_service.register_provider("provider2", mock2)

        response = await provider_service.call(
            messages=[{"role": "user", "content": "Hello"}],
            preferred_provider="provider2",
        )

        assert response.provider == "provider2"
        assert mock1.call_count == 0
        assert mock2.call_count == 1

    @pytest.mark.asyncio
    async def test_call_with_fallback_providers(self, provider_service):
        """Test calling with fallback providers."""
        mock1 = MockProvider("provider1", should_fail=True)
        mock2 = MockProvider("provider2")

        provider_service.register_provider("provider1", mock1)
        provider_service.register_provider("provider2", mock2)

        response = await provider_service.call(
            messages=[{"role": "user", "content": "Hello"}],
            preferred_provider="provider1",
            fallback_providers=["provider2"],
        )

        assert response.provider == "provider2"
        assert mock1.call_count == 3  # Retried 3 times
        assert mock2.call_count == 1

    @pytest.mark.asyncio
    async def test_automatic_fallback(self, provider_service):
        """Test automatic fallback when primary fails."""
        mock1 = MockProvider("primary", should_fail=True)
        mock2 = MockProvider("secondary")

        provider_service.register_provider("primary", mock1, is_primary=True)
        provider_service.register_provider("secondary", mock2)

        response = await provider_service.call(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert response.provider == "secondary"

    # ==================== Stats Tests ====================

    def test_get_stats(self, provider_service):
        """Test getting provider statistics."""
        mock1 = MockProvider("provider1")
        mock2 = MockProvider("provider2")

        provider_service.register_provider("provider1", mock1)
        provider_service.register_provider("provider2", mock2)

        # Manually update stats
        provider_service.provider_stats["provider1"]["calls"] = 10
        provider_service.provider_stats["provider1"]["errors"] = 2
        provider_service.provider_stats["provider1"]["total_latency"] = 1000

        stats = provider_service.get_stats()

        assert "provider1" in stats
        assert stats["provider1"]["calls"] == 10
        assert stats["provider1"]["errors"] == 2
        assert stats["provider1"]["success_rate"] == 0.8
        assert stats["provider1"]["avg_latency_ms"] == 100


class TestProviderClasses:
    """Test individual provider classes."""

    def test_deepseek_provider_creation(self):
        """Test DeepSeek provider creation."""
        provider = DeepSeekProvider(api_key="test-api-key", model="v4")

        assert provider.name == "deepseek"
        assert provider.model == "v4"

    def test_openai_provider_creation(self):
        """Test OpenAI provider creation."""
        provider = OpenAIProvider(api_key="test-api-key", model="gpt-4o")

        assert provider.name == "openai"
        assert provider.model == "gpt-4o"

    def test_gemini_provider_creation(self):
        """Test Gemini provider creation."""
        provider = GeminiProvider(
            api_key="test-api-key", model="gemini-2.5-flash-preview-05-20"
        )

        assert provider.name == "gemini"
        assert provider.model == "gemini-2.5-flash-preview-05-20"

    def test_ollama_provider_creation(self):
        """Test Ollama provider creation."""
        provider = OllamaProvider(base_url="http://localhost:11434", model="llama2")

        assert provider.name == "ollama"
        assert provider.model == "llama2"

    @pytest.mark.asyncio
    async def test_gemini_provider_call_mock(self):
        """Test Gemini provider call with mocked response."""
        provider = GeminiProvider(
            api_key="test-api-key", model="gemini-2.5-flash-preview-05-20"
        )

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "candidates": [
                    {"content": {"parts": [{"text": "Test response from Gemini"}]}}
                ]
            }

            # Configure mock to return our mock instance
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )
            mock_client_instance.post.return_value = mock_response

            response = await provider.call(
                messages=[
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "Hello"},
                ]
            )

            assert response.provider == "gemini"
            assert "Gemini" in response.content


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
