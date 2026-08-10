"""
Application configuration.

All environment-dependent values live here and nowhere else.
Reading os.environ directly anywhere outside this file is a code smell —
it means config is scattered instead of centralized, which makes it
harder to know what the app depends on and easy to forget a var on deploy.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "TraceLens"
    app_env: str = "development"

    database_url: str

    # Added now, used later (Day 8+) — declaring it early means the
    # Settings class doesn't need to change shape when we get there.
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"


# Instantiated once, imported everywhere. This is the one place
# in the whole app that reads environment variables.
settings = Settings()
