"""Service for GLM API communication."""

import httpx
import json
from typing import List, Dict, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class GLMService:
    """Wrapper for GLM API calls."""

    BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(self, api_key: str = "", model: str = "glm-4", temperature: float = 0.7):
        """Initialize GLM service."""
        self.api_key = api_key or settings.glm_api_key
        self.model = model or settings.glm_model
        self.temperature = temperature or settings.glm_temperature

    async def call_model(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> str:
        """
        Call GLM model with a message.

        Args:
            system_prompt: System prompt for the model
            user_message: User message
            conversation_history: Previous messages in conversation

        Returns:
            Model's response
        """
        if not self.api_key:
            # Fallback for testing: echo with a prefix
            logger.warning("GLM_API_KEY not set, using mock response")
            return f"[Mock response from {self.model}] {user_message}"

        messages = []

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "temperature": self.temperature,
            "top_p": 0.7,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.BASE_URL, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"Unexpected GLM response: {data}")
                    return "[Error] Unexpected response format"

        except httpx.TimeoutException:
            logger.error("GLM API timeout")
            return "[Error] GLM API request timed out"
        except httpx.HTTPError as e:
            logger.error(f"GLM API error: {e}")
            logger.error(f"Status: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
            if hasattr(e, 'response'):
                try:
                    logger.error(f"Response body: {e.response.text}")
                except:
                    pass
            return f"[Error] GLM API error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error calling GLM: {e}")
            return f"[Error] Unexpected error: {str(e)}"
