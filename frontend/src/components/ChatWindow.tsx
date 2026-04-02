import React, { useState, useEffect, useRef } from 'react';
import { useConversationStore } from '../store';
import styles from './ChatWindow.module.css';

const AGENT_COLORS: Record<string, string> = {
  Manager: '#0066cc',
  Developer: '#00aa44',
  Designer: '#9900ff',
  Researcher: '#ff9900',
};

let wsInstance: WebSocket | null = null;

export const ChatWindow: React.FC = () => {
  const {
    messages,
    isConnected,
    isLoading,
    processingStatus,
    addMessage,
    conversationId,
    setLoading,
  } = useConversationStore();
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, processingStatus]);

  const handleSendMessage = async () => {
    if (!input.trim() || !isConnected || isSending) return;

    setIsSending(true);
    setLoading(true);

    // Add user message to store
    const userMessage = {
      id: `msg-${Date.now()}`,
      conversationId,
      senderType: 'user' as const,
      content: input,
      timestamp: new Date(),
      type: 'text' as const,
    };

    addMessage(userMessage);
    const messageText = input;
    setInput('');

    // Send to backend via WebSocket
    try {
      if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
        wsInstance.send(JSON.stringify({ content: messageText }));
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }

    setIsSending(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className={styles.chatWindow}>
      <div className={styles.header}>
        <div className={styles.status}>
          {isConnected ? (
            <span className={styles.connected}>● 연결됨</span>
          ) : (
            <span className={styles.disconnected}>● 연결 중단</span>
          )}
        </div>
      </div>

      <div className={styles.messagesContainer}>
        {messages.length === 0 && !processingStatus ? (
          <div className={styles.emptyState}>
            <p>👋 대화를 시작하세요</p>
            <p style={{ fontSize: '12px', color: '#999' }}>
              메시지를 입력하면 4명의 에이전트가 함께 응답합니다
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`${styles.message} ${styles[message.senderType]} ${
                  message.type === 'error' ? styles.error : ''
                }`}
              >
                <div className={styles.messageHeader}>
                  <span
                    className={styles.sender}
                    style={
                      message.senderType === 'agent'
                        ? {
                            color: AGENT_COLORS[message.agentName?.toLowerCase() || 'manager'],
                          }
                        : {}
                    }
                  >
                    {message.senderType === 'user' ? '나' : message.agentName}
                  </span>
                  <span className={styles.timestamp}>
                    {message.timestamp.toLocaleTimeString('ko-KR', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
                <div className={styles.content}>{message.content}</div>
              </div>
            ))}
          </>
        )}

        {(isLoading || processingStatus) && (
          <div className={styles.message}>
            <div className={styles.thinking}>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
              {processingStatus || '에이전트가 생각 중...'}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className={styles.inputArea}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="메시지를 입력하세요... (Shift+Enter: 줄바꿈)"
          disabled={!isConnected || isSending}
          className={styles.input}
          rows={3}
        />
        <button
          onClick={handleSendMessage}
          disabled={!isConnected || !input.trim() || isSending}
          className={styles.sendButton}
        >
          {isSending ? '전송 중...' : '전송'}
        </button>
      </div>
    </div>
  );
};
