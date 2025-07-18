"""FastMCP-based Trustee server implementation."""

from typing import Optional

import structlog
from fastmcp import FastMCP, Context

from .client import TrusteeClient
from .config import TrusteeConfig, load_config
from .exceptions import TrusteeClientError

logger = structlog.get_logger()


class TrusteeMCPServer:
    """FastMCP-based Trustee MCP server."""

    def __init__(self, config: TrusteeConfig):
        self.config = config
        self.client = TrusteeClient(config)
        
        # Create FastMCP instance
        self.mcp = FastMCP(
            name="trustee",
            version="0.1.0"
        )
        
        # Register all tools
        self._register_tools()

    def _register_tools(self):
        """Register all Trustee tools with FastMCP."""
        
        # Policy Management Tools
        @self.mcp.tool
        async def list_policies(ctx: Context) -> str:
            """查看所有证明策略 - 列出KBS中管理的远程证明策略。
            
            这些策略是机密计算安全的核心，它们定义了哪些TEE环境被信任以及什么条件下可以获取机密资源。
            在RATS模型中，这些策略控制着Relying Party（KBS）如何验证来自TEE的证明证据。
            使用场景：安全审计、策略梳理、合规检查。
            """
            await ctx.info("正在获取证明策略列表...")
            try:
                result = await self.client.list_policies()
                return f"Found {result.total} policies:\n" + "\n".join(
                    [f"- {p.id}: {p.type}" for p in result.policies]
                )
            except TrusteeClientError as e:
                await ctx.error(f"获取策略列表失败: {e}")
                raise

        @self.mcp.tool
        async def get_policy(policy_id: str, ctx: Context) -> str:
            """获取特定证明策略详情 - 查看指定ID的证明策略完整内容。
            
            策略通常用Rego语言编写，定义了TEE证明验证的具体规则，如允许的测量值、TCB状态要求等。
            这对理解当前安全配置、调试证明失败问题、策略审查等场景非常重要。
            
            Args:
                policy_id: 要查询的策略ID标识符
            """
            await ctx.info(f"正在获取策略详情: {policy_id}")
            try:
                policy = await self.client.get_policy(policy_id)
                return f"Policy {policy.id}:\nType: {policy.type}\nContent:\n{policy.content}"
            except TrusteeClientError as e:
                await ctx.error(f"获取策略详情失败: {e}")
                raise

        @self.mcp.tool
        async def create_policy(
            policy_id: str, 
            content: str, 
            ctx: Context,
            type: str = "rego"
        ) -> str:
            """创建新的证明策略 - 在KBS中注册新的远程证明验证策略。
            
            策略内容使用Rego语言编写，定义TEE证明的验证逻辑，如检查平台身份、测量值、签名等。
            新策略创建后会立即生效，影响后续的证明请求处理。
            这是实施新安全要求、支持新TEE平台、调整安全策略的关键操作。
            
            Args:
                policy_id: 策略的唯一标识符，建议使用描述性命名
                content: 策略内容，使用Rego语言编写的验证规则
                type: 策略类型，当前支持rego格式
            """
            await ctx.info(f"正在创建策略: {policy_id}")
            try:
                policy_data = {
                    "policy_id": policy_id,
                    "content": content,
                    "type": type,
                }
                policy = await self.client.create_policy(policy_data)
                await ctx.info(f"策略创建成功: {policy_id}")
                return f"Created policy {policy.id} of type {policy.type}"
            except TrusteeClientError as e:
                await ctx.error(f"创建策略失败: {e}")
                raise

        @self.mcp.tool
        async def update_policy(
            policy_id: str, 
            content: str, 
            ctx: Context,
            type: str = "rego"
        ) -> str:
            """更新现有证明策略 - 修改已存在的证明策略内容。
            
            这是安全运维中的关键操作，用于适应安全要求变化、修复策略漏洞、优化验证逻辑。
            更新会立即生效，影响所有后续的证明请求。建议在更新前做好备份和测试。
            
            Args:
                policy_id: 要更新的策略ID
                content: 新的策略内容，将完全替换原有内容
                type: 策略类型
            """
            await ctx.info(f"正在更新策略: {policy_id}")
            try:
                policy_data = {"content": content, "type": type}
                policy = await self.client.update_policy(policy_id, policy_data)
                await ctx.info(f"策略更新成功: {policy_id}")
                return f"Updated policy {policy.id}"
            except TrusteeClientError as e:
                await ctx.error(f"更新策略失败: {e}")
                raise

        # Resource Management Tools
        @self.mcp.tool
        async def list_resources(ctx: Context, repository: Optional[str] = None) -> str:
            """查看机密资源清单 - 列出KBS中存储的所有受保护资源。
            
            这些资源是机密计算的核心价值，包括密钥、证书、配置文件等敏感数据，
            只有通过远程证明的可信TEE环境才能访问。可按仓库名称过滤查看。
            使用场景：资源盘点、访问权限审查、资源管理。
            
            Args:
                repository: 可选：按仓库名称过滤资源列表
            """
            await ctx.info("正在获取机密资源列表...")
            try:
                result = await self.client.list_resources(repository)
                return f"Found {result.total} resources:\n" + "\n".join(
                    [f"- {r.repository}/{r.type}:{r.tag}" for r in result.resources]
                )
            except TrusteeClientError as e:
                await ctx.error(f"获取资源列表失败: {e}")
                raise

        @self.mcp.tool
        async def create_resource(
            repository: str,
            type: str,
            tag: str,
            content: str,
            ctx: Context
        ) -> str:
            """注册新的机密资源 - 向KBS添加需要保护的敏感资源。
            
            资源会被安全存储，只有通过远程证明验证的可信TEE环境才能获取。
            这是部署新应用、分发密钥材料、保护敏感配置的关键步骤。
            每个资源通过repository/type/tag的格式进行标识。
            
            Args:
                repository: 资源仓库名称，用于组织管理相关资源
                type: 资源类型，如key、cert、config等
                tag: 资源标签，用于版本控制或环境区分
                content: 资源的实际内容，将被安全存储
            """
            await ctx.info(f"正在创建资源: {repository}/{type}:{tag}")
            try:
                resource_data = {
                    "repository": repository,
                    "type": type,
                    "tag": tag,
                    "content": content,
                }
                resource = await self.client.create_resource(resource_data)
                await ctx.info(f"资源创建成功: {repository}/{type}:{tag}")
                return f"Created resource {resource.repository}/{resource.type}:{resource.tag}"
            except TrusteeClientError as e:
                await ctx.error(f"创建资源失败: {e}")
                raise

        # Audit and Monitoring Tools
        @self.mcp.tool
        async def get_audit_logs(
            ctx: Context,
            limit: int = 100,
            offset: int = 0,
            operation: Optional[str] = None,
            resource: Optional[str] = None,
            audit_type: str = "attestation"
        ) -> str:
            """查询安全审计日志 - 获取Trustee系统的操作审计记录。
            
            用于安全监控、合规审查、事件调查。支持查询证明记录（attestation）和资源访问记录（resources）两类日志。
            证明记录追踪TEE的证明请求和验证结果；资源记录追踪机密资源的访问情况。
            这对安全运维、合规报告、异常检测非常重要。
            
            Args:
                limit: 返回日志条目的最大数量，用于分页查询
                offset: 分页偏移量，用于获取后续页面的日志
                operation: 可选：按操作类型过滤，如auth、attest、get_resource等
                resource: 可选：按资源标识过滤，查看特定资源的访问记录
                audit_type: 审计日志类型：attestation（证明记录）或resources（资源访问记录）
            """
            await ctx.info(f"正在获取审计日志 ({audit_type})...")
            try:
                result = await self.client.get_audit_logs(
                    limit=limit,
                    offset=offset,
                    operation=operation,
                    resource=resource,
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
            except TrusteeClientError as e:
                await ctx.error(f"获取审计日志失败: {e}")
                raise

        @self.mcp.tool
        async def get_health_status(ctx: Context) -> str:
            """检查系统健康状态 - 获取Trustee各组件的运行状态。
            
            包括Gateway、KBS、AS、RVPS等核心服务。这是运维监控的基础工具，
            用于快速诊断系统问题、确保服务可用性、进行健康检查。
            在生产环境中，建议定期检查以确保机密计算平台的稳定运行。
            """
            await ctx.info("正在检查系统健康状态...")
            try:
                status = await self.client.get_health_status()
                health_text = f"System Status: {status.status}\nComponents:\n"
                for component, comp_status in status.components.items():
                    health_text += f"- {component}: {comp_status}\n"
                return health_text
            except TrusteeClientError as e:
                await ctx.error(f"获取健康状态失败: {e}")
                raise

        # RVPS Tools
        @self.mcp.tool
        async def register_reference_value(
            name: str,
            hash_value: str,
            ctx: Context,
            issuer: Optional[str] = None
        ) -> str:
            """注册参考值 - 向RVPS添加用于证明验证的参考值（可信测量值）。
            
            参考值是远程证明的基础，它们定义了可信软件的期望测量值，
            用于验证TEE中运行的软件是否为预期版本。这通常在软件发布流程中完成，
            将软件构建的测量值注册为可信参考。是建立软件供应链信任、实现安全引导验证的关键步骤。
            
            Args:
                name: 参考值名称，通常对应软件组件或版本标识
                hash_value: 哈希值，软件的测量值或签名摘要
                issuer: 可选：参考值的发布者或来源标识
            """
            await ctx.info(f"正在注册参考值: {name}")
            try:
                rvps_data = {
                    "name": name,
                    "hash_value": hash_value,
                    "issuer": issuer,
                }
                ref_value = await self.client.register_reference_value(rvps_data)
                await ctx.info(f"参考值注册成功: {name}")
                return f"Registered reference value: {ref_value.name} with hash {ref_value.hash_value}"
            except TrusteeClientError as e:
                await ctx.error(f"注册参考值失败: {e}")
                raise

        @self.mcp.tool
        async def query_reference_values(name: str, ctx: Context) -> str:
            """查询参考值 - 从RVPS获取指定名称的参考值信息。
            
            用于验证当前注册的可信测量值、调试证明验证问题、确认软件版本的信任状态。
            在证明过程中，AS会查询这些参考值来验证TEE提供的测量值是否匹配可信软件的期望值。
            
            Args:
                name: 要查询的参考值名称
            """
            await ctx.info(f"正在查询参考值: {name}")
            try:
                ref_values = await self.client.query_reference_values(name)
                result_text = f"Found {len(ref_values)} reference values for '{name}':\n"
                for rv in ref_values:
                    result_text += f"- {rv.name}: {rv.hash_value} (type: {rv.type})\n"
                return result_text
            except TrusteeClientError as e:
                await ctx.error(f"查询参考值失败: {e}")
                raise

    async def run_stdio(self):
        """Run server with stdio transport (backward compatibility)."""
        logger.info("Starting Trustee MCP Server with stdio transport")
        try:
            # Use the specific stdio async method
            await self.mcp.run_stdio_async()
        except Exception as e:
            logger.error("Server failed to start", error=str(e))
            await self.cleanup()
            raise

    async def run_http(self, host: str = "0.0.0.0", port: int = 8000, transport: str = "sse"):
        """Run server with HTTP transport for remote access.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            transport: Transport type ('sse' or 'streamable-http')
        """
        logger.info("Starting Trustee MCP Server with HTTP transport", 
                    host=host, port=port, transport=transport)
        try:
            # Use the specific http async method with transport configuration
            # FastMCP will use SSE transport when transport="sse" is specified
            await self.mcp.run_http_async(host=host, port=port, transport=transport)
        except Exception as e:
            logger.error("Server failed to start", error=str(e))
            await self.cleanup()
            raise

    # Legacy method for backward compatibility
    async def run(self):
        """Run the MCP server with stdio transport (legacy)."""
        await self.run_stdio()

    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up server resources")
        await self.client.close()


async def create_server() -> TrusteeMCPServer:
    """Create and configure the MCP server."""
    config = load_config()
    logger.info("Server configuration loaded")
    return TrusteeMCPServer(config)
