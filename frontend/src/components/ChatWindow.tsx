import React, { useState, useEffect, useRef } from 'react';
import { useConversationStore } from '../store';
import styles from './ChatWindow.module.css';

const AGENT_COLORS: Record<string, string> = {
  Manager: '#0066CC',
  Developer: '#00AA44',
  Designer: '#9900FF',
  Researcher: '#FF9900',
};

export const ChatWindow: React.FC = () => {
  const { messages, isConnected, isLoading, addMessage } = useConversationStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    // Add user message to store
    const userMessage = {
      id: `msg-${Date.now()}`,
      conversationId: 'test-conversation',
      senderType: 'user' as const,
      content: input,
      timestamp: new Date(),
    };

    addMessage(userMessage);
    setInput('');

    // Send to backend via WebSocket
    if (isConnected) {
      // WebSocket connection would be handled in a separate hook
      console.log('Would send to WebSocket:', userMessage);
    }
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
        <h2>AI 가상 회사</h2>
        <div className={styles.status}>
          {isConnected ? (
            <span className={styles.connected}>● 연결됨</span>
          ) : (
            <span className={styles.disconnected}>● 연결 중단</span>
          )}
        </div>
      </div>

      <div className={styles.messagesContainer}>
        {messages.length === 0 ? (
          <div className={styles.emptyState}>
            <p>대화를 시작하세요</p>
            <p style={{ fontSize: '12px', color: '#999' }}>
              메시지를 입력하면 에이전트들이 응답합니다
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`${styles.message} ${styles[message.senderType]}`}
            >
              <div className={styles.messageHeader}>
                <span
                  className={styles.sender}
                  style={
                    message.senderType === 'agent'
                      ? { color: AGENT_COLORS[message.agentName || 'Manager'] }
                      : {}
                  }
                >
                  {message.senderType === 'user' ? '나' : message.agentName}
                </span>
                <span className={styles.timestamp}>
                  {message.timestamp.toLocaleTimeString()}
                </span>
              </div>
              <div className={styles.content}>{message.content}</div>
            </div>
          ))
        )}

        {isLoading && (
          <div className={styles.message}>
            <div className={styles.thinking}>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
              에이전트가 생각 중...
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
          placeholder="메시지를 입력하세요..."
          disabled={!isConnected}
          className={styles.input}
        />
        <button
          onClick={handleSendMessage}
          disabled={!isConnected || !input.trim()}
          className={styles.sendButton}
        >
          전송
        </button>
      </div>
    </div>
  );
};
