"""
config.py — Application configuration via pydantic-settings.

pydantic-settings reads values from environment variables (and optionally a
.env file). Fields are type-validated and raise a clear error on startup if
a required variable is missing — better than discovering it at runtime.

Usage anywhere in the app:
    from price_service.config import settings
    print(settings.database_url)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # model_config tells pydantic-settings to also read from a .env file if
    # present, but environment variables always take precedence over .env.
    # This means docker-compose can inject vars directly without a .env file.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Database ---
    # Full async-compatible DSN. asyncpg requires the postgresql+asyncpg:// scheme.
    # Example: postgresql+asyncpg://user:pass@localhost:5432/pricepilot
    database_url: str

    # --- RabbitMQ ---
    # Standard AMQP URL. aio-pika uses this to connect to RabbitMQ.
    # Example: amqp://guest:guest@localhost:5672/
    rabbitmq_url: str

    # --- Service ---
    # Identifies the environment in logs and observability tooling.
    environment: str = "dev"


# A single module-level instance that the rest of the app imports.
# This is the "settings singleton" pattern — instantiated once at import time.
settings = Settings()
