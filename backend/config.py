from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Database (SQLite for development, PostgreSQL for production)
    database_url: str = "sqlite:///./ai_company.db"

    # GLM API (Legacy - for backward compatibility)
    glm_api_key: str = ""
    glm_model: str = "glm-4"
    glm_temperature: float = 0.7

    # DeepSeek API (Primary LLM)
    deepseek_api_key: str = ""
    deepseek_model: str = "v4"  # "v4" or "r1"
    deepseek_temperature: float = 0.7
    deepseek_enable_hybrid: bool = True  # Enable automatic V4/R1 selection

    # Multi-Provider LLM Service
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"

    # Gemini API (Fallback #1)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash-preview-05-20"
    gemini_temperature: float = 0.7
    gemini_max_retries: int = 3

    # Image Service
    image_service: str = "dall_e"  # or "local", "glm_vision"

    # API
    api_key_header: str = ""  # X-API-Key for auth (empty = disabled)

    # WebSocket
    ws_host: str = "0.0.0.0"
    ws_port: int = 8000

    # Environment
    environment: str = "development"
    debug: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
