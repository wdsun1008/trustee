# Trustee MCP Server: AI 驱动的机密计算管理引擎

`Trustee MCP Server` 是一个基于 [Trustee Gateway](https://github.com/inclavare-containers/trustee/tree/main/trustee-gateway) API 实现的 **模型上下文协议 (Model Context Protocol, MCP)** 服务器。它作为连接大语言模型 (LLM) 与 Trustee的桥梁，旨在将传统的图形化或命令行管理模式，革新为以自然语言为核心的、智能化的交互方式。

在 AI 时代，我们相信通过大语言模型赋能，可以极大地降低机密计算技术的应用门槛，提升安全运维的效率和智能化水平。`mcp-server` 正是这一理念的实践。

## 核心价值

与直接使用 Trustee Web UI 或命令行相比，`mcp-server` 带来了显著的价值：

*   **降低使用门槛**：安全运维人员无需深入学习复杂的机密计算知识或 Rego 策略语法，即可通过自然语言完成查询、策略管理等任务。
*   **提升运维效率**：对于经验丰富的管理员，可以通过自然语言快速执行命令，甚至将多个步骤的复杂任务自动化，从而显著提升工作效率。
*   **智能化与自动化**：这是项目的长期愿景。未来，通过集成的 Agent 能力，实现自动化的安全态势感知、策略生成和安全事件响应，将安全运维带入 "AI-Powered" 的新阶段。

## 目标用户

*   **经验丰富的 Trustee 管理员**：希望通过自然语言交互和自动化能力提升运维效率。
*   **安全运维领域的新用户**：希望降低学习曲线，能更快地熟悉和使用 Trustee 平台管理机密计算环境。

## 工作原理

`mcp-server` 设计为一个标准的 MCP 服务器，通常作为子进程被上层的大语言模型应用（LLM Orchestrator）调用。其核心工作流如下：

```mermaid
graph LR
    A[LLM Orchestrator] -- stdio (JSON-RPC) --> B(Trustee MCP Server);
    B -- HTTP/S (REST API) --> C(Trustee Gateway);
    C -- gRPC/HTTP --> D[后端服务 (KBS, RVPS, etc.)];
```

1.  **启动与发现**：上层应用启动 `mcp-server`，并通过 MCP 协议查询其可用的 "工具" 列表。
2.  **指令解析与调用**：上层应用将用户的自然语言指令（例如："创建一个允许所有操作的策略"）解析并匹配到 `mcp-server` 提供的最合适的工具（例如：`create_policy`）。
3.  **执行与反馈**：`mcp-server` 接收到工具调用请求后，会与 `Trustee Gateway` 进行认证，并调用其相应的 REST API 来执行具体操作。
4.  **结果返回**：`mcp-server` 将 `Trustee Gateway` 的返回结果格式化为自然语言文本，通过 MCP 协议回传给上层应用，最终呈现给用户。

## 功能特性

`mcp-server` 将 Trustee Gateway 的核心管理功能封装为一系列标准化的 LLM 工具：

*   **策略管理 (Policy Management)**
    *   `list_policies`: 列出所有可用的证明策略。
    *   `get_policy`: 获取指定 ID 的策略详情。
    *   `create_policy`: 创建一个新的证明策略。
    *   `update_policy`: 更新一个已有的证明策略。
*   **资源管理 (Resource Management)**
    *   `list_resources`: 列出所有已注册的资源。
    *   `create_resource`: 注册一个新的资源。
*   **参考值服务 (RVPS)**
    *   `query_reference_values`: 查询参考值。
    *   `register_reference_value`: 注册一个新的参考值。
*   **审计与监控 (Audit & Monitoring)**
    *   `get_audit_logs`: 查询审计日志。
    *   `get_health_status`: 检查系统健康状态。

## 使用场景示例

#### 场景一：日常审计与风险分析

> **运维人员**: "显示过去24小时内所有和策略更新相关的审计日志，并分析其中的安全风险。"

`mcp-server` 将调用 `get_audit_logs` 工具，筛选出相关的日志，并将结果返回给 LLM。LLM 进一步对日志内容进行分析，识别出异常操作（如在非工作时间修改关键策略），并向用户报告潜在风险。

#### 场景二：基于安全需求的策略生成与部署

> **管理员**: "根据公司'仅允许来自生产环境的 TDX 机密虚拟机进行证明'的安全原则，为我生成一条 Rego 策略，并部署为 `prod-tdx-only`。"

LLM 首先根据高层级的安全原则生成具体的 Rego 策略代码，然后调用 `create_policy` 工具，将生成的策略内容和指定的 `policy_id` 一起发送给 Trustee，完成部署。

#### 场景三：自动化应用上线

> **DevOps工程师**: "我们正在部署一个新的应用'app-xyz'，请为它创建所需的资源，并关联默认的安全策略。"

这是一个更复杂的复合场景。未来，`mcp-server` 可以提供一个更高阶的工具来处理此类请求。该工具会依次调用 `create_resource` 来注册应用资源，并调用 `update_policy`（或相关接口）来确保新应用受到正确的安全策略保护，将多步操作自动化。

## 安装与配置

### 安装

```bash
# 从源码安装
pip install -e .
```

### 配置

服务通过环境变量或 `.env` 文件进行配置。

1.  **获取 KBS 认证私钥**：
    部署 Trustee 时会生成 ED25519 算法的 PEM 格式私钥文件。请妥善保存此文件，`mcp-server` 需要用它来生成访问 KBS 管理接口所需的 JWT 令牌。

2.  **设置环境变量**：
    ```bash
    # Trustee Gateway 的访问地址
    export TRUSTEE_GATEWAY_URL=http://localhost:8081
    # KBS 认证私钥文件的路径
    export TRUSTEE_KBS_AUTH_PRIVATE_KEY_PATH=/path/to/kbs-auth-private.key
    # (可选) 请求超时时间，默认30秒
    export TRUSTEE_TIMEOUT=30
    # (可选) 请求失败重试次数，默认3次
    export TRUSTEE_MAX_RETRIES=3
    ```
