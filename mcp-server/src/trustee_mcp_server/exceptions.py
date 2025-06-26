"""Exception classes for Trustee MCP Server."""

from typing import Any, Dict, Optional


class TrusteeError(Exception):
    """Base exception for Trustee MCP Server."""

    def __init__(
        self, message: str, code: str = "UNKNOWN_ERROR", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class TrusteeClientError(TrusteeError):
    """Exception for HTTP client errors."""

    def __init__(
        self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None
    ):
        super().__init__(message, "CLIENT_ERROR")
        self.status_code = status_code
        self.response_text = response_text


class TrusteeConfigError(TrusteeError):
    """Exception for configuration errors."""

    def __init__(self, message: str):
        super().__init__(message, "CONFIG_ERROR")


class TrusteeValidationError(TrusteeError):
    """Exception for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, "VALIDATION_ERROR", {"field": field})
        self.field = field


class TrusteeToolError(TrusteeError):
    """Exception for tool execution errors."""

    def __init__(self, message: str, tool_name: str):
        super().__init__(message, "TOOL_ERROR", {"tool": tool_name})
        self.tool_name = tool_name
