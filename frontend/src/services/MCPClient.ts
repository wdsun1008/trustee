import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

export interface MCPServer {
  name: string;
  url: string;
  headers?: Record<string, string>;
}

export interface MCPTool {
  name: string;
  description?: string;
  inputSchema: any;
}

export interface MCPResource {
  uri: string;
  name?: string;
  description?: string;
  mimeType?: string;
}

export interface MCPToolCall {
  name: string;
  arguments: any;
}

export interface MCPToolResult {
  content: Array<{
    type: string;
    text?: string;
    [key: string]: any;
  }>;
  isError?: boolean;
}

export class MCPClient {
  private clients: Map<string, Client> = new Map();
  private transports: Map<string, StreamableHTTPClientTransport> = new Map();
  private tools: Map<string, MCPTool> = new Map();
  private resources: Map<string, MCPResource> = new Map();
  private serverConfigs: Map<string, MCPServer> = new Map();

  /**
   * 添加MCP服务器配置
   */
  addServer(serverName: string, config: MCPServer): void {
    this.serverConfigs.set(serverName, { ...config, name: serverName });
  }

  /**
   * 连接到指定的MCP服务器
   */
  async connectToServer(serverName: string): Promise<void> {
    const config = this.serverConfigs.get(serverName);
    if (!config) {
      throw new Error(`服务器配置不存在: ${serverName}`);
    }

    // 先清理可能存在的旧连接状态
    const existingClient = this.clients.get(serverName);
    const existingTransport = this.transports.get(serverName);
    
    if (existingClient || existingTransport) {
      console.log(`🔄 清理服务器 ${serverName} 的旧连接...`);
      try {
        if (existingTransport) {
          await existingTransport.close();
        }
      } catch (error) {
        console.warn(`清理旧连接时出错: ${serverName}`, error);
      }
      
      // 清理旧状态
      this.clients.delete(serverName);
      this.transports.delete(serverName);
      
      // 清理相关工具和资源
      for (const [key] of this.tools.entries()) {
        if (key.startsWith(`${serverName}:`)) {
          this.tools.delete(key);
        }
      }
      for (const [key] of this.resources.entries()) {
        if (key.startsWith(`${serverName}:`)) {
          this.resources.delete(key);
        }
      }
    }

    try {
      console.log(`🔄 连接到MCP服务器: ${serverName}`);

      // 创建客户端和传输
      const client = new Client({
        name: "trustee-mcp-client",
        version: "1.0.0",
      }, {
        capabilities: {}
      });

      const transport = new StreamableHTTPClientTransport(
        new URL(config.url, window.location.origin)
      );

      // 连接
      await client.connect(transport);

      // 存储连接
      this.clients.set(serverName, client);
      this.transports.set(serverName, transport);

      // 获取工具和资源
      await this.loadServerCapabilities(serverName, client);

      console.log(`✅ 成功连接到MCP服务器: ${serverName}`);
    } catch (error) {
      console.error(`❌ 连接MCP服务器失败: ${serverName}`, error);
      
      // 连接失败时清理部分状态，避免留下不完整的连接
      this.clients.delete(serverName);
      this.transports.delete(serverName);
      
      throw error;
    }
  }

  /**
   * 加载服务器能力（工具和资源）
   */
  private async loadServerCapabilities(serverName: string, client: Client): Promise<void> {
    try {
      // 加载工具
      const toolsResponse = await client.listTools();
      for (const tool of toolsResponse.tools) {
        const toolKey = `${serverName}:${tool.name}`;
        this.tools.set(toolKey, {
          name: tool.name,
          description: tool.description,
          inputSchema: tool.inputSchema
        });
      }

      // 加载资源
      try {
        const resourcesResponse = await client.listResources();
        for (const resource of resourcesResponse.resources) {
          const resourceKey = `${serverName}:${resource.uri}`;
          this.resources.set(resourceKey, {
            uri: resource.uri,
            name: resource.name,
            description: resource.description,
            mimeType: resource.mimeType
          });
        }
      } catch (error) {
        // 如果服务器不支持资源，忽略错误
        console.warn(`服务器 ${serverName} 不支持资源功能`);
      }

      console.log(`📊 从 ${serverName} 加载了 ${toolsResponse.tools.length} 个工具`);
    } catch (error) {
      console.error(`加载服务器能力失败: ${serverName}`, error);
      throw error;
    }
  }

