"""Main MCP server implementation for Trustee Gateway."""

import structlog
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, ToolsCapability

from .client import TrusteeClient
from .config import TrusteeConfig, load_config
from .tools import TrusteeTools

logger = structlog.get_logger()


class TrusteeMCPServer:
    """MCP Server for Trustee Gateway operations."""

    def __init__(self, config: TrusteeConfig):
        self.config = config
        self.server = Server("trustee-mcp-server")
        self.client = TrusteeClient(config)
        self.tools = TrusteeTools(self.client)

        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP server handlers."""

        @self.server.list_tools()
        async def handle_list_tools():
            """Handle list tools request."""
            logger.info("Listing available tools")
            return self.tools.get_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            """Handle tool execution request."""
            logger.info("Executing tool", tool=name, args=arguments)

            try:
                return await self.tools.execute_tool(name, arguments or {})
            except Exception as e:
                logger.error("Tool execution failed", tool=name, error=str(e))
                return [TextContent(type="text", text=f"Error executing tool {name}: {e}")]

    async def run(self):
        """Run the MCP server."""
        logger.info("Starting Trustee MCP Server", base_url=self.config.base_url)

        try:
            async with stdio_server() as (read_stream, write_stream):
                init_options = InitializationOptions(
                    server_name="trustee-mcp-server",
                    server_version="0.1.0",
                    capabilities=ServerCapabilities(tools=ToolsCapability()),
                )
                await self.server.run(read_stream, write_stream, init_options)
        except Exception as e:
            logger.error("Server failed to start", error=str(e))
            raise

    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up server resources")
        await self.client.close()


async def create_server() -> TrusteeMCPServer:
    """Create and configure the MCP server."""
    config = load_config()
    logger.info("Server configuration loaded", base_url=config.base_url)
    return TrusteeMCPServer(config)
