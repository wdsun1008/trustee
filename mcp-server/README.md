# Trustee MCP Server

基于FastMCP的Trustee Gateway MCP服务器 - 为机密计算远程证明操作提供自然语言接口，支持远程访问。

## 概述

Trustee MCP Server是一个基于Model Context Protocol (MCP)的实现，为Trustee Gateway API提供自然语言接口。它使大语言模型(LLM)能够通过自然语言交互来管理机密计算资源、证明策略、审计日志和参考值。

## 核心功能

### 🔐 策略管理
- **查看策略**: 列出所有远程证明策略
- **策略详情**: 获取特定策略详细信息
- **创建策略**: 注册新的证明策略
- **更新策略**: 修改现有策略

### 📦 资源管理  
- **资源清单**: 查看所有机密资源
- **创建资源**: 注册新的机密资源

### 📊 审计与监控
- **审计日志**: 查询系统操作日志
- **健康状态**: 检查系统组件状态

### 🔍 参考值服务 (RVPS)
- **注册参考值**: 添加可信测量值
- **查询参考值**: 检索参考值信息

## 安装

```bash
# 安装包
pip install -e .

# 或从PyPI安装 (可用时)
pip install trustee-mcp-server
```

## 配置

服务器使用环境变量或配置文件：

```bash
# 必需: Trustee Gateway URL
export TRUSTEE_BASE_URL="https://your-trustee-gateway.com"

# 可选: 认证配置
export KBS_AUTH_PRIVATE_KEY_PATH="/path/to/private.key"

# 可选: 超时设置
export TRUSTEE_TIMEOUT=30
```

## 使用方法

### 🖥️ stdio模式 (本地)

```bash
# 启动stdio服务器 (默认模式)
trustee-mcp-server

# 或明确指定stdio模式
trustee-mcp-server --transport stdio
```

### 🌐 HTTP模式 (远程访问)

```bash
# 启动HTTP服务器
trustee-mcp-server --transport http --host 0.0.0.0 --port 8000

# 启动调试模式
trustee-mcp-server --transport http --port 8000 --debug
```

### 📱 前端集成

HTTP模式允许前端应用远程访问MCP功能：

```typescript
// 前端可以通过HTTP连接到MCP服务器
const mcpClient = new MCPClient("http://localhost:8000");
await mcpClient.connect();

// 调用工具
const policies = await mcpClient.callTool("list_policies", {});
```

## 工具参考

### 策略工具

#### `list_policies`
列出系统中的所有证明策略。

#### `get_policy` 
- **policy_id** (必需): 策略标识符

#### `create_policy`
- **policy_id** (必需): 唯一策略标识符  
- **content** (必需): Rego语言的策略内容
- **type** (可选): 策略类型，默认为"rego"

#### `update_policy`
- **policy_id** (必需): 要更新的策略标识符
- **content** (必需): 新的策略内容
- **type** (可选): 策略类型，默认为"rego"

### 资源工具

#### `list_resources`
- **repository** (可选): 按仓库名称过滤

#### `create_resource`
- **repository** (必需): 资源仓库名称
- **type** (必需): 资源类型 (如 "key", "cert", "config")
- **tag** (必需): 用于版本控制的资源标签
- **content** (必需): 资源内容

### 审计工具

#### `get_audit_logs`
- **limit** (可选): 最大条目数，默认100
- **offset** (可选): 分页偏移量，默认0
- **operation** (可选): 按操作类型过滤
- **resource** (可选): 按资源标识符过滤
- **audit_type** (可选): "attestation"或"resources"，默认"attestation"

#### `get_health_status`
无需参数。

### RVPS工具

#### `register_reference_value`
- **name** (必需): 参考值名称
- **hash_value** (必需): 哈希值或测量值
- **issuer** (可选): 参考值发布者

#### `query_reference_values`  
- **name** (必需): 要查询的参考值名称

## 开发

### 设置开发环境

```bash
# 克隆仓库
git clone <repository-url>
cd mcp-server

# 以开发模式安装
pip install -e .
```

### 运行测试

```bash
# 运行单元测试
python -m pytest

# 运行MCP工具测试  
python test_mcp_tools.py

# 使用特定Trustee Gateway测试
TRUSTEE_BASE_URL="https://your-gateway.com" python test_mcp_tools.py
```
