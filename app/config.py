"""
Application settings — loads from .env via python-dotenv.

Import `settings` anywhere config values are needed:

    from app.config import settings
    print(settings.primary_model)
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # GitHub Models
    github_token: str = ""
    github_models_endpoint: str = "https://models.github.ai/inference"
    primary_model: str = "openai/gpt-4o-mini"
    challenger_model: str = "openai/gpt-4o-mini"

    # Policy
    policy_path: str = "./policy/policy_v1.yaml"

    # Database (Phase 2)
    database_url: str = "sqlite:///./audit.db"

    # API
    app_title: str = "Credit Decisioning Agent"
    app_version: str = "0.1.0"
    debug: bool = False

    # CORS — comma-separated list of allowed origins.
    # Dev default allows local frontend servers.
    # Production: set ALLOWED_ORIGINS=https://your-app.example.com in .env
    allowed_origins: str = (
        "http://localhost:5173,"
        "http://localhost:3000,"
        "http://localhost:8000,"
        "http://127.0.0.1:5173,"
        "http://127.0.0.1:3000,"
        "http://127.0.0.1:8000"
    )

    # Rate limiting
    rate_limit_requests: int = 10   # max POST/PUT/PATCH requests per window per IP
    rate_limit_window: int = 60     # window size in seconds

    # Lender identity — used in adverse action notices
    lender_name: str = "Credit Decisioning Ltd"
    lender_contact: str = "decisions@creditagent.example.com | 0800 123 4567"

    def model_post_init(self, __context: object) -> None:
        """Inject loaded values into os.environ so sub-modules can use os.environ directly."""
        os.environ.setdefault("GITHUB_TOKEN", self.github_token)
        os.environ.setdefault("GITHUB_MODELS_ENDPOINT", self.github_models_endpoint)
        os.environ.setdefault("PRIMARY_MODEL", self.primary_model)
        os.environ.setdefault("CHALLENGER_MODEL", self.challenger_model)
        os.environ.setdefault("POLICY_PATH", self.policy_path)
        os.environ.setdefault("DATABASE_URL", self.database_url)
        os.environ.setdefault("RATE_LIMIT_REQUESTS", str(self.rate_limit_requests))
        os.environ.setdefault("RATE_LIMIT_WINDOW", str(self.rate_limit_window))
        os.environ.setdefault("LENDER_NAME", self.lender_name)
        os.environ.setdefault("LENDER_CONTACT", self.lender_contact)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings()


# Module-level singleton
settings = get_settings()
