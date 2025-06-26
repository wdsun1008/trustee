import React, { useState, useRef, useEffect } from 'react';
import { 
  Card, Input, Button, List, Typography, Avatar, Space, Spin, 
  Select, Form, Modal, Switch, Alert, Tooltip, Tag, Divider, message 
} from 'antd';
import { 
  SendOutlined, RobotOutlined, UserOutlined, SettingOutlined, 
  DeleteOutlined, ApiOutlined, ExperimentOutlined, ThunderboltOutlined 
} from '@ant-design/icons';
import { useChat } from '../hooks/useChat';
import { ChatConfig } from '../services/ChatService';

const { TextArea } = Input;
const { Text, Title } = Typography;
const { Option } = Select;

const ChatPage: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const [settingsVisible, setSettingsVisible] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [lastMcpConnected, setLastMcpConnected] = useState(false);

  const {
    messages,
    isLoading,
    isInitialized,
    mcpEnabled,
    mcpConnected,
    mcpTools,
    mcpServersCount,
    chatConfig,
    initialize,
    sendMessage,
    clearMessages,
    setMcpEnabled,
  } = useChat({
    mcpEnabled: true,
    mcpServers: [
      {
        name: 'trustee',
        url: '/mcp',
        headers: { 'Content-Type': 'application/json' }
      }
    ]
  });

  // 监听MCP连接状态变化，只在真正连接成功时显示一次提示
  useEffect(() => {
    if (mcpConnected && !lastMcpConnected && mcpServersCount > 0) {
      message.success(`✅ MCP系统集成已启用: ${mcpServersCount}个服务器, ${mcpTools.length}个工具`);
    }
    setLastMcpConnected(mcpConnected);
  }, [mcpConnected, mcpServersCount, mcpTools.length, lastMcpConnected]);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 发送消息处理
  const handleSend = async () => {
    if (!inputValue.trim() || !isInitialized || isLoading) return;

    const message = inputValue.trim();
    setInputValue('');
    await sendMessage(message);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  // 保存设置
  const handleSaveSettings = async (values: any) => {
    const newConfig: ChatConfig = {
      apiKey: values.apiKey,
      model: values.model || 'qwen3-32b',
      maxTokens: values.maxTokens || 4000,
      temperature: values.temperature ?? 0.7,
      provider: values.provider,
      baseURL: values.baseURL
    };

    await initialize(newConfig);
    setSettingsVisible(false);
  };

  // 获取状态标签
  const getStatusTags = () => {
    const tags = [];
    
    if (isInitialized) {
      tags.push(<Tag key="chat" color="green">聊天就绪</Tag>);
    } else {
      tags.push(<Tag key="chat" color="red">未配置</Tag>);
    }
    
    if (mcpEnabled) {
      const mcpColor = mcpConnected ? 'blue' : 'orange';
      let mcpText = mcpConnected ? 'MCP已连接' : 'MCP未连接';
      
      if (mcpConnected && mcpServersCount > 0) {
        mcpText += ` (${mcpServersCount}服务器, ${mcpTools.length}工具)`;
      }
      
      tags.push(<Tag key="mcp" color={mcpColor}>{mcpText}</Tag>);
    }
    
    return tags;
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Card 
        title={
          <Space>
            <RobotOutlined />
            <span>Trustee AI 助手</span>
            <Space size={4}>
              {getStatusTags()}
            </Space>
            <Divider type="vertical" />
            <Tooltip title="设置">
              <Button 
                type="text" 
                icon={<SettingOutlined />} 
                onClick={() => setSettingsVisible(true)}
              />
            </Tooltip>
            <Tooltip title="清空对话">
              <Button 
                type="text" 
                icon={<DeleteOutlined />} 
                onClick={clearMessages}
                disabled={messages.length === 0}
              />
            </Tooltip>
          </Space>
        }
        style={{ 
          height: '100%', 
          display: 'flex', 
          flexDirection: 'column' 
        }}
        styles={{ 
          body: { 
            flex: 1, 
            display: 'flex', 
            flexDirection: 'column',
            padding: '16px'
          }
        }}
      >
        {!isInitialized && (
          <Alert
            message="聊天服务未初始化"
            description={
              <Space direction="vertical" size={4}>
                <span>请点击设置按钮配置 API 信息以开始聊天</span>
                <Button 
                  type="primary" 
                  size="small" 
                  icon={<SettingOutlined />}
                  onClick={() => setSettingsVisible(true)}
                >
                  立即配置
                </Button>
              </Space>
            }
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 消息列表区域 */}
        <div style={{ 
          flex: 1, 
          overflow: 'auto', 
          marginBottom: 16,
          border: '1px solid #f0f0f0',
          borderRadius: 6,
          padding: 16,
          backgroundColor: '#fafafa'
        }}>
          {messages.length === 0 ? (
            <div style={{ 
              textAlign: 'center', 
              color: '#999', 
              marginTop: 50,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 16
            }}>
              <Space direction="vertical" align="center" size={16}>
                <RobotOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                <Title level={4} type="secondary">与 Trustee AI 助手开始对话</Title>
                <Space wrap>
                  <Tag icon={<ThunderboltOutlined />} color="blue">智能回答</Tag>
                  <Tag icon={<ApiOutlined />} color="green">系统集成</Tag>
                  <Tag icon={<ExperimentOutlined />} color="purple">专业支持</Tag>
                </Space>
                <Text type="secondary" style={{ textAlign: 'center', maxWidth: 400 }}>
                  我是 Trustee 可信计算平台的 AI 助手，可以帮助您管理策略配置、资源管理、系统监控等功能。
                  {mcpConnected && ` 当前已连接 ${mcpServersCount} 个 MCP 服务器，可提供 ${mcpTools.length} 个工具的实时数据支持。`}
                </Text>
              </Space>
            </div>
          ) : (
            <List
              dataSource={messages}
              renderItem={(item) => (
                <List.Item style={{ border: 'none', padding: '8px 0' }}>
                  <List.Item.Meta
                    avatar={
                      <Avatar 
                        icon={item.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                        style={{ 
                          backgroundColor: item.role === 'user' ? '#1890ff' : '#52c41a'
                        }}
                      />
                    }
                    title={
                      <Space>
                        <span>{item.role === 'user' ? '用户' : 'AI助手'}</span>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {item.timestamp.toLocaleTimeString()}
                        </Text>
                      </Space>
                    }
                    description={
                      <div style={{ 
                        whiteSpace: 'pre-wrap', 
                        wordBreak: 'break-word',
                        marginTop: 8,
                        lineHeight: 1.6
                      }}>
                        {item.content}
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          )}
          
          {isLoading && (
            <div style={{ textAlign: 'center', padding: 16 }}>
              <Spin tip="AI 正在思考...">
                <div style={{ minHeight: 40 }} />
              </Spin>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div style={{ display: 'flex', gap: 8 }}>
          <TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder={
              isInitialized 
                ? "输入消息... (Ctrl+Enter 发送)" 
                : "请先配置聊天服务..."
            }
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={isLoading || !isInitialized}
            style={{ flex: 1 }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={isLoading}
            disabled={!inputValue.trim() || !isInitialized}
            size="large"
          >
            发送
          </Button>
        </div>
      </Card>

      {/* 设置模态框 */}
      <Modal
        title={
          <Space>
            <SettingOutlined />
            <span>聊天设置</span>
          </Space>
        }
        open={settingsVisible}
        onCancel={() => setSettingsVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          layout="vertical"
          initialValues={chatConfig || {
            provider: 'dashscope',
            model: 'qwen3-32b',
            maxTokens: 4000,
            temperature: 0.7
          }}
          onFinish={handleSaveSettings}
        >
          <Form.Item 
            label="API 提供商" 
            name="provider"
            rules={[{ required: true, message: '请选择API提供商' }]}
          >
            <Select>
              <Option value="dashscope">阿里云通义千问</Option>
              <Option value="openai">OpenAI</Option>
              <Option value="custom">自定义</Option>
            </Select>
          </Form.Item>

          <Form.Item 
            label="API Key" 
            name="apiKey"
            rules={[{ required: true, message: '请输入API Key' }]}
          >
            <Input.Password 
              placeholder="请输入您的API Key" 
              autoComplete="off"
            />
          </Form.Item>

          <Form.Item 
            label="模型名称" 
            name="model"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input 
              placeholder="例如: qwen3-32b, gpt-4, claude-3-sonnet"
              addonBefore="模型:"
            />
          </Form.Item>

          <Form.Item 
            dependencies={['provider']}
            shouldUpdate={(prevValues, currentValues) => prevValues.provider !== currentValues.provider}
          >
            {({ getFieldValue }) => {
              const provider = getFieldValue('provider');
              return provider === 'custom' ? (
                <Form.Item 
                  label="自定义 API 地址" 
                  name="baseURL"
                  rules={[{ required: true, message: '请输入API地址' }]}
                >
                  <Input placeholder="https://api.example.com/v1" />
                </Form.Item>
              ) : null;
            }}
          </Form.Item>

          <Form.Item label="最大令牌数" name="maxTokens">
            <Input type="number" min={100} max={8000} placeholder="4000" />
          </Form.Item>

          <Form.Item label="温度 (创造性)" name="temperature">
            <Input type="number" min={0} max={2} step={0.1} placeholder="0.7" />
          </Form.Item>

          <Divider>MCP 系统集成</Divider>

          <Form.Item>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <Switch 
                  checked={mcpEnabled}
                  onChange={setMcpEnabled}
                />
                <span>启用 MCP 系统集成</span>
                <Tag color={mcpConnected ? 'green' : mcpEnabled ? 'orange' : 'default'}>
                  {mcpConnected ? '已连接' : mcpEnabled ? '连接中' : '已禁用'}
                </Tag>
              </Space>
              <Text type="secondary" style={{ fontSize: 12 }}>
                启用后，AI 助手可以实时访问 Trustee 系统数据，提供更准确的答案和操作支持
              </Text>
            </Space>
          </Form.Item>

          {mcpEnabled && mcpConnected && mcpTools.length > 0 && (
            <Form.Item label={`可用工具 (${mcpTools.length}个)`}>
              <div style={{ 
                maxHeight: '200px', 
                overflowY: 'auto', 
                border: '1px solid #d9d9d9', 
                borderRadius: '6px', 
                padding: '8px' 
              }}>
                {mcpTools.map((tool, index) => (
                  <div key={index} style={{ 
                    marginBottom: '8px', 
                    padding: '8px', 
                    backgroundColor: '#fafafa', 
                    borderRadius: '4px' 
                  }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                      <Tag color="blue">{tool.name}</Tag>
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {tool.description || '无描述'}
                    </div>
                  </div>
                ))}
              </div>
            </Form.Item>
          )}

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                保存配置
              </Button>
              <Button onClick={() => setSettingsVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ChatPage; 