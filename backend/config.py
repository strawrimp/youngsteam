from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Database
    database_url: str = "postgresql://localhost/ai_company"

    # GLM API
    glm_api_key: str = ""
    glm_model: str = "glm-4"
    glm_temperature: float = 0.7

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
