"""Data models for Trustee MCP Server."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class PolicyModel(BaseModel):
    """Policy data model."""

    id: str = Field(description="Policy ID", min_length=1)
    content: str = Field(description="Policy content", min_length=1)
    type: str = Field(description="Policy type", default="rego")
    created_at: Optional[datetime] = Field(default=None, description="Creation time")
    updated_at: Optional[datetime] = Field(default=None, description="Last update time")

    @validator("type")
    def validate_type(cls, v):
        if v not in ["rego", "json"]:
            raise ValueError('Type must be "rego" or "json"')
        return v


class ResourceModel(BaseModel):
    """Resource data model."""

    repository: str = Field(description="Resource repository", min_length=1)
    type: str = Field(description="Resource type", min_length=1)
    tag: str = Field(description="Resource tag", min_length=1)
    content: Union[str, bytes] = Field(description="Resource content")
    size: Optional[int] = Field(default=None, description="Resource size", ge=0)

    @property
    def full_name(self) -> str:
        """Get full resource name."""
        return f"{self.repository}/{self.type}:{self.tag}"


class AuditLogEntry(BaseModel):
    """Audit log entry model."""

    id: str = Field(description="Log entry ID")
    timestamp: str = Field(description="Log timestamp as ISO string")
    operation: str = Field(description="Operation performed")
    resource: str = Field(description="Resource affected")
    user: Optional[str] = Field(default=None, description="User who performed operation")
    status: str = Field(description="Operation status")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")

    @property
    def is_successful(self) -> bool:
        """Check if operation was successful."""
        return self.status.lower() in ["success", "completed", "ok", "200"]


class HealthStatus(BaseModel):
    """Health status model."""

    status: str = Field(description="Overall health status")
    components: Dict[str, str] = Field(description="Component health status")
    timestamp: datetime = Field(description="Status check timestamp")

    @property
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return self.status.lower() in ["healthy", "ok", "running"]


class RvpsReferenceValue(BaseModel):
    """RVPS reference value model."""

    name: str = Field(description="Reference value name", min_length=1)
    hash_value: str = Field(description="Hash value", min_length=1)
    version: str = Field(description="Message version", default="0.1.0")
    type: str = Field(description="Message type", default="sample")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    @validator("type")
    def validate_type(cls, v):
        valid_types = ["sample", "in-toto", "cocosigner"]
        if v.lower() not in valid_types:
            raise ValueError(f'Type must be one of: {", ".join(valid_types)}')
        return v.lower()


class PolicyListResponse(BaseModel):
    """Response model for policy list."""

    policies: List[PolicyModel] = Field(description="List of policies")
    total: int = Field(description="Total number of policies", ge=0)


class ResourceListResponse(BaseModel):
    """Response model for resource list."""

    resources: List[ResourceModel] = Field(description="List of resources")
    total: int = Field(description="Total number of resources", ge=0)


class AuditLogResponse(BaseModel):
    """Response model for audit logs."""

    logs: List[AuditLogEntry] = Field(description="List of audit log entries")
    total: int = Field(description="Total number of log entries", ge=0)
    has_more: bool = Field(description="Whether there are more entries")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(description="Error message", min_length=1)
    code: str = Field(description="Error code", min_length=1)
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
