"""환경변수 기반 설정. API Key는 코드/저장소에 두지 않는다."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    llm_provider: str = "mock"  # mock | anthropic | openai_compatible
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = ""
    database_url: str = "sqlite:///./data/humor.db"
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    max_upload_bytes: int = 4 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.environ.get
        return cls(
            llm_provider=e("HUMOR_LLM_PROVIDER", "mock").strip().lower(),
            anthropic_api_key=e("ANTHROPIC_API_KEY", ""),
            anthropic_model=e("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
            openai_api_key=e("OPENAI_API_KEY", ""),
            openai_base_url=e("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            openai_model=e("OPENAI_MODEL", ""),
            database_url=e("DATABASE_URL", "sqlite:///./data/humor.db"),
            cors_origins=[o.strip() for o in e("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()],
        )
