"""Configuration management for Trustee MCP Server."""

import os
from typing import Optional

from pydantic import BaseModel, Field


class TrusteeConfig(BaseModel):
    """Configuration for Trustee Gateway connection."""

    base_url: str = Field(
        default="http://localhost:8081", description="Base URL for Trustee Gateway"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds", ge=1)
    max_retries: int = Field(
        default=3, description="Maximum number of retries for failed requests", ge=0
    )
    kbs_auth_private_key_path: Optional[str] = Field(
        default=None, description="Path to KBS authentication private key file (ED25519 PEM format)"
    )

    class Config:
        env_prefix = "TRUSTEE_"

    @classmethod
    def from_env(cls) -> "TrusteeConfig":
        """Create configuration from environment variables."""
        return cls(
            base_url=os.getenv("TRUSTEE_GATEWAY_URL")
            or os.getenv("TRUSTEE_BASE_URL", "http://localhost:8081"),
            timeout=int(os.getenv("TRUSTEE_TIMEOUT", "30")),
            max_retries=int(os.getenv("TRUSTEE_MAX_RETRIES", "3")),
            kbs_auth_private_key_path=os.getenv("TRUSTEE_KBS_AUTH_PRIVATE_KEY_PATH"),
        )


def load_config() -> TrusteeConfig:
    """Load configuration from environment variables."""
    return TrusteeConfig.from_env()
