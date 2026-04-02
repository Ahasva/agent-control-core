from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "agent-control-core"

    use_mock_llm: bool = True

    openai_api_key: str | None = None
    planner_model: str = "gpt-5.4-mini"
    risk_model: str = "gpt-5.4-mini"
    explanation_model: str = "gpt-4o-mini"
    fallback_model: str = "gpt-4o-mini"

    audit_enabled: bool = True
    fail_closed: bool = True

    serial_enabled: bool = Field(default=False)
    serial_port: str | None = Field(default=None)
    serial_baudrate: int = Field(default=115200)
    serial_timeout: float = Field(default=1.0)