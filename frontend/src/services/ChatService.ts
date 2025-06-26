export interface ChatMessage {
  id: string;
  role: 'system' | 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ChatConfig {
  apiKey: string;
  model: string;
  maxTokens?: number;
  temperature?: number;
  provider: 'dashscope' | 'openai' | 'custom';
  baseURL?: string;
}

export interface ChatResponse {
  message: ChatMessage;
  toolCalls?: any[];
}

export interface ToolCall {
  type: 'function';
  function: {
    name: string;
    arguments: string;
  };
}

export class ChatService {
  private config: ChatConfig | null = null;
  private apiEndpoint = '';

  /**
   * 初始化聊天服务
   */
  async initialize(config: ChatConfig): Promise<void> {
    this.config = config;
    
    // 根据提供商设置API端点
    switch (config.provider) {
      case 'dashscope':
        // 使用代理路径，避免CORS问题
        this.apiEndpoint = '/proxy/dashscope/api/v1/services/aigc/text-generation/generation';
        break;
      case 'openai':
        // 使用代理路径，避免CORS问题
        this.apiEndpoint = config.baseURL?.startsWith('http') 
          ? '/proxy/openai/v1/chat/completions'
          : (config.baseURL || '/proxy/openai/v1/chat/completions');
        break;
      case 'custom':
        if (!config.baseURL) {
          throw new Error('自定义提供商需要指定baseURL');
        }
        this.apiEndpoint = config.baseURL.endsWith('/chat/completions') 
          ? config.baseURL 
          : `${config.baseURL}/chat/completions`;
        break;
      default:
        throw new Error(`不支持的提供商: ${config.provider}`);
    }

    console.log(`✅ 聊天服务初始化成功: ${config.provider} - ${this.apiEndpoint}`);
  }

  /**
   * 发送消息（不带工具）
   */
  async sendMessage(messages: ChatMessage[]): Promise<ChatMessage> {
    if (!this.config) {
      throw new Error('聊天服务未初始化');
    }

    const response = await this.makeAPIRequest(messages);
    
    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: response.content,
      timestamp: new Date()
    };
  }

  /**
   * 发送消息（带工具支持）
   */
  async sendMessageWithTools(
    messages: ChatMessage[], 
    tools: any[], 
    toolChoice: 'auto' | 'none' | string = 'auto'
  ): Promise<ChatResponse> {
    if (!this.config) {
      throw new Error('聊天服务未初始化');
    }

    const response = await this.makeAPIRequest(messages, tools, toolChoice);
    
    const assistantMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'assistant',
      content: response.content || '',
      timestamp: new Date()
    };

    return {
      message: assistantMessage,
      toolCalls: response.toolCalls
    };
  }

  /**
   * 统一的API请求方法
   */
  private async makeAPIRequest(
    messages: ChatMessage[], 
    tools?: any[], 
    toolChoice?: 'auto' | 'none' | string
  ): Promise<{ content: string; toolCalls?: any[] }> {
    if (!this.config) {
      throw new Error('聊天服务未配置');
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };

    let requestBody: any;

    // 根据提供商构建请求
    if (this.config.provider === 'dashscope') {
      headers['Authorization'] = `Bearer ${this.config.apiKey}`;
      
      requestBody = {
        model: this.config.model,
        input: {
          messages: messages.map(msg => ({
            role: msg.role,
            content: msg.content
          }))
        },
        parameters: {
          max_tokens: this.config.maxTokens || 4000,
          temperature: this.config.temperature ?? 0.7,
          result_format: 'message',
          enable_thinking: false
        }
      };

      // 通义千问的工具调用格式
      if (tools && tools.length > 0) {
        requestBody.parameters.tools = tools;
        if (toolChoice && toolChoice !== 'none') {
          requestBody.parameters.tool_choice = toolChoice;
        }
      }
    } else {
      // OpenAI 兼容格式
      headers['Authorization'] = `Bearer ${this.config.apiKey}`;
      
      requestBody = {
        model: this.config.model,
        messages: messages.map(msg => ({
          role: msg.role,
          content: msg.content
        })),
        max_tokens: this.config.maxTokens || 4000,
        temperature: this.config.temperature ?? 0.7
      };

      if (tools && tools.length > 0) {
        requestBody.tools = tools;
        if (toolChoice && toolChoice !== 'none') {
          requestBody.tool_choice = toolChoice;
        }
      }
    }

    try {
      console.log(`🔄 发送API请求: ${this.config.provider}`);
      
      const response = await fetch(this.apiEndpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API请求失败: ${response.status} ${response.statusText}\n${errorText}`);
      }

      const data = await response.json();
      
      return this.parseAPIResponse(data);
    } catch (error) {
      console.error('❌ API请求失败:', error);
      throw error;
    }
  }

  /**
   * 解析API响应
   */
  private parseAPIResponse(data: any): { content: string; toolCalls?: any[] } {
    if (!this.config) {
      throw new Error('聊天服务未配置');
    }

    try {
      if (this.config.provider === 'dashscope') {
        // 通义千问响应格式
        if (data.output?.choices?.[0]?.message) {
          const message = data.output.choices[0].message;
          return {
            content: message.content || '',
            toolCalls: message.tool_calls
          };
        } else {
          throw new Error('无效的API响应格式');
        }
      } else {
        // OpenAI 兼容格式
        if (data.choices?.[0]?.message) {
          const message = data.choices[0].message;
          return {
            content: message.content || '',
            toolCalls: message.tool_calls
          };
        } else {
          throw new Error('无效的API响应格式');
        }
      }
    } catch (error) {
      console.error('解析API响应失败:', error);
      throw new Error(`解析响应失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  }

  /**
   * 检查服务是否已初始化
   */
  isInitialized(): boolean {
    return this.config !== null;
  }

  /**
   * 获取当前配置
   */
  getConfig(): ChatConfig | null {
    return this.config;
  }
}

// 导出单例实例
export const chatService = new ChatService(); 