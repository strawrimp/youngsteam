"""Service for GLM API communication with Zhipu AI JWT authentication."""

import httpx
import json
import jwt
import time
from typing import List, Dict, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class GLMService:
    """Wrapper for GLM API calls with Zhipu AI JWT authentication."""

    BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(self, api_key: str = "", model: str = "glm-4", temperature: float = 0.7):
        """Initialize GLM service.

        Args:
            api_key: Zhipu AI API key (format: KEY_ID.KEY_SECRET)
            model: Model name (default: glm-4)
            temperature: Temperature for generation
        """
        self.api_key = api_key or settings.glm_api_key
        self.model = model or settings.glm_model
        self.temperature = temperature or settings.glm_temperature

    def _generate_jwt_token(self) -> str:
        """Generate JWT token for Zhipu AI authentication.

        Zhipu AI requires special JWT format with:
        1. Header includes "sign_type": "SIGN"
        2. Timestamps in milliseconds (not seconds)
        3. HS256 algorithm with API secret

        Returns:
            JWT token string

        Raises:
            ValueError: If API key format is invalid
        """
        if not self.api_key or "." not in self.api_key:
            raise ValueError(
                "Invalid API key format. Expected: KEY_ID.KEY_SECRET"
            )

        # Split API key into ID and secret
        key_id, key_secret = self.api_key.split(".", 1)

        # Generate JWT with Zhipu AI requirements
        now_ms = int(round(time.time() * 1000))
        exp_ms = now_ms + 3600 * 1000  # 1 hour expiration in milliseconds

        headers = {
            "alg": "HS256",
            "sign_type": "SIGN",  # Zhipu AI required field
        }

        payload = {
            "api_key": key_id,
            "exp": exp_ms,  # Milliseconds
            "timestamp": now_ms,  # Milliseconds
        }

        token = jwt.encode(
            payload=payload,
            key=key_secret,
            algorithm="HS256",
            headers=headers,
        )

        logger.debug(f"Generated JWT token (expires in 1 hour)")
        return token

    async def call_model(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> str:
        """Call GLM model with a message using JWT authentication.

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

        try:
            # Generate JWT token with Zhipu AI format
            token = self._generate_jwt_token()

            messages = []

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Build request headers with JWT token
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [{"role": "system", "content": system_prompt}] + messages,
                "temperature": self.temperature,
                "top_p": 0.7,
            }

            logger.debug(f"Calling GLM API with model: {self.model}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.BASE_URL,
                    json=payload,
                    headers=headers,
                )

                if response.status_code != 200:
                    logger.error(
                        f"GLM API error {response.status_code}: {response.text}"
                    )
                    response.raise_for_status()

                data = response.json()

                if "choices" in data and len(data["choices"]) > 0:
                    result = data["choices"][0]["message"]["content"]
                    logger.debug(f"GLM response received ({len(result)} chars)")
                    return result
                else:
                    logger.error(f"Unexpected GLM response: {data}")
                    return "[Error] Unexpected response format"

        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return f"[Error] Configuration error: {str(e)}"
        except httpx.TimeoutException:
            logger.error("GLM API timeout")
            return "[Error] GLM API request timed out"
        except httpx.HTTPError as e:
            logger.error(f"GLM API error: {e}")
            if hasattr(e, "response"):
                try:
                    logger.error(f"Response body: {e.response.text}")
                except:
                    pass
            return f"[Error] GLM API error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error calling GLM: {e}")
            return f"[Error] Unexpected error: {str(e)}"
