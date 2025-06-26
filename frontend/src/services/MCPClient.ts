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

    if (tools.length === 0 && resources.length === 0) {
      return '你是一个智能助手。';
    }

    let prompt = '你是一个智能助手，可以访问以下能力：\n\n';

    if (tools.length > 0) {
      prompt += '可用工具:\n';
      tools.forEach(tool => {
        prompt += `- ${tool.name}: ${tool.description || '无描述'}\n`;
      });
      prompt += '\n';
    }

    if (resources.length > 0) {
      prompt += '可用资源:\n';
      resources.forEach(resource => {
        prompt += `- ${resource.uri}: ${resource.description || resource.name || '无描述'}\n`;
      });
      prompt += '\n';
    }

    prompt += '使用指南:\n';
    prompt += '1. 根据用户需求选择合适的工具或资源\n';
    prompt += '2. 可以调用多个工具获取全面信息\n';
    prompt += '3. 处理错误时给出清晰说明\n';
    prompt += '4. 基于工具结果提供准确的回答\n\n';
    prompt += '请智能分析用户意图，选择合适的工具完成任务。';

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