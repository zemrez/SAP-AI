"""Application configuration via pydantic-settings."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration – reads from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SAP connection
    SAP_BASE_URL: str = "https://localhost:44300/sap/opu/odata/sap"
    SAP_USERNAME: str = ""
    SAP_PASSWORD: str = ""
    SAP_CLIENT: str = "100"

    # LLM
    LLM_PROVIDER: Literal["gemini", "openai"] = "gemini"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_MAX_EXPLANATIONS: int = 10  # Max anomalies to send for LLM explanation per scan

    # App
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8011


settings = Settings()
