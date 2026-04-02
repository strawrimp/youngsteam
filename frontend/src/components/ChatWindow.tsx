import React, { useState, useEffect, useRef } from 'react';
import { useConversationStore } from '../store';

const AGENT_COLORS: Record<string, string> = {
  manager: '#4E7EBE',
  developer: '#4A9B6F',
  designer: '#7C6BA8',
  researcher: '#D4A055',
};

interface ChatWindowProps {
  wsInstance?: WebSocket | null;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ wsInstance: wsFromProps }) => {
  const {
    messages,
    isConnected,
    isLoading,
    processingStatus,
    addMessage,
    conversationId,
    setLoading,
    wsInstance: wsFromStore,
    isSending,
    setIsSending,
  } = useConversationStore();

  const wsInstance = wsFromProps !== undefined ? wsFromProps : wsFromStore;
  const wsRef = useRef<WebSocket | null>(wsInstance);

  useEffect(() => {
    wsRef.current = wsInstance;
  }, [wsInstance]);

  useEffect(() => {
    if (!processingStatus && isLoading) {
      setIsSending(false);
      setLoading(false);
    }
  }, [processingStatus, isLoading, setIsSending, setLoading]);

  const [input, setInput] = useState('');
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

    const ws = wsRef.current;
    console.log('Sending message, WebSocket readyState:', ws?.readyState);
    try {
      if (ws && ws.readyState === WebSocket.OPEN) {
        console.log('Sending to WebSocket:', messageText);
        ws.send(JSON.stringify({ content: messageText }));
      } else {
        console.error('WebSocket not open, state:', ws?.readyState);
        setIsSending(false);
        setLoading(false);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setIsSending(false);
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white overflow-hidden">
      {/* Header with connection status */}
      <div className="flex-shrink-0 border-b border-neutral-300 px-lg py-md bg-neutral-50">
        <div className="flex items-center gap-md">
          <span className={`inline-block w-2 h-2 rounded-full ${isConnected ? 'bg-success' : 'bg-error'}`} />
          <span className="text-sm font-medium text-neutral-700">
            {isConnected ? '✓ 연결됨' : '○ 연결 중단'}
          </span>
        </div>
      </div>

      {/* Messages container */}
      <div className="flex-1 overflow-y-auto p-lg space-y-lg">
        {messages.length === 0 && !processingStatus ? (
          <div className="flex flex-col items-center justify-center h-full gap-md text-center">
            <p className="text-2xl">👋</p>
            <p className="text-base font-medium text-neutral-900">대화를 시작하세요</p>
            <p className="text-sm text-neutral-600">
              메시지를 입력하면 4명의 에이전트가 함께 응답합니다
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={
                  message.senderType === 'user'
                    ? 'message-user'
                    : message.type === 'error'
                    ? 'message-system'
                    : 'message-agent'
                }
              >
                {message.senderType !== 'user' && (
                  <div className="flex items-center justify-between mb-md">
                    <div className="flex items-center gap-sm">
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: AGENT_COLORS[message.agentName?.toLowerCase() || 'manager'] }}
                      />
                      <span
                        className="text-xs font-semibold"
                        style={{ color: AGENT_COLORS[message.agentName?.toLowerCase() || 'manager'] }}
                      >
                        {message.agentName}
                      </span>
                    </div>
                    <span className="text-caption text-neutral-600">
                      {message.timestamp.toLocaleTimeString('ko-KR', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                )}
                <div className="text-base leading-relaxed text-neutral-800">{message.content}</div>
                {message.senderType === 'user' && (
                  <span className="text-caption text-white opacity-70 mt-xs block">
                    {message.timestamp.toLocaleTimeString('ko-KR', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                )}
              </div>
            ))}
          </>
        )}

        {(isLoading || processingStatus) && (
          <div className="message-agent">
            <div className="flex items-center gap-md">
              <div className="flex gap-xs">
                <span className="inline-block w-2 h-2 rounded-full bg-agent-manager animate-pulse" />
                <span className="inline-block w-2 h-2 rounded-full bg-agent-manager animate-pulse" style={{ animationDelay: '0.2s' }} />
                <span className="inline-block w-2 h-2 rounded-full bg-agent-manager animate-pulse" style={{ animationDelay: '0.4s' }} />
              </div>
              <span className="text-sm text-neutral-700">
                {processingStatus || '에이전트가 생각 중...'}
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 border-t border-neutral-300 bg-white p-lg space-y-md">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="메시지를 입력하세요... (Shift+Enter: 줄바꿈)"
          disabled={!isConnected || isSending}
          className="textarea w-full max-h-[120px]"
          rows={3}
        />
        <button
          onClick={handleSendMessage}
          disabled={!isConnected || !input.trim() || isSending}
          className="btn w-full bg-agent-manager text-white"
        >
          {isSending ? '전송 중...' : '전송'}
        </button>
      </div>
    </div>
  );
};
