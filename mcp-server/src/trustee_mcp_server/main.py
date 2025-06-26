"""Main entry point for Trustee MCP Server."""

import argparse
import asyncio
import sys

import structlog
from dotenv import load_dotenv

from .server import create_server


def setup_logging(debug: bool = False):
    """Setup structured logging."""
    if debug:
        structlog.configure(
            processors=[
                structlog.dev.ConsoleRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
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
    parser = argparse.ArgumentParser(
        description="Trustee MCP Server - 机密计算远程证明MCP服务器"
    )
    
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="传输协议：stdio（标准输入输出）或 http（HTTP远程访问）"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="HTTP服务器监听地址（仅HTTP模式）"
    )
    
    parser.add_argument(
        "--port", 
        type=int,
        default=8000,
        help="HTTP服务器监听端口（仅HTTP模式）"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )

    args = parser.parse_args()
    
    setup_logging(debug=args.debug)
    logger = structlog.get_logger()

    # Load environment variables
    load_dotenv()

    logger.info("Initializing Trustee MCP Server")

    server = None
    try:
        server = await create_server()
        
        if args.transport == "stdio":
            logger.info("启动Trustee MCP服务器 (stdio模式)")
            await server.run_stdio()
        else:  # http
            logger.info(
                "启动Trustee MCP服务器 (HTTP模式)", 
                host=args.host, 
                port=args.port
            )
            await server.run_http(host=args.host, port=args.port)

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