  /**
   * 连接到所有配置的服务器
   */
  async connectToAllServers(): Promise<void> {
    const promises = Array.from(this.serverConfigs.keys()).map(serverName =>
      this.connectToServer(serverName).catch(error => {
        console.error(`连接服务器失败: ${serverName}`, error);
        return null;
      })
    );

    await Promise.all(promises);
  }

  /**
   * 调用工具
   */
  async callTool(toolName: string, parameters: any = {}): Promise<MCPToolResult> {
    // 查找工具所属的服务器
    let serverName: string | null = null;
    let actualToolName = toolName;

    for (const [toolKey, tool] of this.tools.entries()) {
      if (tool.name === toolName || toolKey.endsWith(`:${toolName}`)) {
        [serverName] = toolKey.split(':');
        actualToolName = tool.name;
        break;
      }
    }

    if (!serverName) {
      throw new Error(`工具不存在: ${toolName}`);
    }

    const client = this.clients.get(serverName);
    if (!client) {
      throw new Error(`服务器未连接: ${serverName}`);
    }

    try {
      console.log(`🔧 调用工具: ${toolName} (服务器: ${serverName})`);
      
      const result = await client.callTool({
        name: actualToolName,
        arguments: parameters
      });

      console.log(`✅ 工具调用成功: ${toolName}`);
      
      // 确保返回符合 MCPToolResult 接口的数据
      const content = Array.isArray(result.content) 
        ? result.content 
        : [{ type: 'text', text: JSON.stringify(result) }];
      
      return {
        content,
        isError: false
      };
    } catch (error) {
      console.error(`❌ 工具调用失败: ${toolName}`, error);
      throw error;
    }
  }

  /**
   * 批量调用工具
   */
  async callMultipleTools(toolCalls: MCPToolCall[]): Promise<MCPToolResult[]> {
    const results: MCPToolResult[] = [];

    for (const toolCall of toolCalls) {
      try {
        const result = await this.callTool(toolCall.name, toolCall.arguments);
        results.push(result);
      } catch (error) {
        results.push({
          content: [{
            type: 'text',
            text: `错误: ${error instanceof Error ? error.message : '未知错误'}`
          }],
          isError: true
        });
      }
    }

    return results;
  }

  /**
   * 获取所有可用工具
   */
  getTools(): MCPTool[] {
    return Array.from(this.tools.values());
  }

  /**
   * 获取工具的LLM格式定义
   */
  getToolsForLLM(): any[] {
    return Array.from(this.tools.values()).map(tool => ({
      type: 'function',
      function: {
        name: tool.name,
        description: tool.description || '',
        parameters: tool.inputSchema || { type: 'object', properties: {} }
      }
    }));
  }

  /**
   * 获取所有可用资源
   */
  getResources(): MCPResource[] {
    return Array.from(this.resources.values());
  }

  /**
   * 读取资源内容
   */
  async readResource(uri: string): Promise<any> {
    // 查找资源所属的服务器
    let serverName: string | null = null;

    for (const [resourceKey] of this.resources.entries()) {
      if (resourceKey.endsWith(uri) || resourceKey.includes(uri)) {
        [serverName] = resourceKey.split(':');
        break;
      }
    }

    if (!serverName) {
      throw new Error(`资源不存在: ${uri}`);
    }

    const client = this.clients.get(serverName);
    if (!client) {
      throw new Error(`服务器未连接: ${serverName}`);
    }

    try {
      const result = await client.readResource({ uri });
      return result;
    } catch (error) {
      console.error(`读取资源失败: ${uri}`, error);
      throw error;
    }
  }

  /**
   * 格式化工具调用结果
   */
  formatToolResults(results: MCPToolResult[]): string {
    return results.map((result, index) => {
      if (result.isError) {
        return `❌ 工具调用 ${index + 1} 失败: ${result.content[0]?.text || '未知错误'}`;
      }

      const content = result.content
        .map(item => item.text || JSON.stringify(item))
        .join('\n');

      return `✅ 工具调用 ${index + 1} 结果:\n${content}`;
    }).join('\n\n');
  }

  /**
   * 解析LLM工具调用
   */
  parseLLMToolCalls(toolCalls: any[]): MCPToolCall[] {
    return toolCalls.map(call => ({
      name: call.function?.name || call.name,
      arguments: typeof call.function?.arguments === 'string'
        ? JSON.parse(call.function.arguments)
        : call.function?.arguments || call.arguments || {}
    }));
  }

