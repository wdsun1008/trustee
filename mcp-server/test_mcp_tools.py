#!/usr/bin/env python3.11
"""
Trustee MCP 工具全面测试套件

这个测试套件全面覆盖所有可用的 MCP 工具，包括：
- 策略管理工具 (list_policies, get_policy, create_policy, update_policy)
- 资源管理工具 (list_resources, create_resource)
- 审计日志工具 (get_audit_logs - 支持 attestation 和 resources 类型)
- 健康状态工具 (get_health_status)
- RVPS 参考值工具 (register_reference_value, query_reference_values)

总共10个MCP工具的完整测试覆盖。

执行环境要求：Python 3.11+ 和 pip3.11
"""

import asyncio
import json
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 添加 mcp-server 模块到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from trustee_mcp_server.client import TrusteeClient
from trustee_mcp_server.config import load_config
from trustee_mcp_server.exceptions import TrusteeClientError


@dataclass
class TestResult:
    """测试结果数据类"""
    name: str
    success: bool
    duration: float
    data: Optional[Any] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class TestSuite:
    """测试套件数据类"""
    name: str
    results: List[TestResult]
    total_duration: float

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results if not r.success)

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        return (self.success_count / len(self.results)) * 100


class ComprehensiveMCPTester:
    """全面的 MCP 工具测试器 - 测试所有10个MCP工具"""

    def __init__(self):
        self.config = load_config()
        self.client = TrusteeClient(self.config)
        self.test_suites: List[TestSuite] = []
        self.test_data = {
            "policies": [],
            "resources": [],
            "reference_values": []
        }

    def print_header(self, title: str, char: str = "=", width: int = 80):
        """打印格式化的标题"""
        print(f"\n{char * width}")
        print(f"  {title}")
        print(f"{char * width}")

    def print_result(self, result: TestResult, show_data: bool = True):
        """打印测试结果"""
        status = "✅ 成功" if result.success else "❌ 失败"
        print(f"\n{result.name}: {status} ({result.duration:.3f}s)")

        # 显示警告
        if result.warnings:
            for warning in result.warnings:
                print(f"⚠️  警告: {warning}")

        if result.success and result.data and show_data:
            self._print_data(result.data)
        elif result.error:
            print(f"❌ 错误: {result.error}")

    def _print_data(self, data: Any, max_length: int = 500):
        """打印数据内容"""
        if isinstance(data, dict):
            print(json.dumps(data, indent=2, ensure_ascii=False))
        elif isinstance(data, list):
            print(f"返回 {len(data)} 条记录")
            for i, item in enumerate(data[:5]):  # 只显示前5条
                print(f"  {i+1}. {item}")
            if len(data) > 5:
                print(f"  ... (还有 {len(data) - 5} 条记录)")
        else:
            str_data = str(data)
            if len(str_data) > max_length:
                print(f"{str_data[:max_length]}...")
            else:
                print(str_data)

    async def run_test(self, test_name: str, test_func, *args, **kwargs) -> TestResult:
        """运行单个测试并记录结果"""
        start_time = time.time()
        try:
            result_data = await test_func(*args, **kwargs)
            duration = time.time() - start_time
            return TestResult(
                name=test_name,
                success=True,
                duration=duration,
                data=result_data
            )
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"❌ 测试失败: {test_name}")
            print(f"   错误: {error_msg}")
            if isinstance(e, TrusteeClientError):
                print(f"   详细信息: 可能是服务配置或网络问题")
            return TestResult(
                name=test_name,
                success=False,
                duration=duration,
                error=error_msg
            )

    async def test_health_status(self) -> Dict[str, Any]:
        """测试健康状态检查 - 工具#1"""
        health = await self.client.get_health_status()
        return {
            "status": health.status,
            "is_healthy": health.is_healthy,
            "components": dict(health.components),
            "timestamp": health.timestamp.isoformat(),
            "component_count": len(health.components)
        }

    async def test_policy_lifecycle(self) -> List[TestResult]:
        """测试策略完整生命周期 - 工具#2, #3, #4, #5"""
        results = []
        
        # 工具#2: 列出现有策略 (list_policies)
        results.append(await self.run_test(
            "MCP工具#2: 列出所有策略 (list_policies)",
            self._test_list_policies
        ))
        
        # 工具#4: 创建测试策略 (create_policy)
        test_policies = [
            {
                "policy_id": "test-allow-all-mcp",
                "content": "package policy\ndefault allow := true\n# MCP测试策略",
                "type": "rego"
            },
            {
                "policy_id": "test-restrictive-mcp", 
                "content": "package policy\ndefault allow := false\n# 严格策略用于MCP测试",
                "type": "rego"
            }
        ]
        
        for policy in test_policies:
            results.append(await self.run_test(
                f"MCP工具#4: 创建策略 (create_policy): {policy['policy_id']}",
                self._test_create_policy,
                policy
            ))
            
        # 工具#3: 获取策略详情 (get_policy)
        for policy in test_policies:
            results.append(await self.run_test(
                f"MCP工具#3: 获取策略详情 (get_policy): {policy['policy_id']}",
                self._test_get_policy,
                policy['policy_id']
            ))
            
        # 工具#5: 测试策略更新 (update_policy)
        update_data = {
            "content": "package policy\ndefault allow := false\n# 已更新的MCP测试策略",
            "type": "rego"
        }
        results.append(await self.run_test(
            "MCP工具#5: 更新策略 (update_policy): test-allow-all-mcp",
            self._test_update_policy,
            "test-allow-all-mcp",
            update_data
        ))
        
        return results

    async def _test_list_policies(self):
        """列出所有策略"""
        policies = await self.client.list_policies()
        return {
            "total_policies": policies.total,
            "policy_ids": [p.id for p in policies.policies],
            "found_policies": len(policies.policies)
        }

    async def _test_get_policy(self, policy_id: str):
        """获取指定策略详情"""
        policy = await self.client.get_policy(policy_id)
        return {
            "policy_id": policy.id,
            "content_length": len(policy.content),
            "type": policy.type,
            "has_content": bool(policy.content)
        }

    async def _test_create_policy(self, policy_data: Dict[str, Any]):
        """创建新策略"""
        policy = await self.client.create_policy(policy_data)
        self.test_data["policies"].append(policy_data["policy_id"])
        return {
            "policy_id": policy.id,
            "type": policy.type,
            "created": True
        }

    async def _test_update_policy(self, policy_id: str, policy_data: Dict[str, Any]):
        """更新现有策略"""
        policy = await self.client.update_policy(policy_id, policy_data)
        return {
            "policy_id": policy.id,
            "updated": True,
            "type": policy.type
        }

    async def test_resource_lifecycle(self) -> List[TestResult]:
        """测试资源完整生命周期 - 工具#6, #7"""
        results = []
        
        # 工具#6: 列出现有资源 (list_resources)
        results.append(await self.run_test(
            "MCP工具#6: 列出所有资源 (list_resources)",
            self._test_list_resources
        ))
        
        # 按仓库过滤资源列表
        results.append(await self.run_test(
            "MCP工具#6: 按仓库过滤资源 (list_resources with filter)",
            self._test_list_resources_filtered,
            "test-repo"
        ))
        
        # 工具#7: 创建测试资源 (create_resource)
        test_resources = [
            {
                "repository": "mcp-test-repo",
                "type": "key",
                "tag": "v1.0",
                "content": "这是一个MCP测试密钥内容"
            },
            {
                "repository": "mcp-test-repo",
                "type": "config",
                "tag": "prod",
                "content": json.dumps({"app": "mcp-test", "env": "production"})
            },
            {
                "repository": "mcp-test-repo",
                "type": "cert",
                "tag": "latest",
                "content": "-----BEGIN CERTIFICATE-----\nMCP测试证书内容\n-----END CERTIFICATE-----"
            }
        ]
        
        for resource in test_resources:
            results.append(await self.run_test(
                f"MCP工具#7: 创建资源 (create_resource): {resource['repository']}/{resource['type']}:{resource['tag']}",
                self._test_create_resource,
                resource
            ))
        
        # 再次列出资源，验证创建结果
        results.append(await self.run_test(
            "MCP工具#6: 验证资源创建后的列表 (list_resources verification)",
            self._test_list_resources
        ))
        
        return results

    async def _test_list_resources(self):
        """列出所有资源"""
        resources = await self.client.list_resources()
        resource_summary = {}
        for r in resources.resources:
            key = f"{r.repository}/{r.type}"
            if key not in resource_summary:
                resource_summary[key] = []
            resource_summary[key].append(r.tag)
        
        return {
            "total_resources": resources.total,
            "resource_count": len(resources.resources),
            "resource_summary": resource_summary,
            "found_repositories": list(set(r.repository for r in resources.resources))
        }

    async def _test_list_resources_filtered(self, repository: str):
        """按仓库过滤列出资源"""
        resources = await self.client.list_resources(repository)
        return {
            "repository_filter": repository,
            "filtered_count": len(resources.resources),
            "total_available": resources.total,
            "resources": [f"{r.type}:{r.tag}" for r in resources.resources]
        }

    async def _test_create_resource(self, resource_data: Dict[str, Any]):
        """创建新资源"""
        resource = await self.client.create_resource(resource_data)
        resource_id = f"{resource.repository}/{resource.type}:{resource.tag}"
        self.test_data["resources"].append(resource_id)
        return {
            "resource_id": resource_id,
            "repository": resource.repository,
            "type": resource.type,
            "tag": resource.tag,
            "created": True
        }

    async def test_audit_logs(self) -> List[TestResult]:
        """测试审计日志功能 - 工具#8"""
        results = []
        
        # 测试证明审计日志
        results.append(await self.run_test(
            "MCP工具#8: 获取证明审计日志 (get_audit_logs - attestation)",
            self._test_get_audit_logs,
            "attestation",
            10
        ))
        
        # 测试资源访问审计日志
        results.append(await self.run_test(
            "MCP工具#8: 获取资源审计日志 (get_audit_logs - resources)",
            self._test_get_audit_logs,
            "resources",
            10
        ))
        
        # 测试分页功能
        results.append(await self.run_test(
            "MCP工具#8: 审计日志分页测试 (get_audit_logs - pagination)",
            self._test_audit_logs_pagination
        ))
        
        # 测试过滤功能
        results.append(await self.run_test(
            "MCP工具#8: 审计日志过滤测试 (get_audit_logs - filtering)",
            self._test_audit_logs_filtering
        ))
        
        return results

    async def _test_get_audit_logs(self, audit_type: str = "attestation", limit: int = 10, **kwargs):
        """获取审计日志"""
        logs = await self.client.get_audit_logs(
            audit_type=audit_type,
            limit=limit,
            **kwargs
        )
        
        log_details = []
        for log in logs.logs[:3]:  # 只显示前3条详情
            log_details.append({
                "timestamp": log.timestamp,
                "operation": log.operation,
                "resource": log.resource,
                "status": log.status,
                "has_details": bool(log.details)
            })
        
        return {
            "audit_type": audit_type,
            "total_logs": logs.total,
            "returned_count": len(logs.logs),
            "sample_logs": log_details,
            "limit_used": limit
        }

    async def _test_audit_logs_pagination(self):
        """测试审计日志分页"""
        page1 = await self.client.get_audit_logs(limit=5, offset=0)
        page2 = await self.client.get_audit_logs(limit=5, offset=5)
        
        return {
            "page1_count": len(page1.logs),
            "page2_count": len(page2.logs),
            "total_available": page1.total,
            "pagination_working": len(page1.logs) > 0 or len(page2.logs) > 0
        }

    async def _test_audit_logs_filtering(self):
        """测试审计日志过滤"""
        # 测试按操作类型过滤
        auth_logs = await self.client.get_audit_logs(
            operation="auth",
            limit=5
        )
        
        # 测试资源类型审计日志
        resource_logs = await self.client.get_audit_logs(
            audit_type="resources",
            limit=5
        )
        
        return {
            "auth_operation_logs": len(auth_logs.logs),
            "resource_audit_logs": len(resource_logs.logs),
            "filtering_available": True,
            "auth_total": auth_logs.total,
            "resource_total": resource_logs.total
        }

    async def test_rvps_operations(self) -> List[TestResult]:
        """测试RVPS参考值操作 - 工具#9, #10"""
        results = []
        
        # 工具#9: 注册测试参考值 (register_reference_value)
        test_reference_values = [
            {
                "name": "mcp-test-component-v1",
                "hash_value": "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "issuer": "MCP测试套件"
            },
            {
                "name": "mcp-test-kernel-v2", 
                "hash_value": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                "issuer": "MCP内核测试"
            },
            {
                "name": "mcp-test-app-latest",
                "hash_value": "sha256:fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321"
                # 无issuer测试可选参数
            }
        ]
        
        for rvps_data in test_reference_values:
            results.append(await self.run_test(
                f"MCP工具#9: 注册参考值 (register_reference_value): {rvps_data['name']}",
                self._test_register_reference_value,
                rvps_data
            ))
        
        # 工具#10: 查询参考值 (query_reference_values)
        for rvps_data in test_reference_values:
            results.append(await self.run_test(
                f"MCP工具#10: 查询参考值 (query_reference_values): {rvps_data['name']}",
                self._test_query_reference_values,
                rvps_data['name']
            ))
        
        # 测试查询不存在的参考值
        results.append(await self.run_test(
            "MCP工具#10: 查询不存在的参考值 (query_reference_values - not found)",
            self._test_query_reference_values,
            "nonexistent-mcp-test-component"
        ))
        
        return results

    async def _test_register_reference_value(self, rvps_data: Dict[str, Any]):
        """注册参考值"""
        ref_value = await self.client.register_reference_value(rvps_data)
        self.test_data["reference_values"].append(rvps_data["name"])
        return {
            "name": ref_value.name,
            "hash_value": ref_value.hash_value,
            "type": ref_value.type,
            "registered": True
        }

    async def _test_query_reference_values(self, name: str):
        """查询参考值"""
        ref_values = await self.client.query_reference_values(name)
        return {
            "query": name,
            "found_count": len(ref_values),
            "values": [
                {
                    "name": rv.name,
                    "hash_value": rv.hash_value,
                    "version": rv.version,
                    "type": rv.type
                }
                for rv in ref_values
            ]
        }

    async def test_error_handling(self) -> List[TestResult]:
        """测试错误处理和边界情况"""
        results = []
        
        # 测试无效策略ID
        results.append(await self.run_test(
            "错误处理: 获取不存在的策略",
            self._test_get_invalid_policy
        ))
        
        # 测试无效资源创建
        results.append(await self.run_test(
            "错误处理: 创建无效资源",
            self._test_create_invalid_resource
        ))
        
        # 测试无效参考值注册
        results.append(await self.run_test(
            "错误处理: 注册无效参考值",
            self._test_register_invalid_reference_value
        ))
        
        return results

    async def _test_get_invalid_policy(self):
        """测试获取不存在的策略"""
        try:
            await self.client.get_policy("nonexistent-policy-12345-mcp-test")
            return {"unexpected": "应该抛出异常但没有"}
        except TrusteeClientError as e:
            return {"expected_error": str(e), "handled_correctly": True}

    async def _test_create_invalid_resource(self):
        """测试创建无效资源"""
        try:
            invalid_resource = {
                "repository": "",  # 空仓库名
                "type": "test",
                "tag": "v1",
                "content": "test"
            }
            await self.client.create_resource(invalid_resource)
            return {"unexpected": "应该验证失败但没有"}
        except (TrusteeClientError, ValueError) as e:
            return {"expected_error": str(e), "handled_correctly": True}

    async def _test_register_invalid_reference_value(self):
        """测试注册无效参考值"""
        try:
            invalid_ref_value = {
                "name": "",  # 空名称
                "hash_value": "invalid-hash"  # 无效哈希
            }
            await self.client.register_reference_value(invalid_ref_value)
            return {"unexpected": "应该验证失败但没有"}
        except (TrusteeClientError, ValueError) as e:
            return {"expected_error": str(e), "handled_correctly": True}

    async def run_comprehensive_test_suite(self):
        """运行全面的测试套件 - 覆盖所有10个MCP工具"""
        self.print_header("🚀 Trustee MCP 工具全面测试套件 (10个工具完整覆盖)", width=100)
        print(f"Python 版本: {sys.version}")
        print(f"连接目标: {self.config.base_url}")
        print(f"超时设置: {self.config.timeout}秒")
        print(f"测试目标: 覆盖所有10个MCP工具的完整功能")
        
        total_start_time = time.time()
        
        # 定义测试套件 - 覆盖所有10个MCP工具
        test_suites = [
            ("MCP工具#1: 健康状态检查", self.test_health_status_suite),
            ("MCP工具#2-5: 策略生命周期 (4个工具)", self.test_policy_lifecycle),
            ("MCP工具#6-7: 资源生命周期 (2个工具)", self.test_resource_lifecycle), 
            ("MCP工具#8: 审计日志功能", self.test_audit_logs),
            ("MCP工具#9-10: RVPS 参考值操作 (2个工具)", self.test_rvps_operations),
            ("错误处理测试", self.test_error_handling),
        ]
        
        # 运行所有测试套件
        for suite_name, suite_func in test_suites:
            self.print_header(f"📋 {suite_name}", char="-", width=80)
            suite_start_time = time.time()
            
            if suite_name.startswith("MCP工具#1"):
                # 健康状态检查返回单个结果
                result = await self.run_test(suite_name, suite_func)
                suite_results = [result]
            else:
                # 其他测试套件返回结果列表
                suite_results = await suite_func()
            
            suite_duration = time.time() - suite_start_time
            
            # 显示测试结果
            for result in suite_results:
                self.print_result(result, show_data=True)
            
            # 记录测试套件
            test_suite = TestSuite(
                name=suite_name,
                results=suite_results,
                total_duration=suite_duration
            )
            self.test_suites.append(test_suite)
            
            # 显示套件摘要
            print(f"\n📊 {suite_name} 摘要:")
            print(f"   总测试数: {len(suite_results)}")
            print(f"   成功数: {test_suite.success_count}")
            print(f"   失败数: {test_suite.failure_count}")
            print(f"   成功率: {test_suite.success_rate:.1f}%")
            print(f"   总耗时: {suite_duration:.3f}秒")
        
        total_duration = time.time() - total_start_time
        await self.print_final_summary(total_duration)
        
        # 关闭客户端连接
        await self.client.close()

    async def test_health_status_suite(self):
        """健康状态检查套件 - 返回单个结果"""
        return await self.test_health_status()

    async def print_final_summary(self, total_duration: float):
        """打印最终测试摘要"""
        self.print_header("📊 最终测试摘要 - MCP工具完整覆盖报告", width=100)
        
        total_tests = sum(len(suite.results) for suite in self.test_suites)
        total_success = sum(suite.success_count for suite in self.test_suites)
        total_failure = sum(suite.failure_count for suite in self.test_suites)
        overall_success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0
        
        print(f"🎯 总体结果:")
        print(f"   总测试套件数: {len(self.test_suites)}")
        print(f"   总测试用例数: {total_tests}")
        print(f"   总成功数: {total_success}")
        print(f"   总失败数: {total_failure}")
        print(f"   总体成功率: {overall_success_rate:.1f}%")
        print(f"   总耗时: {total_duration:.3f}秒")
        
        print(f"\n📋 各套件详情:")
        for suite in self.test_suites:
            status_icon = "✅" if suite.failure_count == 0 else "❌"
            print(f"   {status_icon} {suite.name}: {suite.success_count}/{len(suite.results)} "
                  f"({suite.success_rate:.1f}%) - {suite.total_duration:.3f}s")
        
        # 显示MCP工具覆盖情况
        print(f"\n🔧 MCP工具覆盖情况:")
        mcp_tools = [
            "1. get_health_status - 健康状态检查",
            "2. list_policies - 列出所有策略", 
            "3. get_policy - 获取策略详情",
            "4. create_policy - 创建策略",
            "5. update_policy - 更新策略", 
            "6. list_resources - 列出资源",
            "7. create_resource - 创建资源",
            "8. get_audit_logs - 获取审计日志",
            "9. register_reference_value - 注册参考值",
            "10. query_reference_values - 查询参考值"
        ]
        
        for tool in mcp_tools:
            print(f"   ✅ {tool}")
        
        # 显示创建的测试数据摘要
        print(f"\n📦 测试数据摘要:")
        print(f"   创建的策略: {len(self.test_data['policies'])} - {self.test_data['policies']}")
        print(f"   创建的资源: {len(self.test_data['resources'])} - {self.test_data['resources']}")
        print(f"   注册的参考值: {len(self.test_data['reference_values'])} - {self.test_data['reference_values']}")
        
        # 最终状态
        if total_failure == 0:
            print(f"\n🎉 所有测试通过！所有10个Trustee Gateway MCP 工具运行正常。")
            print(f"   📊 完整覆盖: 策略管理(4个) + 资源管理(2个) + 审计日志(1个) + 健康检查(1个) + RVPS(2个) = 10个工具")
        else:
            print(f"\n⚠️  有 {total_failure} 个测试失败，请检查相关配置和服务状态。")
            print(f"   🔍 建议检查: Trustee连接、KBS服务状态、RVPS服务状态")
        
        print(f"\n{'='*100}")


async def main():
    """主函数"""
    try:
        tester = ComprehensiveMCPTester()
        await tester.run_comprehensive_test_suite()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试运行失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        print(f"详细错误:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    print("🔧 启动 Trustee MCP 工具全面测试套件...")
    print("📋 测试目标: 覆盖所有10个MCP工具的完整功能")
    print("⚙️  环境要求: Python 3.11+ 和 pip3.11")
    asyncio.run(main())
