"""Trustee MCP Server package."""

from .client import TrusteeClient
from .config import TrusteeConfig, load_config
from .exceptions import (
    TrusteeClientError,
    TrusteeConfigError,
    TrusteeError,
    TrusteeToolError,
    TrusteeValidationError,
)
from .models import (
    AuditLogEntry,
    AuditLogResponse,
    ErrorResponse,
    HealthStatus,
    PolicyListResponse,
    PolicyModel,
    ResourceListResponse,
    ResourceModel,
    RvpsReferenceValue,
)
from .server import TrusteeMCPServer, create_server

__version__ = "0.1.0"

__all__ = [
    "TrusteeClient",
    "TrusteeConfig",
    "load_config",
    "TrusteeError",
    "TrusteeClientError",
    "TrusteeConfigError",
    "TrusteeValidationError",
    "TrusteeToolError",
    "PolicyModel",
    "ResourceModel",
    "AuditLogEntry",
    "HealthStatus",
    "RvpsReferenceValue",
    "PolicyListResponse",
    "ResourceListResponse",
    "AuditLogResponse",
    "ErrorResponse",
    "TrusteeMCPServer",
    "create_server",
]