  /**
   * 生成系统提示词
   */
  generateSystemPrompt(): string {
    const tools = this.getTools();
    const resources = this.getResources();

    let prompt = `# Trustee AI 助手

你是 Trustee 机密计算管理平台的专业 AI 助手，具备深度理解机密计算、远程证明和可信执行环境(TEE)的能力。

## 关于 Trustee 平台

### 🏗️ 系统架构
Trustee 是一个完整的机密计算可信基础设施，采用 RATS (Remote ATtestation procedureS) 架构模型，包含以下核心组件：

**🔑 Key Broker Service (KBS)**
- 角色：Relying Party（依赖方）
- 功能：协助远程证明和机密数据下发
- 职责：验证TEE身份后，安全下发密钥、配置等机密资源

**🛡️ Attestation Service (AS)**  
- 角色：Verifier（验证方）
- 功能：验证来自TEE的证明证据
- 支持：多种TEE平台（Intel TDX、AMD SEV、ARM CCA等）

**📊 Reference Value Provider Service (RVPS)**
- 功能：管理用于验证TEE证据的参考值
- 作用：提供可信的测量基线和完整性校验值
- 对应：RATS架构中的Endorser/Reference Value Provider

**🌐 Trustee Gateway**
- 功能：统一的API网关和管理入口
- 提供：RESTful API接口和Web管理界面
- 集成：所有Trustee组件的统一访问点

### 🔄 工作流程
1. **客户端请求**：TEE环境中的应用向KBS请求机密资源
2. **证明生成**：TEE生成包含硬件和软件测量值的证明证据  
3. **证明验证**：AS验证证明证据的真实性和完整性
4. **参考值校验**：RVPS提供参考值进行测量值比对
5. **策略评估**：根据预定义策略决定是否信任该TEE
6. **资源下发**：验证通过后，KBS安全下发所请求的机密资源

## MCP 系统集成

当前系统通过 Model Context Protocol (MCP) 集成了 Trustee Gateway，提供以下实时管理能力：

`;

    if (tools.length > 0) {
      prompt += '### 🔧 可用工具\n\n';
      
      // 按功能分类展示工具
      const policyTools = tools.filter(t => t.name.includes('policy') || t.name.includes('policies'));
      const resourceTools = tools.filter(t => t.name.includes('resource'));
      const auditTools = tools.filter(t => t.name.includes('audit') || t.name.includes('logs'));
      const rvpsTools = tools.filter(t => t.name.includes('reference') || t.name.includes('rvps'));
      const healthTools = tools.filter(t => t.name.includes('health'));
      const otherTools = tools.filter(t => 
        !policyTools.includes(t) && !resourceTools.includes(t) && 
        !auditTools.includes(t) && !rvpsTools.includes(t) && !healthTools.includes(t)
      );

      if (policyTools.length > 0) {
        prompt += '**📋 证明策略管理**\n';
        policyTools.forEach(tool => {
          prompt += `- \`${tool.name}\`: ${tool.description || '证明策略操作'}\n`;
        });
        prompt += '\n';
      }

      if (resourceTools.length > 0) {
        prompt += '**📦 机密资源管理**\n';
        resourceTools.forEach(tool => {
          prompt += `- \`${tool.name}\`: ${tool.description || '机密资源操作'}\n`;
        });
        prompt += '\n';
      }

      if (auditTools.length > 0) {
        prompt += '**📊 审计与监控**\n';
        auditTools.forEach(tool => {
          prompt += `- \`${tool.name}\`: ${tool.description || '审计日志查询'}\n`;
        });
        prompt += '\n';
      }

      if (rvpsTools.length > 0) {
        prompt += '**🔍 参考值服务 (RVPS)**\n';
        rvpsTools.forEach(tool => {
          prompt += `- \`${tool.name}\`: ${tool.description || '参考值管理'}\n`;
        });
        prompt += '\n';
      }

      if (healthTools.length > 0) {
        prompt += '**⚡ 系统监控**\n';
        healthTools.forEach(tool => {
          prompt += `- \`${tool.name}\`: ${tool.description || '系统状态检查'}\n`;
        });
        prompt += '\n';
      }

      if (otherTools.length > 0) {
        prompt += '**🛠️ 其他工具**\n';
        otherTools.forEach(tool => {
          prompt += `- \`${tool.name}\`: ${tool.description || '系统管理功能'}\n`;
        });
        prompt += '\n';
      }
    }

    if (resources.length > 0) {
      prompt += '### 📂 可用资源\n';
      resources.forEach(resource => {
        prompt += `- ${resource.uri}: ${resource.description || resource.name || '系统资源'}\n`;
      });
      prompt += '\n';
    }

    prompt += `## 🎯 服务能力

### 专业领域
- **机密计算**：TEE技术、硬件安全、内存加密、安全启动
- **远程证明**：RATS协议、证明证据验证、信任链建立
- **密钥管理**：密钥生成、分发、轮换、撤销
- **安全策略**：Rego策略语言、访问控制、合规管理
- **系统运维**：服务监控、日志分析、故障诊断

### 典型场景
1. **策略配置**：帮助制定和优化远程证明策略
2. **资源管理**：协助管理机密密钥和配置文件
3. **安全审计**：分析系统访问日志和操作记录
4. **故障诊断**：检查系统健康状态，定位问题根因
5. **合规检查**：验证系统配置是否符合安全标准

## 💡 使用指南

### 基本原则
1. **安全优先**：始终考虑操作的安全影响
2. **最小权限**：仅执行用户明确授权的操作
3. **详细记录**：重要操作前后应检查审计日志
4. **状态验证**：操作完成后验证系统状态

### 最佳实践
- 在修改策略前，先查看现有策略列表
- 创建资源前，确认仓库和类型符合规范
- 定期检查系统健康状态
- 关注审计日志中的异常操作

### 常用工作流
1. **健康检查** → **策略审查** → **资源清单** → **审计分析**
2. **问题诊断**：健康状态 → 审计日志 → 具体组件检查
3. **策略管理**：查看现有 → 创建/更新 → 验证生效

## 🤝 交互方式

我会根据你的需求智能选择合适的工具，提供准确的技术支持。你可以：

- 询问 Trustee 系统的架构和工作原理
- 请求检查系统状态或诊断问题
- 获取策略、资源管理的专业建议
- 了解机密计算和远程证明的技术细节
- 获得运维操作的最佳实践指导

现在，我已准备好为你提供专业的 Trustee 机密计算管理计算平台支持服务！`;

    return prompt;
  }

