"""MCP tools for Trustee Gateway operations."""

import json
from typing import Any, Dict, List, Optional

import structlog
from mcp.types import TextContent, Tool

from .client import TrusteeClient
from .exceptions import TrusteeClientError

logger = structlog.get_logger()


class SchemaBuilder:
    """Helper class to build JSON schemas for tools."""

    @staticmethod
    def create_object_schema(
        properties: Dict[str, Dict[str, Any]], required: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create object schema with properties and required fields."""
        return {
            "type": "object",
            "properties": properties,
            "required": required or [],
        }

    @staticmethod
    def string_prop(description: str, default: Optional[str] = None) -> Dict[str, Any]:
        """Create string property schema."""
        prop = {"type": "string", "description": description}
        if default is not None:
            prop["default"] = default
        return prop

    @staticmethod
    def integer_prop(
        description: str, default: Optional[int] = None, minimum: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create integer property schema."""
        prop: Dict[str, Any] = {"type": "integer", "description": description}
        if default is not None:
            prop["default"] = default
        if minimum is not None:
            prop["minimum"] = minimum
        return prop


class TrusteeTools:
    """MCP tools for Trustee Gateway operations."""

    def __init__(self, client: TrusteeClient):
        self.client = client
        self._schema = SchemaBuilder()

    def get_tools(self) -> List[Tool]:
        """Get all available MCP tools."""
        return [
            # Policy Management Tools
            Tool(
                name="list_policies",
                description="List all policies in the KBS",
                inputSchema=self._schema.create_object_schema(
                    {
                        "random_string": self._schema.string_prop(
                            "Dummy parameter for no-parameter tools"
                        )
                    },
                    ["random_string"],
                ),
            ),
            Tool(
                name="get_policy",
                description="Get a specific policy by ID",
                inputSchema=self._schema.create_object_schema(
                    {"policy_id": self._schema.string_prop("The policy ID to retrieve")},
                    ["policy_id"],
                ),
            ),
            Tool(
                name="create_policy",
                description="Create a new policy",
                inputSchema=self._schema.create_object_schema(
                    {
                        "policy_id": self._schema.string_prop("The policy ID"),
                        "content": self._schema.string_prop("The policy content (Rego format)"),
                        "type": self._schema.string_prop("The policy type", "rego"),
                    },
                    ["policy_id", "content"],
                ),
            ),
            Tool(
                name="update_policy",
                description="Update an existing policy",
                inputSchema=self._schema.create_object_schema(
                    {
                        "policy_id": self._schema.string_prop("The policy ID to update"),
                        "content": self._schema.string_prop("The new policy content"),
                        "type": self._schema.string_prop("The policy type", "rego"),
                    },
                    ["policy_id", "content"],
                ),
            ),
            # Resource Management Tools
            Tool(
                name="list_resources",
                description="List resources in the KBS",
                inputSchema=self._schema.create_object_schema(
                    {"repository": self._schema.string_prop("Filter by repository name")}
                ),
            ),
            Tool(
                name="create_resource",
                description="Create a new resource",
                inputSchema=self._schema.create_object_schema(
                    {
                        "repository": self._schema.string_prop("The resource repository"),
                        "type": self._schema.string_prop("The resource type"),
                        "tag": self._schema.string_prop("The resource tag"),
                        "content": self._schema.string_prop("The resource content"),
                    },
                    ["repository", "type", "tag", "content"],
                ),
            ),
            # Audit and Monitoring Tools
            Tool(
                name="get_audit_logs",
                description="Query audit logs",
                inputSchema=self._schema.create_object_schema(
                    {
                        "limit": self._schema.integer_prop(
                            "Maximum number of log entries to return", 100, 1
                        ),
                        "offset": self._schema.integer_prop("Offset for pagination", 0, 0),
                        "operation": self._schema.string_prop("Filter by operation type"),
                        "resource": self._schema.string_prop("Filter by resource"),
                        "audit_type": self._schema.string_prop(
                            "Type of audit log: attestation or resources", "attestation"
                        ),
                    }
                ),
            ),
            Tool(
                name="get_health_status",
                description="Get system health status",
                inputSchema=self._schema.create_object_schema(
                    {
                        "random_string": self._schema.string_prop(
                            "Dummy parameter for no-parameter tools"
                        )
                    },
                    ["random_string"],
                ),
            ),
            # RVPS Tools
            Tool(
                name="register_reference_value",
                description="Register a reference value in RVPS",
                inputSchema=self._schema.create_object_schema(
                    {
                        "name": self._schema.string_prop("Reference value name"),
                        "hash_value": self._schema.string_prop("Hash value"),
                        "issuer": self._schema.string_prop("Issuer of the reference value"),
                    },
                    ["name", "hash_value"],
                ),
            ),
            Tool(
                name="query_reference_values",
                description="Query reference values by name",
                inputSchema=self._schema.create_object_schema(
                    {"name": self._schema.string_prop("Reference value name to query")},
                    ["name"],
                ),
            ),
        ]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute a tool and return the result."""
        try:
            handler = getattr(self, f"_handle_{name}", None)
            if handler:
                result = await handler(arguments)
                return [TextContent(type="text", text=result)]
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except TrusteeClientError as e:
            logger.error("Tool execution failed", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Error executing {name}: {e}")]
        except Exception as e:
            logger.error("Unexpected error in tool execution", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Unexpected error in {name}: {e}")]

    # Policy handlers
    async def _handle_list_policies(self, args: Dict[str, Any]) -> str:
        result = await self.client.list_policies()
        return f"Found {result.total} policies:\n" + "\n".join(
            [f"- {p.id}: {p.type}" for p in result.policies]
        )

    async def _handle_get_policy(self, args: Dict[str, Any]) -> str:
        policy = await self.client.get_policy(args["policy_id"])
        return f"Policy {policy.id}:\nType: {policy.type}\nContent:\n{policy.content}"

    async def _handle_create_policy(self, args: Dict[str, Any]) -> str:
        policy_data = {
            "policy_id": args.get("policy_id", "new-policy"),
            "content": args["content"],
            "type": args.get("type", "rego"),
        }
        policy = await self.client.create_policy(policy_data)
        return f"Created policy {policy.id} of type {policy.type}"

    async def _handle_update_policy(self, args: Dict[str, Any]) -> str:
        policy_data = {"content": args["content"], "type": args.get("type", "rego")}
        policy = await self.client.update_policy(args["policy_id"], policy_data)
        return f"Updated policy {policy.id}"

    # Resource handlers
    async def _handle_list_resources(self, args: Dict[str, Any]) -> str:
        result = await self.client.list_resources(args.get("repository"))
        return f"Found {result.total} resources:\n" + "\n".join(
            [f"- {r.repository}/{r.type}:{r.tag}" for r in result.resources]
        )

    async def _handle_create_resource(self, args: Dict[str, Any]) -> str:
        resource_data = {
            "repository": args["repository"],
            "type": args["type"],
            "tag": args["tag"],
            "content": args["content"],
        }
        resource = await self.client.create_resource(resource_data)
        return f"Created resource {resource.repository}/{resource.type}:{resource.tag}"

    # Audit handlers
    async def _handle_get_audit_logs(self, args: Dict[str, Any]) -> str:
        audit_type = args.get("audit_type", "attestation")
        result = await self.client.get_audit_logs(
            limit=args.get("limit", 100),
            offset=args.get("offset", 0),
            operation=args.get("operation"),
            resource=args.get("resource"),
            audit_type=audit_type,
        )
        
        if audit_type == "resources":
            log_text = f"Found {result.total} resource audit log entries:\n"
            for log in result.logs:
                details = log.details or {}
                log_text += f"- {log.timestamp}: {log.operation} {log.resource} (Status: {log.status}, Success: {details.get('successful', False)})\n"
        else:
            log_text = f"Found {result.total} attestation audit log entries:\n"
            for log in result.logs:
                details = log.details or {}
                log_text += f"- {log.timestamp}: {log.operation} session {log.resource} (Status: {log.status}, Success: {details.get('successful', False)})\n"
        
        return log_text

    async def _handle_get_health_status(self, args: Dict[str, Any]) -> str:
        status = await self.client.get_health_status()
        health_text = f"System Status: {status.status}\nComponents:\n"
        for component, comp_status in status.components.items():
            health_text += f"- {component}: {comp_status}\n"
        return health_text

    # RVPS handlers
    async def _handle_register_reference_value(self, args: Dict[str, Any]) -> str:
        rvps_data = {
            "name": args["name"],
            "hash_value": args["hash_value"],
            "issuer": args.get("issuer"),
        }
        ref_value = await self.client.register_reference_value(rvps_data)
        return f"Registered reference value: {ref_value.name} with hash {ref_value.hash_value}"

    async def _handle_query_reference_values(self, args: Dict[str, Any]) -> str:
        ref_values = await self.client.query_reference_values(args["name"])
        result_text = f"Found {len(ref_values)} reference values for '{args['name']}':\n"
        for rv in ref_values:
            result_text += f"- {rv.name}: {rv.hash_value} (type: {rv.type})\n"
        return result_text
