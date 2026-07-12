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
    challenger_model: str = "meta/llama-3.1-70b-instruct"

    # Policy
    policy_path: str = "./policy/policy_v1.yaml"

    # Database (Phase 2)
    database_url: str = "sqlite:///./audit.db"

    # API
    app_title: str = "Credit Decisioning Agent"
    app_version: str = "0.1.0"
    debug: bool = False

    def model_post_init(self, __context: object) -> None:
        """Inject loaded values into os.environ so sub-modules can use os.environ directly."""
        os.environ.setdefault("GITHUB_TOKEN", self.github_token)
        os.environ.setdefault("GITHUB_MODELS_ENDPOINT", self.github_models_endpoint)
        os.environ.setdefault("PRIMARY_MODEL", self.primary_model)
        os.environ.setdefault("CHALLENGER_MODEL", self.challenger_model)
        os.environ.setdefault("POLICY_PATH", self.policy_path)
        os.environ.setdefault("DATABASE_URL", self.database_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings()


# Module-level singleton
settings = get_settings()
