"""HTTP client for Trustee Gateway API."""

import base64
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
import structlog

from .config import TrusteeConfig
from .exceptions import TrusteeClientError
from .jwt_auth import JWTAuthenticator
from .models import (
    AuditLogEntry,
    AuditLogResponse,
    HealthStatus,
    PolicyListResponse,
    PolicyModel,
    ResourceListResponse,
    ResourceModel,
    RvpsReferenceValue,
)

logger = structlog.get_logger()


class TrusteeClient:
    """HTTP client for Trustee Gateway API."""

    def __init__(self, config: TrusteeConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.jwt_auth = JWTAuthenticator(config.kbs_auth_private_key_path)
        self.client = httpx.AsyncClient(timeout=config.timeout, headers=self._get_headers())

    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with JWT authentication for KBS operations."""
        headers = self._get_headers()
        if self.jwt_auth.is_configured():
            try:
                token = self.jwt_auth.create_auth_token()
                headers["Authorization"] = f"Bearer {token}"
            except ValueError as e:
                logger.warning("Failed to create JWT auth token", error=str(e))
        return headers

    def _encode_base64_urlsafe(self, content: str) -> str:
        """Encode string content as URL-safe base64 without padding."""
        if not content:
            return ""
        # Use URL-safe base64 encoding and remove padding
        encoded_bytes = base64.urlsafe_b64encode(content.encode("utf-8"))
        encoded_str = encoded_bytes.decode("ascii")

        # Remove padding characters
        return encoded_str.rstrip("=")
    
    def _encode_base64(self, content: str) -> str:
        """Encode string content as base64 without padding."""
        if not content:
            return ""
        # Use standard base64 encoding and remove padding
        encoded_bytes = base64.b64encode(content.encode("utf-8"))
        encoded_str = encoded_bytes.decode("ascii")

        return encoded_str

    def _decode_base64_urlsafe(self, content: str) -> str:
        """Decode URL-safe base64 content without padding."""
        if not content:
            return ""
        try:
            # Add padding if necessary for decoding
            missing_padding = len(content) % 4
            if missing_padding:
                content += "=" * (4 - missing_padding)
            return base64.urlsafe_b64decode(content).decode("utf-8")
        except Exception as e:
            logger.warning(
                "Failed to decode URL-safe base64 content, using raw content", error=str(e)
            )
            return content

    def _decode_base64(self, content: str) -> str:
        """Decode base64 content to string."""
        try:
            return base64.b64decode(content).decode("utf-8")
        except Exception as e:
            logger.warning("Failed to decode base64 content, using raw content", error=str(e))
            return content

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make HTTP request with error handling."""
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        try:
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            )
            response.raise_for_status()
            return response
        except httpx.RequestError as e:
            logger.error("Request failed", url=url, error=str(e))
            raise TrusteeClientError(f"Request failed: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error", url=url, status=e.response.status_code, response=e.response.text
            )
            raise TrusteeClientError(f"HTTP {e.response.status_code}: {e.response.text}")

    async def _request_with_auth(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make HTTP request with JWT authentication."""
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        try:
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=self._get_auth_headers(),
            )
            response.raise_for_status()
            return response
        except httpx.RequestError as e:
            logger.error("Request failed", url=url, error=str(e))
            raise TrusteeClientError(f"Request failed: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error", url=url, status=e.response.status_code, response=e.response.text
            )
            raise TrusteeClientError(f"HTTP {e.response.status_code}: {e.response.text}")

    # Policy Management
    async def list_policies(self) -> PolicyListResponse:
        """List all attestation policies."""
        response = await self._request("GET", "/api/kbs/v0/attestation-policies")
        data = response.json()
        policies = [PolicyModel(id=k, content=v, type="rego") for k, v in data.items()]
        return PolicyListResponse(policies=policies, total=len(policies))

    async def get_policy(self, policy_id: str) -> PolicyModel:
        """Get specific attestation policy by ID."""
        response = await self._request("GET", f"/api/kbs/v0/attestation-policy/{policy_id}")
        # Try URL-safe decoding first, fallback to standard decoding
        try:
            content = self._decode_base64_urlsafe(response.text)
        except Exception:
            content = self._decode_base64(response.text)
        return PolicyModel(id=policy_id, content=content, type="rego")

    async def create_policy(self, policy_data: Dict[str, Any]) -> PolicyModel:
        """Create new attestation policy."""
        encoded_policy_data = {
            "policy_id": policy_data.get("policy_id", ""),
            "type": policy_data.get("type", "rego"),
            "policy": self._encode_base64_urlsafe(policy_data.get("content", "")),
        }
        await self._request_with_auth(
            "POST", "/api/kbs/v0/attestation-policy", json_data=encoded_policy_data
        )
        return PolicyModel(
            id=policy_data.get("policy_id", ""),
            content=policy_data.get("content", ""),
            type=policy_data.get("type", "rego"),
        )

    async def update_policy(self, policy_id: str, policy_data: Dict[str, Any]) -> PolicyModel:
        """Update existing attestation policy."""
        policy_data["policy_id"] = policy_id
        return await self.create_policy(policy_data)

    # Resource Management
    async def list_resources(self, repository: Optional[str] = None) -> ResourceListResponse:
        """List resources, optionally filtered by repository."""
        params = {"repository": repository} if repository else None
        response = await self._request("GET", "/api/kbs/v0/resources", params=params)
        data = response.json()
        resources = [
            ResourceModel(
                repository=item["repository_name"],
                type=item["resource_type"],
                tag=item["resource_tag"],
                content="",  # Content not returned in list
            )
            for item in data
        ]
        return ResourceListResponse(resources=resources, total=len(resources))

    async def create_resource(self, resource_data: Dict[str, Any]) -> ResourceModel:
        """Create new resource."""
        repository = resource_data["repository"]
        resource_type = resource_data["type"]
        tag = resource_data["tag"]
        content = resource_data.get("content", "")
        endpoint = f"/api/kbs/v0/resource/{repository}/{resource_type}/{tag}"

        # Send resource content in request body
        headers = self._get_auth_headers()
        headers["Content-Type"] = "application/octet-stream"

        try:
            response = await self.client.request(
                method="POST",
                url=urljoin(self.base_url, endpoint.lstrip("/")),
                content=content.encode("utf-8") if isinstance(content, str) else content,
                headers=headers,
            )
            response.raise_for_status()

            return ResourceModel(
                repository=repository, type=resource_type, tag=tag, content=content
            )
        except httpx.RequestError as e:
            logger.error("Request failed", url=endpoint, error=str(e))
            raise TrusteeClientError(f"Request failed: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error", url=endpoint, status=e.response.status_code, response=e.response.text
            )
            raise TrusteeClientError(f"HTTP {e.response.status_code}: {e.response.text}")

    # Audit Log Access
    async def get_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        operation: Optional[str] = None,
        resource: Optional[str] = None,
        audit_type: str = "attestation",
    ) -> AuditLogResponse:
        """Get audit logs with filtering."""
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }
        if operation:
            params["operation"] = operation
        if resource:
            params["resource"] = resource

        if audit_type == "resources":
            endpoint = "/api/audit/resources"
        else:
            endpoint = "/api/audit/attestation"
            
        response = await self._request("GET", endpoint, params=params)
        data = response.json()

        logs = []
        if audit_type == "resources":
            logs = [
                AuditLogEntry(
                    id=str(item.get("id", "")),
                    timestamp=item.get("timestamp", ""),
                    operation=item.get("method", "unknown"),
                    resource=f"{item.get('repository', '')}/{item.get('type', '')}:{item.get('tag', '')}",
                    status=str(item.get("status", 0)),
                    details={
                        "successful": item.get("successful", False),
                        "client_ip": item.get("client_ip", ""),
                        "session_id": item.get("session_id", ""),
                    },
                )
                for item in data
            ]
        else:
            logs = [
                AuditLogEntry(
                    id=str(item.get("id", "")),
                    timestamp=item.get("timestamp", ""),
                    operation="attestation",
                    resource=item.get("session_id", ""),
                    status=str(item.get("status", 0)),
                    details={
                        "successful": item.get("successful", False),
                        "client_ip": item.get("client_ip", ""),
                    },
                )
                for item in data
            ]
        return AuditLogResponse(logs=logs, total=len(logs), has_more=False)

    # Health Check
    async def get_health_status(self) -> HealthStatus:
        """Get system health status."""
        response = await self._request("GET", "/api/services-health")
        data = response.json()

        components_status = {}
        overall_status = "ok"

        for component_name, component_info in data.items():
            status = component_info.get("status", "unknown")
            components_status[component_name] = status
            if status.lower() not in ["ok", "not supported", "running", "healthy"]:
                overall_status = "error"

        if not components_status:
            overall_status = "unknown"

        return HealthStatus(
            status=overall_status,
            components=components_status,
            timestamp=datetime.now(),
        )

    # RVPS Operations
    async def register_reference_value(self, rvps_data: Dict[str, Any]) -> RvpsReferenceValue:
        """Register reference value in RVPS."""
        payload_data = {rvps_data.get("name", "test-binary"): [rvps_data.get("hash_value", "")]}
        payload_json = json.dumps(payload_data)
        payload_base64 = self._encode_base64(payload_json)

        message_content = {"version": "0.1.0", "type": "sample", "payload": payload_base64}

        message_data = {"message": json.dumps(message_content)}

        await self._request_with_auth("POST", "/api/rvps/register", json_data=message_data)

        return RvpsReferenceValue(
            name=rvps_data.get("name", ""),
            hash_value=rvps_data.get("hash_value", ""),
            version="0.1.0",
            type="sample",
        )

    async def query_reference_values(self, name: str) -> List[RvpsReferenceValue]:
        """Query reference values by name."""
        response = await self._request("GET", "/api/rvps/query")
        data = response.json()

        results = []
        for ref_name, values in data.items():
            if name in ref_name:
                for value in values:
                    results.append(
                        RvpsReferenceValue(
                            name=ref_name,
                            hash_value=value,
                            version="0.1.0",
                            type="sample",
                        )
                    )
        return results

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
