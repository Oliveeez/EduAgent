/**
 * Step 2.5: 讲稿编辑页面
 * 类似Claude的对话界面，支持多轮交互编辑讲稿
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Layout,
  Input,
  Button,
  Card,
  Space,
  Spin,
  message,
  Typography,
  Collapse,
  Tag,
  Divider,
  Modal,
  Tooltip,
} from 'antd';
import {
  SendOutlined,
  SaveOutlined,
  RobotOutlined,
  UserOutlined,
  FileTextOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { editScript, saveScript, getScriptConversation, initScriptEdit } from '../services/api';
import '../styles/ScriptEdit.css';

const { Content, Sider } = Layout;
const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

function Step2ScriptEdit({ sessionData, updateSessionData, onBack, onNext }) {
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [initialized, setInitialized] = useState(false);
  
  const [userMessage, setUserMessage] = useState('');
  const [conversation, setConversation] = useState([]);
  const [currentScript, setCurrentScript] = useState(null);
  const [modificationCount, setModificationCount] = useState(0);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 初始化编辑会话
  useEffect(() => {
    if (sessionData.outlineId && !initialized) {
      initializeSession();
    }
  }, [sessionData.outlineId]);

  // 自动滚动到最新消息
  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const initializeSession = async () => {
    setLoading(true);
    try {
      const response = await initScriptEdit(sessionData.outlineId);
      
      if (response.success) {
        setCurrentScript(response.current_script);
        setInitialized(true);
        
        // 添加欢迎消息
        setConversation([
          {
            role: 'assistant',
            content: '您好！我是讲稿编辑助手。我已经加载了您的讲稿，您可以告诉我需要如何修改，例如：\n\n• "第一章节的开场白太简短了，请丰富一下"\n• "第二个知识点需要增加一些实例"\n• "整体语气太正式了，请改得口语化一些"\n\n请告诉我您的需求吧！',
            timestamp: new Date().toISOString(),
          },
        ]);
        
        message.success('编辑会话已初始化');
      }
    } catch (error) {
      message.error('初始化失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!userMessage.trim()) {
      message.warning('请输入修改需求');
      return;
    }

    // 添加用户消息到对话
    const newUserMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    };
    
    setConversation((prev) => [...prev, newUserMessage]);
    setUserMessage('');
    setSending(true);

    try {
      const response = await editScript({
        outline_id: sessionData.outlineId,
        user_message: userMessage,
        context: null,
      });

      if (response.success) {
        // 添加助手响应
        const assistantMessage = {
          role: 'assistant',
          content: response.assistant_message,
          timestamp: new Date().toISOString(),
          modifications: response.modifications_applied,
        };
        
        setConversation((prev) => [...prev, assistantMessage]);
        setCurrentScript(response.updated_script);
        setModificationCount((prev) => prev + response.modifications_applied);
        
        if (response.modifications_applied > 0) {
          message.success(`已应用 ${response.modifications_applied} 项修改`);
        }
      }
    } catch (error) {
      message.error('发送失败：' + error.message);
      
      // 添加错误消息
      setConversation((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '抱歉，处理您的请求时出现了错误。请稍后重试。',
          timestamp: new Date().toISOString(),
          error: true,
        },
      ]);
    } finally {
      setSending(false);
      // 重新聚焦输入框
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  };

  const handleSaveScript = async () => {
    if (!currentScript) {
      message.warning('没有可保存的讲稿');
      return;
    }

    setLoading(true);
    try {
      const response = await saveScript({
        outline_id: sessionData.outlineId,
        updated_script: currentScript,
      });

      if (response.success) {
        message.success('讲稿已保存');
        updateSessionData({ script: currentScript });
      }
    } catch (error) {
      message.error('保存失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteEditing = async () => {
    if (!currentScript) {
      message.warning('没有可保存的讲稿');
      return;
    }

    setLoading(true);
    try {
      // 先保存讲稿
      const response = await saveScript({
        outline_id: sessionData.outlineId,
        updated_script: currentScript,
      });

      if (response.success) {
        message.success('讲稿已保存，进入下一步');
        updateSessionData({ script: currentScript });
        
        // 进入下一步
        if (onNext) {
          onNext();
        }
      }
    } catch (error) {
      message.error('保存失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const renderMessage = (msg, index) => {
    const isUser = msg.role === 'user';
    const isError = msg.error;

    return (
      <div key={index} className={`message ${isUser ? 'user-message' : 'assistant-message'}`}>
        <div className="message-avatar">
          {isUser ? <UserOutlined /> : <RobotOutlined />}
        </div>
        <div className="message-content">
          <div className="message-header">
            <Text strong>{isUser ? '您' : 'AI助手'}</Text>
            <Text type="secondary" className="message-time">
              {new Date(msg.timestamp).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Text>
          </div>
          <div className={`message-text ${isError ? 'error-message' : ''}`}>
            {msg.content.split('\n').map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
          {msg.modifications > 0 && (
            <div className="message-footer">
              <Tag color="green" icon={<CheckCircleOutlined />}>
                已应用 {msg.modifications} 项修改
              </Tag>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderScriptPreview = () => {
    if (!currentScript || !currentScript.sections) {
      return (
        <div className="empty-state">
          <FileTextOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
          <p>讲稿加载中...</p>
        </div>
      );
    }

    return (
      <Collapse defaultActiveKey={['0']} className="script-preview">
        {currentScript.sections.map((section, index) => (
          <Panel
            header={
              <Space>
                <Text strong>章节 {index + 1}:</Text>
                <Text>{section.title}</Text>
              </Space>
            }
            key={index}
          >
            {section.opening && (
              <Card size="small" className="script-section" title="开场白">
                <div className="script-text">{section.opening}</div>
              </Card>
            )}

            {section.points && section.points.length > 0 && (
              <Card size="small" className="script-section" title="知识点讲解">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {section.points.map((point, pIndex) => (
                    <div key={pIndex} className="script-point">
                      <Tag color="blue">知识点 {pIndex + 1}</Tag>
                      <div className="script-text">{point.text}</div>
                    </div>
                  ))}
                </Space>
              </Card>
            )}

            {section.closing && (
              <Card size="small" className="script-section" title="总结">
                <div className="script-text">{section.closing}</div>
              </Card>
            )}
          </Panel>
        ))}
      </Collapse>
    );
  };

  return (
    <div className="script-edit-container">
      <Layout style={{ height: 'calc(100vh - 200px)' }}>
        {/* 左侧：讲稿预览 */}
        <Sider width={400} theme="light" className="script-preview-sider">
          <div className="sider-header">
            <Title level={4}>
              <FileTextOutlined /> 当前讲稿
            </Title>
            {modificationCount > 0 && (
              <Tag color="orange">{modificationCount} 处修改</Tag>
            )}
          </div>
          <div className="sider-content">{renderScriptPreview()}</div>
        </Sider>

        {/* 右侧：对话区域 */}
        <Content className="conversation-content">
          <div className="conversation-header">
            <Space>
              <Button icon={<ArrowLeftOutlined />} onClick={onBack}>
                返回
              </Button>
              <Title level={4}>
                <RobotOutlined /> 讲稿编辑助手
              </Title>
            </Space>
            <Space>
              <Button
                icon={<SaveOutlined />}
                onClick={handleSaveScript}
                loading={loading}
                disabled={!currentScript}
              >
                保存讲稿
              </Button>
              <Button
                type="primary"
                icon={<ArrowRightOutlined />}
                onClick={handleCompleteEditing}
                loading={loading}
                disabled={!currentScript}
                size="large"
              >
                完成编辑，进入 Step 3
              </Button>
            </Space>
          </div>

          {/* 对话消息列表 */}
          <div className="conversation-messages">
            {loading && !initialized ? (
              <div className="loading-state">
                <Spin size="large" tip="正在初始化编辑会话..." />
              </div>
            ) : (
              <>
                {conversation.map((msg, index) => renderMessage(msg, index))}
                {sending && (
                  <div className="message assistant-message typing">
                    <div className="message-avatar">
                      <RobotOutlined />
                    </div>
                    <div className="message-content">
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* 输入区域 */}
          <div className="conversation-input">
            <TextArea
              ref={inputRef}
              value={userMessage}
              onChange={(e) => setUserMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="描述您想要的修改，例如：'第一章节的开场白需要更生动一些'"
              autoSize={{ minRows: 2, maxRows: 6 }}
              disabled={!initialized || sending}
            />
            <div className="input-actions">
              <Text type="secondary" className="input-hint">
                按 Enter 发送，Shift + Enter 换行
              </Text>
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSendMessage}
                loading={sending}
                disabled={!initialized || !userMessage.trim()}
              >
                发送
              </Button>
            </div>
          </div>
        </Content>
      </Layout>

      {/* 帮助提示 */}
      <div className="help-tips">
        <Text type="secondary">
          💡 提示：您可以要求修改开场白、总结、知识点讲解，或者调整语气、增加示例等
        </Text>
      </div>
    </div>
  );
}

export default Step2ScriptEdit;