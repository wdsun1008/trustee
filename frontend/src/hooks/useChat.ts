import { useState, useEffect, useRef, useCallback } from 'react';
import { message } from 'antd';
import { ChatService, ChatMessage, ChatConfig } from '../services/ChatService';
import { MCPClient, MCPTool, MCPServer } from '../services/MCPClient';

export interface UseChatConfig {
  mcpEnabled?: boolean;
  mcpServers?: MCPServer[];
}

export interface UseChatResult {
  // 聊天状态
  messages: ChatMessage[];
  isLoading: boolean;
  isInitialized: boolean;
  
  // MCP状态
  mcpEnabled: boolean;
  mcpConnected: boolean;
  mcpTools: MCPTool[];
  mcpServersCount: number;
  
  // 配置
  chatConfig: ChatConfig | null;
  
  // 操作
  initialize: (config: ChatConfig) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  setMcpEnabled: (enabled: boolean) => void;
  addMcpServer: (serverName: string, server: MCPServer) => void;
}

export const useChat = (config?: UseChatConfig): UseChatResult => {
  // 聊天状态
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [chatConfig, setChatConfig] = useState<ChatConfig | null>(null);
  
  // MCP状态
  const [mcpEnabled, setMcpEnabled] = useState(config?.mcpEnabled ?? true);
  const [mcpConnected, setMcpConnected] = useState(false);
  const [mcpTools, setMcpTools] = useState<MCPTool[]>([]);
  const [mcpServersCount, setMcpServersCount] = useState(0);
  
  // 服务实例
  const chatServiceRef = useRef<ChatService>(new ChatService());
  const mcpClientRef = useRef<MCPClient>(new MCPClient());

  /**
   * 初始化聊天服务
   */
  const initialize = useCallback(async (config: ChatConfig) => {
    try {
      setIsLoading(true);
      
      // 初始化聊天服务
      await chatServiceRef.current.initialize(config);
      setChatConfig(config);
      setIsInitialized(true);
      
      message.success('✅ 聊天服务初始化成功');

    } catch (error) {
      console.error('❌ 初始化失败:', error);
      message.error(`初始化失败: ${error instanceof Error ? error.message : '未知错误'}`);
      setIsInitialized(false);
    } finally {
      setIsLoading(false);
    }
  }, []); 

  /**
   * 初始化MCP客户端
   */
  const initializeMCP = useCallback(async () => {
    if (!mcpEnabled) {
      setMcpConnected(false);
      setMcpTools([]);
      setMcpServersCount(0);
      // 在禁用MCP时安全断开连接
      try {
        await mcpClientRef.current.disconnect();
      } catch (error) {
        console.warn('断开MCP连接时出错:', error);
      }
      return;
    }

    try {
      console.log('🔄 初始化MCP客户端...');
      
      try {
        await mcpClientRef.current.disconnect();
        await new Promise(resolve => setTimeout(resolve, 50));
      } catch (error) {
        console.warn('断开现有MCP连接时出错:', error);
      }
      
      if (config?.mcpServers) {
        config.mcpServers.forEach((server, index) => {
          mcpClientRef.current.addServer(`server_${index}`, server);
        });
      } else {
        mcpClientRef.current.addServer('trustee', {
          name: 'trustee',
          url: '/mcp',
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      await mcpClientRef.current.connectToAllServers();
      
      const tools = mcpClientRef.current.getTools();
      const serversCount = mcpClientRef.current.getConnectedServersCount();
      
      setMcpConnected(serversCount > 0);
      setMcpTools(tools);
      setMcpServersCount(serversCount);
      
      if (serversCount > 0) {
        console.log(`✅ MCP连接成功: ${serversCount}个服务器, ${tools.length}个工具`);
        
        const health = mcpClientRef.current.getConnectionHealth();
        console.log('📊 MCP连接健康状态:', health);
      } else {
        console.warn('⚠️ 未连接到任何MCP服务器');
        const health = mcpClientRef.current.getConnectionHealth();
        console.warn('📊 MCP连接状态详情:', health);
      }
    } catch (error) {
      console.error('❌ MCP初始化失败:', error);
      setMcpConnected(false);
      setMcpTools([]);
      setMcpServersCount(0);
      
      if (error instanceof Error && !error.message.includes('Connection closed')) {
        message.error(`MCP连接失败: ${error.message}`);
      } else {
        console.warn('MCP服务器暂时不可用，将在后台重试');
      }
    }
  }, [mcpEnabled, config?.mcpServers]);

  /**
   * 发送消息
   */
  const sendMessage = useCallback(async (content: string) => {
    if (!isInitialized || !content.trim()) return;

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      let currentMessages = [...messages, userMessage];
      let assistantResponse = '';
      let toolCallsNeeded: any[] = [];

      // 如果MCP已连接，添加系统提示词并使用工具
      if (mcpEnabled && mcpConnected && mcpTools.length > 0) {
        const systemPrompt = mcpClientRef.current.generateSystemPrompt();
        const tools = mcpClientRef.current.getToolsForLLM();
        
        // 添加系统提示词到消息开头
        const messagesWithSystem: ChatMessage[] = [
          {
            id: `system_${Date.now()}`,
            role: 'system',
            content: systemPrompt,
            timestamp: new Date()
          },
          ...currentMessages
        ];

        // 发送带工具的请求
        const response = await chatServiceRef.current.sendMessageWithTools(
          messagesWithSystem,
          tools,
          'auto'
        );
        
        assistantResponse = response.message.content;
        toolCallsNeeded = response.toolCalls || [];
      } else {
        // 普通聊天模式
        const response = await chatServiceRef.current.sendMessage(currentMessages);
        assistantResponse = response.content;
      }

      // 处理工具调用
      if (toolCallsNeeded.length > 0) {
        console.log('🔧 处理工具调用:', toolCallsNeeded);
        
        try {
          // 解析并执行工具调用
          const mcpToolCalls = mcpClientRef.current.parseLLMToolCalls(toolCallsNeeded);
          const toolResults = await mcpClientRef.current.callMultipleTools(mcpToolCalls);
          const formattedResults = mcpClientRef.current.formatToolResults(toolResults);
          
          // 发送包含工具结果的请求
          const messagesWithToolResults: ChatMessage[] = [
            ...currentMessages,
            {
              id: `assistant_${Date.now()}`,
              role: 'assistant',
              content: assistantResponse,
              timestamp: new Date()
            },
            {
              id: `tool_result_${Date.now()}`,
              role: 'user',
              content: `工具执行结果：\n${formattedResults}\n\n请根据以上工具执行结果，为用户提供完整的回答。`,
              timestamp: new Date()
            }
          ];

          const finalResponse = await chatServiceRef.current.sendMessage(messagesWithToolResults);
          assistantResponse = finalResponse.content;
        } catch (toolError) {
          console.error('❌ 工具调用失败:', toolError);
          assistantResponse += `\n\n⚠️ 工具调用过程中出现错误: ${toolError instanceof Error ? toolError.message : '未知错误'}`;
        }
      }

      // 添加最终的助手回复
      const assistantMessage: ChatMessage = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: assistantResponse || '抱歉，我无法生成回复。',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error('❌ 发送消息失败:', error);
      
      const errorMessage: ChatMessage = {
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: `❌ 抱歉，出现了错误：${error instanceof Error ? error.message : '未知错误'}`,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [isInitialized, messages, mcpEnabled, mcpConnected, mcpTools]);

  /**
   * 清空消息
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    message.success('对话已清空');
  }, []);

  /**
   * 添加MCP服务器
   */
  const addMcpServer = useCallback((serverName: string, server: MCPServer) => {
    mcpClientRef.current.addServer(serverName, server);
    if (mcpEnabled) {
      // 重新初始化MCP以连接新服务器
      initializeMCP();
    }
  }, [mcpEnabled, initializeMCP]);

  /**
   * 监听MCP启用状态变化 - 添加防抖机制避免频繁调用
   */
  useEffect(() => {
    if (!isInitialized) return;
    
    // 检查是否需要重新连接（避免不必要的重连）
    const currentlyConnected = mcpClientRef.current.isConnected();
    const needsConnection = mcpEnabled && !currentlyConnected;
    const needsDisconnection = !mcpEnabled && currentlyConnected;
    
    if (!needsConnection && !needsDisconnection) {
      return;
    }
    
    // 使用setTimeout创建简单的防抖机制
    const timer = setTimeout(() => {
      console.log(`🔄 MCP状态变更: enabled=${mcpEnabled}, connected=${currentlyConnected}`);
      initializeMCP();
    }, 200);
    
    return () => clearTimeout(timer);
  }, [mcpEnabled, isInitialized, initializeMCP]);

  /**
   * 组件卸载时清理资源
   */
  useEffect(() => {
    return () => {
      mcpClientRef.current.disconnect();
    };
  }, []);

  return {
    // 聊天状态
    messages,
    isLoading,
    isInitialized,
    
    // MCP状态
    mcpEnabled,
    mcpConnected,
    mcpTools,
    mcpServersCount,
    
    // 配置
    chatConfig,
    
    // 操作
    initialize,
    sendMessage,
    clearMessages,
    setMcpEnabled,
    addMcpServer,
  };
}; 