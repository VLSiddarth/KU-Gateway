"""Configuration management for KU-Gateway (Pydantic v2 compatible)."""

from typing import Optional, List, Dict
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

class Settings(BaseSettings):
    """KU-Gateway configuration settings."""

    # Core settings
    host: str = Field("0.0.0.0", alias="KU_GATEWAY_HOST")
    port: int = Field(8000, alias="KU_GATEWAY_PORT")
    debug: bool = Field(False, alias="KU_GATEWAY_DEBUG")
    workers: int = Field(4, alias="KU_GATEWAY_WORKERS")

    # KU API settings
    ku_api_key: str = Field(..., alias="KU_API_KEY")
    ku_api_url: str = Field("https://api.knowledgeuniverse.tech", alias="KU_API_URL")
    ku_api_timeout: int = Field(30, alias="KU_API_TIMEOUT")

    # Decay threshold
    decay_threshold: float = Field(0.5, alias="KU_DECAY_THRESHOLD", ge=0.0, le=1.0)

    # Source-specific thresholds (optional overrides)
    source_thresholds: Dict[str, float] = Field(
        default_factory=dict,
        alias="KU_SOURCE_THRESHOLDS"
    )

    # Rate limiting
    rate_limit: int = Field(100, alias="KU_RATE_LIMIT")

    # Redis cache
    redis_enabled: bool = Field(False, alias="KU_REDIS_ENABLED")
    redis_url: Optional[str] = Field(None, alias="KU_REDIS_URL")
    redis_ttl: int = Field(3600, alias="KU_REDIS_TTL")

    # Vault (BYOK)
    vault_enabled: bool = Field(False, alias="KU_VAULT_ENABLED")
    vault_api_url: Optional[str] = Field(None, alias="KU_VAULT_API_URL")

    # Telemetry
    telemetry_enabled: bool = Field(True, alias="KU_TELEMETRY_ENABLED")
    telemetry_colors: bool = Field(True, alias="KU_TELEMETRY_COLORS")
    telemetry_tables: bool = Field(True, alias="KU_TELEMETRY_TABLES")
    telemetry_log_level: str = Field("info", alias="KU_LOG_LEVEL")

    # Security
    allowed_origins: List[str] = Field(["*"], alias="KU_ALLOWED_ORIGINS")
    allowed_hosts: List[str] = Field(["*"], alias="KU_ALLOWED_HOSTS")

    # LLM providers
    openai_compatible_endpoints: List[str] = Field(
        ["openai.com", "api.openai.com", "api.anthropic.com", "api.gemini.google.com"],
        alias="KU_OPENAI_ENDPOINTS"
    )

    # Upstream LLM provider (not part of KU API)
    upstream_llm_base_url: str = Field(
        "https://api.openai.com", alias="UPSTREAM_LLM_BASE_URL"
    )
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")

    # KU API query difficulty (1-5)
    ku_difficulty: int = Field(3, alias="KU_DIFFICULTY", ge=1, le=5)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # ignore extra env vars
    )

    @field_validator("ku_api_key")
    @classmethod
    def validate_api_key(cls, v):
        if not v.startswith("ku_"):
            raise ValueError("API key must start with 'ku_'")
        return v

    @field_validator("source_thresholds", mode="before")
    @classmethod
    def parse_source_thresholds(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON for source_thresholds")
        return v