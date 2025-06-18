"""Main entry point for Trustee MCP Server."""

import asyncio
import sys

import structlog
from dotenv import load_dotenv

from .server import create_server


def setup_logging():
    """Setup structured logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


async def main():
    """Main async entry point."""
    setup_logging()
    logger = structlog.get_logger()

    # Load environment variables
    load_dotenv()

    logger.info("Initializing Trustee MCP Server")

    server = None
    try:
        server = await create_server()
        await server.run()

    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down gracefully")
    except Exception as e:
        logger.error("Server error", error=str(e), exc_info=True)
        sys.exit(1)
    finally:
        if server:
            await server.cleanup()
            logger.info("Server shutdown complete")


def cli_main():
    """CLI entry point for setuptools."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli_main()
