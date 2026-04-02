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

    # Image Service
    image_service: str = "dall_e"  # or "local", "glm_vision"
    openai_api_key: Optional[str] = None

    # API
    api_key_header: str = ""  # X-API-Key for auth (empty = disabled)

    # WebSocket
    ws_host: str = "localhost"
    ws_port: int = 8000

    # Environment
    environment: str = "development"
    debug: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
