from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load variables from .env if present
load_dotenv()

class Settings(BaseSettings):
    """Project configuration loaded from environment variables or .env file."""
    # Model config for Pydantic v2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # Make env var names case-insensitive
        env_prefix="",  # No prefix for env vars
        extra="ignore",  # Ignore unknown env keys (e.g., ADMIN_PORT, LOG_LEVEL)
    )

    # Bot settings
    bot_token: str = Field(..., alias="BOT_TOKEN")

    # Database settings with aliases for UPPERCASE env vars
    postgres_dsn: str | None = Field(None, alias="POSTGRES_DSN")
    postgres_host: str = Field("localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")
    postgres_db: str = Field("masterbot", alias="POSTGRES_DB")
    postgres_user: str = Field("masterbot", alias="POSTGRES_USER")
    postgres_password: str = Field("masterbot", alias="POSTGRES_PASSWORD")

    # Partner onboarding (superadmin invite)
    partner_invite_code: str | None = Field(None, alias="PARTNER_INVITE_CODE")

    # Admin settings
    @property
    def database_url(self) -> str:
        """Construct database URL from components or use DSN if provided."""
        if self.postgres_dsn:
            return self.postgres_dsn
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @model_validator(mode='after')
    def validate_database_config(self) -> 'Settings':
        """Validate database configuration."""
        if not self.postgres_dsn and not all([
            self.postgres_host,
            self.postgres_port,
            self.postgres_db,
            self.postgres_user,
            self.postgres_password
        ]):
            raise ValueError(
                "Either POSTGRES_DSN or all database connection parameters must be provided"
            )
        return self

@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
