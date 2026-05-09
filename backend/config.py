from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# ──────────────────────────────────────────────
#  DB 경로 절대 경로 계산 (실행 위치 무관)
#  - config.py 기준: backend/ 디렉토리
#  - 목표: 항상 backend/ai_company.db 를 가리킴
# ──────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent
_DEFAULT_SQLITE_PATH = _BACKEND_DIR / "ai_company.db"
_DEFAULT_DATABASE_URL = f"sqlite:///{_DEFAULT_SQLITE_PATH}"


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Database (SQLite for development, PostgreSQL for production)
    # 기본값: backend/ai_company.db 의 절대 경로 (실행 cwd 무관)
    database_url: str = _DEFAULT_DATABASE_URL

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

    # OpenClaw Gateway (Mac Mini - 실세계 작업 위임)
    openclaw_enabled: bool = False
    openclaw_base_url: str = "http://mac-mini.local:18789"
    openclaw_api_key: str = ""
    openclaw_timeout: float = 180.0
    openclaw_fallback_host: str = ""  # mDNS 실패 시 정적 IP 백업

    # OpenClaw WebSocket RPC
    openclaw_ws_enabled: bool = True  # WS 먼저 시도, 실패 시 HTTP 폴백
    openclaw_ws_endpoint: str = ""  # 직접 지정 시 프로브 생략 (e.g. "ws://172.30.1.18:18789/")
    openclaw_ws_probe_timeout: float = 5.0
    openclaw_ws_cache_ttl: int = 3600
    openclaw_device_state_path: str = "backend/state/openclaw_device.json"
    openclaw_requested_scopes: str = "operator.admin,operator.read,operator.write,operator.approvals,operator.pairing"
    openclaw_client_id: str = "openclaw-control-ui"
    openclaw_client_version: str = "local-dev"

    # Image Service
    image_service: str = "dall_e"  # or "local", "glm_vision"

    # API
    api_key_header: str = ""  # X-API-Key for auth (empty = disabled)

    # WebSocket
    ws_host: str = "0.0.0.0"
    ws_port: int = 8001

    # Environment
    environment: str = "development"

    debug: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
