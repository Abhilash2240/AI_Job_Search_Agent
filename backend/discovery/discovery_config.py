# backend/discovery/discovery_config.py
"""Discovery integration configuration with environment variable validation."""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Ensure environment variables from backend/.env and .env are loaded
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()


class DiscoverySettings(BaseModel):
    """Runtime configuration for job discovery providers and orchestration."""
    firecrawl_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("FIRECRAWL_API_KEY")
    )
    greenhouse_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GREENHOUSE_API_KEY")
    )
    lever_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("LEVER_API_KEY")
    )
    
    # Concurrency and rate limiting
    max_concurrency: int = Field(
        default_factory=lambda: int(os.getenv("DISCOVERY_MAX_CONCURRENCY", "5"))
    )
    request_timeout: float = Field(
        default_factory=lambda: float(os.getenv("DISCOVERY_REQUEST_TIMEOUT", "15.0"))
    )
    retry_limit: int = Field(
        default_factory=lambda: int(os.getenv("DISCOVERY_RETRY_LIMIT", "3"))
    )
    rate_limit: float = Field(
        default_factory=lambda: float(os.getenv("DISCOVERY_RATE_LIMIT", "5.0"))
    )
    batch_size: int = Field(
        default_factory=lambda: int(os.getenv("DISCOVERY_BATCH_SIZE", "20"))
    )

    @property
    def FIRECRAWL_API_KEY(self) -> Optional[str]:
        return self.firecrawl_api_key

    @property
    def GREENHOUSE_API_KEY(self) -> Optional[str]:
        return self.greenhouse_api_key

    @property
    def LEVER_API_KEY(self) -> Optional[str]:
        return self.lever_api_key

    @property
    def DISCOVERY_MAX_CONCURRENCY(self) -> int:
        return self.max_concurrency

    @property
    def DISCOVERY_REQUEST_TIMEOUT(self) -> float:
        return self.request_timeout

    @property
    def DISCOVERY_RETRY_LIMIT(self) -> int:
        return self.retry_limit

    @property
    def DISCOVERY_RATE_LIMIT(self) -> float:
        return self.rate_limit

    @property
    def DISCOVERY_BATCH_SIZE(self) -> int:
        return self.batch_size

    @property
    def DISCOVERY_USER_AGENT(self) -> str:
        return os.getenv("DISCOVERY_USER_AGENT", "AI-Job-Search-Agent-Discovery/1.0")

    @property
    def has_firecrawl(self) -> bool:
        """Whether a usable Firecrawl API key is present."""
        return bool(self.firecrawl_api_key and len(self.firecrawl_api_key.strip()) > 5)

    def sanitized_dict(self) -> dict:
        """Return configuration summary with credentials redacted."""
        return {
            "has_firecrawl": self.has_firecrawl,
            "has_greenhouse_key": bool(self.greenhouse_api_key),
            "has_lever_key": bool(self.lever_api_key),
            "max_concurrency": self.max_concurrency,
            "request_timeout": self.request_timeout,
            "retry_limit": self.retry_limit,
            "rate_limit": self.rate_limit,
            "batch_size": self.batch_size,
        }


_settings_instance: Optional[DiscoverySettings] = None


def get_discovery_settings() -> DiscoverySettings:
    """Retrieve singleton discovery settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = DiscoverySettings()
    return _settings_instance

discovery_settings = get_discovery_settings()
