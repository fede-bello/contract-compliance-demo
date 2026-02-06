from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ============================================================================
    # API Keys and Credentials
    # ============================================================================
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None

    LLAMA_CLOUD_API_KEY: str | None = None
    LLAMA_CLOUD_BASE_URL: str = "https://api.cloud.llamaindex.ai"

    # ============================================================================
    # Validation
    # ============================================================================

    @model_validator(mode="after")
    def validate_credentials(self) -> "Config":
        """Validate required credentials are present."""

        missing = []

        # Validate LlamaCloud credentials
        if not self.LLAMA_CLOUD_API_KEY:
            missing.append("LLAMA_CLOUD_API_KEY")

        # Validate Anthropic credentials
        if not self.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")

        # Validate OpenAI credentials
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")

        if missing:
            raise ValueError(f"Missing required credentials: {', '.join(missing)}")

        return self

    # ============================================================================
    # Workflow Server
    # ============================================================================
    WORKFLOW_SERVER_HOST: str = "0.0.0.0"
    WORKFLOW_SERVER_PORT: int = 8080

    DEBUG: bool = Field(
        default=False, description="Enable debug mode to save workflow step inputs"
    )


@lru_cache
def get_settings() -> Config:
    """Get cached configuration instance."""
    return Config()
