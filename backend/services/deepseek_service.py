"""Service for DeepSeek API communication with hybrid V4 + R1 model selection."""

import httpx
import json
import time
from typing import List, Dict, Optional, Tuple, Any
from config import settings
import logging

logger = logging.getLogger(__name__)


class DeepSeekService:
    """Wrapper for DeepSeek API calls with intelligent V4/R1 model selection.

    This service implements a hybrid strategy:
    - DeepSeek V4: For standard tasks (~70% of operations)
    - DeepSeek R1: For complex reasoning tasks (voting, strategy, analysis)
    """

    BASE_URL = "https://api.deepseek.com/chat/completions"

    MODELS = {
        "v4": "deepseek-chat",  # Fast, cost-effective for standard tasks
        "r1": "deepseek-reasoner",  # Advanced reasoning for complex tasks
    }

    # Task types that require R1 (complex reasoning)
    R1_REQUIRED_TASKS = {
        "voting",  # Consensus decisions require careful reasoning
        "strategy",  # Strategic planning needs R1
        "analysis",  # Data analysis needs R1
        "math",  # Mathematical reasoning
        "reasoning",  # General complex reasoning
        "decision",  # Final decisions
    }

    # Task types recommended for R1 but can use V4
    R1_RECOMMENDED_TASKS = {
        "architecture",  # Architecture decisions
        "insight",  # Generating insights
        "evaluation",  # Evaluating options
        "code_review",  # Code review (if complex)
    }

    def __init__(
        self,
        api_key: str = "",
        model: str = "v4",
        temperature: float = 0.7,
        enable_hybrid: bool = True,
    ):
        """Initialize DeepSeek service.

        Args:
            api_key: DeepSeek API key
            model: Primary model ('v4' or 'r1', default: 'v4')
            temperature: Temperature for generation
            enable_hybrid: Enable automatic V4/R1 selection (default: True)
        """
        self.api_key = api_key or settings.deepseek_api_key
        self.primary_model = model
        self.temperature = temperature or settings.deepseek_temperature
        self.enable_hybrid = enable_hybrid
        self.model_usage = {"v4": 0, "r1": 0}  # Track usage statistics

        # Validate model choice
        if self.primary_model not in self.MODELS:
            logger.warning(f"Invalid model '{self.primary_model}', using 'v4'")
            self.primary_model = "v4"

    def _should_use_r1(
        self,
        task_type: str = "default",
        complexity: float = 0.0,
    ) -> bool:
        """Determine whether to use R1 or V4 for a given task.

        Args:
            task_type: Type of task being performed
            complexity: Complexity score (0.0 to 1.0)

        Returns:
            True if R1 should be used, False for V4
        """
        if not self.enable_hybrid:
            return self.primary_model == "r1"

        # R1 is required for these task types
        if task_type.lower() in self.R1_REQUIRED_TASKS:
            return True

        # R1 is recommended if complexity is high
        if task_type.lower() in self.R1_RECOMMENDED_TASKS:
            if complexity >= 0.7:  # Complexity threshold
                return True

        # Default to V4 for all other cases
        return False

    async def call_model(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        task_type: str = "default",
        complexity: float = 0.0,
    ) -> str:
        """Call DeepSeek model with automatic V4/R1 selection.

        Args:
            system_prompt: System prompt for the model
            user_message: User message
            conversation_history: Previous messages in conversation
            task_type: Type of task (used for model selection)
            complexity: Task complexity score (0.0-1.0)

        Returns:
            Model's response
        """
        response, model_used = await self.call_model_with_type(
            system_prompt=system_prompt,
            user_message=user_message,
            conversation_history=conversation_history,
            task_type=task_type,
            complexity=complexity,
        )
        return response

    async def call_model_with_type(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        task_type: str = "default",
        complexity: float = 0.0,
    ) -> Tuple[str, str]:
        """Call DeepSeek model and return both response and model type used.

        Args:
            system_prompt: System prompt for the model
            user_message: User message
            conversation_history: Previous messages in conversation
            task_type: Type of task (used for model selection)
            complexity: Task complexity score (0.0-1.0)

        Returns:
            Tuple of (response, model_type_used)
        """
        if not self.api_key:
            # Fallback for testing: echo with a prefix
            logger.warning("DEEPSEEK_API_KEY not set, using mock response")
            model_type = "r1" if self._should_use_r1(task_type, complexity) else "v4"
            return (
                f"[Mock response from {self.MODELS[model_type]}] {user_message}",
                model_type,
            )

        try:
            # Determine which model to use
            use_r1 = self._should_use_r1(task_type, complexity)
            model_type = "r1" if use_r1 else "v4"
            model_name = self.MODELS[model_type]

            # Track usage
            self.model_usage[model_type] += 1

            messages = []

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Build request headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model_name,
                "messages": [{"role": "system", "content": system_prompt}] + messages,
                "temperature": self.temperature,
                "top_p": 0.95,
                "max_tokens": 8192,
            }

            logger.debug(
                f"Calling DeepSeek API with model: {model_name} "
                f"(task_type={task_type}, complexity={complexity})"
            )

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.BASE_URL,
                    json=payload,
                    headers=headers,
                )

                if response.status_code != 200:
                    logger.error(
                        f"DeepSeek API error {response.status_code}: {response.text}"
                    )
                    response.raise_for_status()

                data = response.json()

                if "choices" in data and len(data["choices"]) > 0:
                    result = data["choices"][0]["message"]["content"]
                    logger.debug(
                        f"DeepSeek {model_type} response received ({len(result)} chars)"
                    )
                    return result, model_type
                else:
                    logger.error(f"Unexpected DeepSeek response: {data}")
                    return "[Error] Unexpected response format", model_type

        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return f"[Error] Configuration error: {str(e)}", "v4"
        except httpx.TimeoutException:
            logger.error("DeepSeek API timeout")
            return "[Error] DeepSeek API request timed out", "v4"
        except httpx.HTTPError as e:
            logger.error(f"DeepSeek API error: {e}")
            if hasattr(e, "response"):
                try:
                    logger.error(f"Response body: {e.response.text}")
                except Exception:
                    pass
            return f"[Error] DeepSeek API error: {str(e)}", "v4"
        except Exception as e:
            logger.error(f"Unexpected error calling DeepSeek: {e}")
            return f"[Error] Unexpected error: {str(e)}", "v4"

    def get_model_usage_stats(self) -> Dict:
        """Get statistics on model usage (V4 vs R1).

        Returns:
            Dict with usage counts and percentages
        """
        total = self.model_usage["v4"] + self.model_usage["r1"]
        if total == 0:
            return {
                "v4_count": 0,
                "r1_count": 0,
                "v4_percent": 0.0,
                "r1_percent": 0.0,
            }

        return {
            "v4_count": self.model_usage["v4"],
            "r1_count": self.model_usage["r1"],
            "total": total,
            "v4_percent": round(100 * self.model_usage["v4"] / total, 1),
            "r1_percent": round(100 * self.model_usage["r1"] / total, 1),
        }

    def reset_usage_stats(self):
        """Reset model usage statistics."""
        self.model_usage = {"v4": 0, "r1": 0}

    async def call_model_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict]] = None,
        task_type: str = "default",
        complexity: float = 0.0,
    ) -> Dict[str, Any]:
        """Call DeepSeek model with tool/function calling support.

        Args:
            system_prompt: System prompt
            user_message: User message
            tools: List of tool schemas (OpenAI function calling format)
            conversation_history: Previous conversation
            task_type: Task type for model selection
            complexity: Complexity score for model selection

        Returns:
            Dict with 'content' (str), 'tool_calls' (list), 'model_used' (str)
        """
        if not self.api_key:
            return {
                "content": f"[Mock] {user_message}",
                "tool_calls": [],
                "model_used": "v4",
            }

        try:
            use_r1 = self._should_use_r1(task_type, complexity)
            # R1 doesn't support function calling - use V4 for tool use
            model_name = self.MODELS["v4"]
            model_type = "v4"
            self.model_usage[model_type] += 1

            messages = [{"role": "system", "content": system_prompt}]
            if conversation_history:
                messages.extend(conversation_history)
            if user_message:  # Only add user message if non-empty
                messages.append({"role": "user", "content": user_message})

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.4,  # Lower temp for more focused responses
                "top_p": 0.9,
                "frequency_penalty": 0.3,  # Reduce repetitive self-intro patterns
                "max_tokens": 8192,
                "tools": tools,
                "tool_choice": "auto",
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.BASE_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

            if "choices" not in data or not data["choices"]:
                return {
                    "content": "[Error] No response",
                    "tool_calls": [],
                    "model_used": model_type,
                }

            message = data["choices"][0]["message"]
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []

            # Parse tool calls
            parsed_tool_calls = []
            for tc in tool_calls:
                if tc.get("type") == "function":
                    try:
                        args = json.loads(tc["function"].get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}
                    parsed_tool_calls.append(
                        {
                            "id": tc.get("id", ""),
                            "name": tc["function"]["name"],
                            "arguments": args,
                        }
                    )

            return {
                "content": content,
                "tool_calls": parsed_tool_calls,
                "model_used": model_type,
                "raw_message": message,
            }

        except httpx.TimeoutException:
            logger.error("DeepSeek tool call timeout")
            return {"content": "[Error] Timeout", "tool_calls": [], "model_used": "v4"}
        except Exception as e:
            logger.error(f"DeepSeek tool call error: {e}")
            return {
                "content": f"[Error] {str(e)}",
                "tool_calls": [],
                "model_used": "v4",
            }