  /**
   * 检查连接状态
   */
  isConnected(): boolean {
    return this.clients.size > 0;
  }

  /**
   * 获取连接的服务器数量
   */
  getConnectedServersCount(): number {
    return this.clients.size;
  }

  /**
   * 获取连接健康状态
   */
  getConnectionHealth(): { 
    totalServers: number;
    connectedServers: number;
    totalTools: number;
    totalResources: number;
    serverDetails: Array<{
      name: string;
      connected: boolean;
      toolCount: number;
      resourceCount: number;
    }>;
  } {
    const serverDetails = Array.from(this.serverConfigs.keys()).map(serverName => {
      const connected = this.clients.has(serverName);
      const toolCount = Array.from(this.tools.keys()).filter(key => key.startsWith(`${serverName}:`)).length;
      const resourceCount = Array.from(this.resources.keys()).filter(key => key.startsWith(`${serverName}:`)).length;
      
      return {
        name: serverName,
        connected,
        toolCount,
        resourceCount
      };
    });

    return {
      totalServers: this.serverConfigs.size,
      connectedServers: this.clients.size,
      totalTools: this.tools.size,
      totalResources: this.resources.size,
      serverDetails
    };
  }

  /**
   * 断开所有连接
   */
  async disconnect(): Promise<void> {
    console.log('🔄 断开所有MCP连接...');

    // 先清理状态，避免在断开过程中发生错误导致状态不一致
    const clientsToDisconnect = Array.from(this.clients.entries());
    const transportsToClose = Array.from(this.transports.entries());
    
    // 立即清理状态，避免其他操作使用已失效的连接
    this.clients.clear();
    this.transports.clear();
    this.tools.clear();
    this.resources.clear();
    this.serverConfigs.clear();

    // 异步断开连接，即使出错也不影响状态清理
    for (const [serverName, transport] of transportsToClose) {
      try {
        await transport.close();
        console.log(`✅ 已断开服务器: ${serverName}`);
      } catch (error) {
        // 断开连接时的错误不应该中断流程，只记录警告
        console.warn(`断开服务器连接时出错: ${serverName}`, error);
        // 不再抛出错误，避免中断调用方的流程
      }
    }

    console.log('✅ 所有MCP连接已断开');
  }
} 