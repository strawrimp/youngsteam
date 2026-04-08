"""LLM Provider Service - Multi-provider abstraction with failover."""

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    provider: str
    model: str
    tokens_used: int = 0
    latency_ms: int = 0


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def call(
        self,
        messages: List[Dict],
        **kwargs,
    ) -> LLMResponse:
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API provider."""

    def __init__(self, api_key: str, model: str = "v4"):
        self.api_key = api_key
        self.model = model

    @property
    def name(self) -> str:
        return "deepseek"

    async def call(
        self,
        messages: List[Dict],
        **kwargs,
    ) -> LLMResponse:
        from services.deepseek_service import DeepSeekService

        service = DeepSeekService(
            api_key=self.api_key,
            model=self.model,
        )

        system = None
        user = None
        for msg in messages:
            if msg.get("role") == "system":
                system = msg.get("content")
            elif msg.get("role") == "user":
                user = msg.get("content")

        start = time.time()
        response = await service.call_model(
            system_prompt=system or "",
            user_message=user or "",
            task_type=kwargs.get("task_type", "default"),
            complexity=kwargs.get("complexity", 0.0),
        )
        latency = int((time.time() - start) * 1000)

        return LLMResponse(
            content=response,
            provider=self.name,
            model=self.model,
            latency_ms=latency,
        )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"

    @property
    def name(self) -> str:
        return "openai"

    async def call(
        self,
        messages: List[Dict],
        **kwargs,
    ) -> LLMResponse:
        import httpx

        temperature = kwargs.get("temperature", 0.7)

        start = time.time()

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                },
            )

        latency = int((time.time() - start) * 1000)

        if response.status_code != 200:
            raise Exception(f"OpenAI error: {response.status_code} - {response.text}")

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            latency_ms=latency,
        )


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider (Fallback #1)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash-preview-05-20",
        temperature: float = 0.7,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def name(self) -> str:
        return "gemini"

    async def call(
        self,
        messages: List[Dict],
        **kwargs,
    ) -> LLMResponse:
        import httpx

        start = time.time()

        # Build request
        url = f"{self.base_url}/models/{self.model}:generateContent"

        headers = {
            "Content-Type": "application/json",
        }

        # Add API key to URL parameter or header
        if self.api_key:
            url += f"?key={self.api_key}"

        # Build contents for Gemini
        contents = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            # Gemini uses "model" prefix for system messages
            if role == "system":
                contents.append(
                    {"role": "user", "parts": [{"text": f"[System] {content}"}]}
                )
            else:
                contents.append({"role": role, "parts": [{"text": content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", self.temperature),
                "topP": kwargs.get("top_p", 0.95),
                "maxOutputTokens": kwargs.get("max_tokens", 8192),
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )

        latency = int((time.time() - start) * 1000)

        if response.status_code != 200:
            error_msg = f"Gemini error: {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg += f" - {error_data['error']}"
            except:
                error_msg += f" - {response.text}"
            raise Exception(error_msg)

        data = response.json()

        # Extract text from Gemini response
        if "candidates" in data and len(data["candidates"]) > 0:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                content = "".join(
                    part.get("text", "") for part in candidate["content"]["parts"]
                )
            else:
                content = candidate.get("content", "")
        else:
            logger.warning(f"Unexpected Gemini response format: {data}")
            content = str(data)

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            tokens_used=data.get("usage", {}).get("total_tokens", 0),
            latency_ms=latency,
        )


class OllamaProvider(BaseLLMProvider):
    """Ollama local provider."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model

    @property
    def name(self) -> str:
        return "ollama"

    async def call(
        self,
        messages: List[Dict],
        **kwargs,
    ) -> LLMResponse:
        import httpx

        system_message = ""
        user_message = ""

        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            elif msg.get("role") == "user":
                user_message = msg.get("content", "")

        prompt = (
            f"{system_message}\n\n{user_message}" if system_message else user_message
        )

        start = time.time()

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
            )

        latency = int((time.time() - start) * 1000)

        if response.status_code != 200:
            raise Exception(f"Ollama error: {response.status_code} - {response.text}")

        data = response.json()
        content = data.get("response", "")

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            latency_ms=latency,
        )


class LLMProviderService:
    """Multi-provider LLM service with failover and load balancing."""

    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.fallback_order: List[str] = []
        self.provider_stats: Dict[str, Dict] = {}

    def register_provider(
        self,
        name: str,
        provider: BaseLLMProvider,
        is_primary: bool = False,
    ):
        self.providers[name] = provider
        self.provider_stats[name] = {
            "calls": 0,
            "errors": 0,
            "total_latency": 0,
        }

        if is_primary:
            self.fallback_order.insert(0, name)
        else:
            self.fallback_order.append(name)

        logger.info(f"Registered LLM provider: {name}")

    def get_provider(self, name: str) -> Optional[BaseLLMProvider]:
        return self.providers.get(name)

    def get_primary_provider(self) -> Optional[BaseLLMProvider]:
        if self.fallback_order:
            return self.providers.get(self.fallback_order[0])
        return None

    async def call(
        self,
        messages: List[Dict],
        preferred_provider: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None,
        **kwargs,
    ) -> LLMResponse:
        """Call an LLM with automatic failover.

        Args:
            messages: Chat messages
            preferred_provider: Preferred provider name
            fallback_providers: List of fallback providers in order

        Returns:
            LLMResponse from successful provider
        """
        providers_to_try = []

        if preferred_provider and preferred_provider in self.providers:
            providers_to_try.append(preferred_provider)

        if fallback_providers:
            for name in fallback_providers:
                if name in self.providers and name not in providers_to_try:
                    providers_to_try.append(name)

        for name in self.fallback_order:
            if name not in providers_to_try:
                providers_to_try.append(name)

        last_error = None
        jitter = random.uniform(0.1, 0.5)

        for provider_name in providers_to_try:
            provider = self.providers[provider_name]

            for attempt in range(3):
                try:
                    logger.info(
                        f"Calling provider: {provider_name} (attempt {attempt + 1})"
                    )

                    response = await provider.call(messages, **kwargs)

                    self.provider_stats[provider_name]["calls"] += 1
                    self.provider_stats[provider_name]["total_latency"] += (
                        response.latency_ms
                    )

                    logger.info(
                        f"Provider {provider_name} succeeded ({response.latency_ms}ms)"
                    )

                    return response

                except Exception as e:
                    logger.warning(
                        f"Provider {provider_name} failed (attempt {attempt + 1}): {e}"
                    )

                    self.provider_stats[provider_name]["errors"] += 1
                    last_error = e

                    if attempt < 2:
                        wait_time = jitter * (2**attempt)
                        logger.info(f"Retrying after {wait_time:.1f}s...")
                        await asyncio.sleep(wait_time)

        raise Exception(f"All providers failed. Last error: {last_error}")

    def get_stats(self) -> Dict[str, Dict]:
        stats = {}
        for name, data in self.provider_stats.items():
            calls = data["calls"]
            errors = data["errors"]
            total_latency = data["total_latency"]

            stats[name] = {
                "calls": calls,
                "errors": errors,
                "success_rate": (calls - errors) / calls if calls > 0 else 0,
                "avg_latency_ms": total_latency // calls if calls > 0 else 0,
            }

        return stats


_provider_service: Optional[LLMProviderService] = None


def get_llm_provider_service() -> LLMProviderService:
    """Get singleton LLM provider service."""
    global _provider_service
    if _provider_service is None:
        _provider_service = LLMProviderService()
    return _provider_service
