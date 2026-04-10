import React, { useState, useRef, useEffect, useCallback } from 'react';
import MessageBubble, { MessageRole } from './MessageBubble';
import TypingIndicator from './TypingIndicator';
import { InviteModal } from './InviteModal';
import { useMention } from '../hooks/useMention';
import { useConversationStore } from '../store';
import { api } from '../api';
import { InviteSuggestion, MentionCandidate } from '../types';
import { useTheme } from '../hooks/useTheme';
import { getAgentConfig } from '../agentConfig';

// 예시 프롬프트
const EXAMPLE_PROMPTS = [
  '이번 스프린트에서 가장 중요한 기능 3가지를 우선순위별로 정해주세요',
  '새로운 랜딩 페이지 디자인 컨셉을 제안해 주세요',
  '경쟁사 최신 트렌드를 분석해 주세요',
  '현재 아키텍처의 개선점을 찾아주세요',
];

export interface ChatMessage {
  id: string;
  role: MessageRole;
  name: string;
  content: string;
  isCode?: boolean;
  isUser?: boolean;
}

interface ChatWindowProps {
  messages?: ChatMessage[];
  isTyping?: boolean;
  typingAgentName?: string;
  onSendMessage?: (message: string) => void;
  dateLabel?: string;
}

// Mention Dropdown Component
interface MentionDropdownProps {
  candidates: MentionCandidate[];
  selectedIndex: number;
  onSelect: (candidate: MentionCandidate) => void;
  position: { top: number; left: number };
}

const MentionDropdown: React.FC<MentionDropdownProps> = ({
  candidates,
  selectedIndex,
  onSelect,
  position,
}) => {
  const { isDark } = useTheme();
  
  if (candidates.length === 0) return null;

  return (
    <div
      className={`absolute z-50 border rounded-lg shadow-lg 
                 max-h-48 overflow-y-auto min-w-[200px] ${
                   isDark 
                     ? 'bg-slate-800 border-slate-700' 
                     : 'bg-white border-slate-200'
                 }`}
      style={{ top: position.top, left: position.left }}
    >
      {candidates.map((candidate, index) => (
        <button
          key={candidate.id}
          onClick={() => onSelect(candidate)}
          className={`w-full px-4 py-2 flex items-center gap-3 text-left transition-colors
            ${index === selectedIndex
              ? isDark
                ? 'bg-slate-700/40 text-slate-300'
                : 'bg-primary/10 text-primary'
              : isDark
                ? 'hover:bg-slate-700'
                : 'hover:bg-slate-50'}`}
        >
          <span className="text-xl">
            {candidate.emoji || '🤖'}
          </span>
          <div>
            <div className={`font-medium text-sm ${
              isDark ? 'text-slate-200' : ''
            }`}>{candidate.display_name || candidate.name}</div>
            <div className={`text-xs ${
              isDark ? 'text-slate-500' : 'text-slate-500'
            }`}>@{candidate.name}</div>
          </div>
        </button>
      ))}
    </div>
  );
};

const ChatWindow: React.FC<ChatWindowProps> = ({
  messages: propsMessages,
  isTyping = false,
  typingAgentName,
  onSendMessage,
  dateLabel = '경영 동기화 • 14:00',
}) => {
  const [inputValue, setInputValue] = useState('');
  const [cursorPosition, setCursorPosition] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputContainerRef = useRef<HTMLDivElement>(null);
  
  // Theme
  const { isDark } = useTheme();

  // Get messages from store
  const storeMessages = useConversationStore((state) => state.messages);
  const processingStatus = useConversationStore((state) => state.processingStatus);
  const agents = useConversationStore((state) => state.agents);
  const conversationId = useConversationStore((state) => state.conversationId);
  const wsInstance = useConversationStore((state) => state.wsInstance);

  const displayMessages = storeMessages.length > 0 ? storeMessages : (propsMessages || []);

  // Mention hook
  const handleMentionAgent = useCallback(async (agentId: string) => {
    if (!conversationId) return;
    try {
      await api.mentionAgent({
        conversation_id: conversationId,
        mentioned_agent_id: agentId,
        message: inputValue,
      });
    } catch (error) {
      console.error('Failed to mention agent:', error);
    }
  }, [conversationId, inputValue]);

  const {
    mentionState,
    handleInput: handleMentionInput,
    selectCandidate,
    handleKeyDown: handleMentionKeyDown,
  } = useMention({ agents, onMention: handleMentionAgent });

  // Invite suggestions state
  const [inviteSuggestions, setInviteSuggestions] = useState<InviteSuggestion[]>([]);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);

  // WebSocket event listener for invite suggestions
  useEffect(() => {
    if (!wsInstance) return;

    const handleInviteSuggested = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'INVITE_SUGGESTED' && data.suggestions) {
          setInviteSuggestions(data.suggestions);
          setIsInviteModalOpen(true);
        }
      } catch (error) {
        console.error('Failed to parse invite event:', error);
      }
    };

    wsInstance.addEventListener('message', handleInviteSuggested);
    return () => {
      wsInstance.removeEventListener('message', handleInviteSuggested);
    };
  }, [wsInstance]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [displayMessages, isTyping]);

  const handleSend = () => {
    if (inputValue.trim() && onSendMessage) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    const cursorPos = e.target.selectionStart || 0;
    setInputValue(value);
    setCursorPosition(cursorPos);
    handleMentionInput(value, cursorPos);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    // Handle mention navigation first
    const keyResult = handleMentionKeyDown(e);
    if (keyResult === true) return; // Handled by mention

    if (typeof keyResult === 'object' && keyResult.shouldSelect) {
      // Select mention candidate
      const result = selectCandidate(
        keyResult.candidate,
        inputValue,
        cursorPosition
      );
      if (result) {
        setInputValue(result.newValue);
        setTimeout(() => {
          inputRef.current?.setSelectionRange(
            result.newCursorPosition,
            result.newCursorPosition
          );
        }, 0);
      }
      return;
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Invite handlers
  const handleAcceptInvite = async (agentId: string) => {
    try {
      await api.acceptInvite({
        conversation_id: conversationId,
        agent_id: agentId,
      });
      setInviteSuggestions((prev) => prev.filter((s) => s.agent_id !== agentId));
      if (inviteSuggestions.length === 1) {
        setIsInviteModalOpen(false);
      }
    } catch (error) {
      console.error('Failed to accept invite:', error);
    }
  };

  const handleRejectInvite = async (agentId: string) => {
    try {
      await api.rejectInvite({
        conversation_id: conversationId,
        agent_id: agentId,
      });
      setInviteSuggestions((prev) => prev.filter((s) => s.agent_id !== agentId));
      if (inviteSuggestions.length === 1) {
        setIsInviteModalOpen(false);
      }
    } catch (error) {
      console.error('Failed to reject invite:', error);
    }
  };

  // Calculate mention dropdown position
  const getMentionDropdownPosition = () => {
    if (!inputRef.current) return { top: 0, left: 0 };
    const rect = inputRef.current.getBoundingClientRect();
    return {
      top: rect.top - 200, // Show above input
      left: rect.left,
    };
  };

  return (
    <>
      <main className={`flex-1 flex flex-col min-w-0 min-h-0 ${
        isDark ? 'bg-slate-900' : 'bg-white'
      }`}>
        {/* Chat Stream Area */}
        <div className={`flex-1 overflow-y-auto p-8 flex flex-col gap-8 no-scrollbar min-h-0 ${
          isDark ? 'bg-slate-900/50' : 'bg-slate-50/30'
        }`}>
          {/* Date Label */}
          <div className="flex justify-center">
            <span className={`px-4 py-1 rounded-full text-[10px] font-bold tracking-widest uppercase ${
              isDark 
                ? 'bg-slate-800 text-slate-400' 
                : 'bg-slate-200 text-slate-600'
            }`}>
              {dateLabel}
            </span>
          </div>

          {/* Status Message */}
          {processingStatus && (
            <div className={`text-center text-sm ${
              isDark ? 'text-slate-400' : 'text-slate-600'
            }`}>
              {processingStatus}
            </div>
          )}

          {/* Empty state */}
          {displayMessages.length === 0 && !isTyping && (
            <div className={`flex-1 flex flex-col items-center justify-center gap-6 py-16 px-4 ${
              isDark ? 'text-slate-500' : 'text-slate-400'
            }`}>
              {/* 웰컴 아이콘 */}
              <div className={`w-20 h-20 rounded-2xl flex items-center justify-center ${
                isDark ? 'bg-slate-800' : 'bg-slate-100'
              }`}>
                <span className="material-symbols-outlined text-4xl" style={{ fontVariationSettings: '"FILL" 0, "wght" 300' }}>
                  smart_toy
                </span>
              </div>
              
              {/* 웰컴 메시지 */}
              <div className="text-center max-w-md">
                <h3 className={`text-lg font-bold mb-2 ${
                  isDark ? 'text-slate-200' : 'text-slate-700'
                }`}>
                  AI 경영진 팀과 협업하세요
                </h3>
                <p className={`text-sm leading-relaxed ${
                  isDark ? 'text-slate-400' : 'text-slate-500'
                }`}>
                  당신의 AI 팀이 프로젝트의 모든 측면에서 전문적인 인사이트를 제공합니다.
                  아래 에이전트에게 직접 명령을 내리거나, @멘션으로 특정 팀원을 호출할 수 있습니다.
                </p>
              </div>

              {/* 에이전트 소개 카드 */}
              <div className="grid grid-cols-2 gap-3 w-full max-w-lg">
                {agents.length > 0 ? agents.map((agent) => {
                  const config = getAgentConfig(agent.id, agents);
                  return (
                    <div
                      key={agent.id}
                      className={`rounded-xl p-3 border transition-all hover:shadow-sm ${
                        isDark 
                          ? 'bg-slate-800/50 border-slate-700/50' 
                          : 'bg-white border-slate-200/80'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg">{config.emoji}</span>
                        <span className={`text-sm font-bold ${
                          isDark ? 'text-slate-200' : 'text-slate-700'
                        }`}>
                          {config.display_name}
                        </span>
                      </div>
                      <p className={`text-[11px] leading-relaxed ${
                        isDark ? 'text-slate-400' : 'text-slate-500'
                      }`}>
                        {config.description || '팀원입니다'}
                      </p>
                    </div>
                  );
                }) : (
                  // 에이전트가 아직 로드되지 않은 경우
                  <div className={`col-span-2 text-center py-4 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                    <p className="text-sm">에이전트 팀을 불러오는 중...</p>
                  </div>
                )}
              </div>

              {/* 예시 프롬프트 */}
              <div className="w-full max-w-lg">
                <p className={`text-[10px] font-bold uppercase tracking-wider mb-3 text-center ${
                  isDark ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  이렇게 물어보세요
                </p>
                <div className="grid grid-cols-1 gap-2">
                  {EXAMPLE_PROMPTS.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setInputValue(prompt);
                        inputRef.current?.focus();
                      }}
                      className={`text-left text-xs px-4 py-2.5 rounded-lg border transition-all hover:shadow-sm ${
                        isDark
                          ? 'bg-slate-800/30 border-slate-700/50 text-slate-400 hover:bg-slate-800/60 hover:text-slate-300'
                          : 'bg-white border-slate-200/80 text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                      }`}
                    >
                      💬 "{prompt}"
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Messages */}
          {displayMessages.map((message) => {
            // Handle both old (role/name/isUser) and new (senderType/agentName) formats
            const isUser = (message as any).isUser === true || message.senderType === 'user';

            // Determine role from multiple sources
            const agentNameLower = (message.agentName as string)?.toLowerCase() ?? '';
            const validRoles = ['manager', 'developer', 'designer', 'researcher', 'user'];
            const inferredRole = validRoles.includes(agentNameLower) ? agentNameLower : (isUser ? 'user' : 'manager');
            const role = ((message as any).role as string) || inferredRole;

            const name = (message as any).name || message.agentName || (isUser ? '나' : 'Unknown');

            return (
              <MessageBubble
                key={message.id}
                role={role as MessageRole}
                name={name}
                content={message.content}
                isCode={false}
                isUser={isUser}
              />
            );
          })}

          {/* Typing Indicator */}
          {isTyping && <TypingIndicator agentName={typingAgentName} />}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Section */}
        <footer className="p-8 pt-0">
          <div 
            ref={inputContainerRef}
            className={`relative max-w-input mx-auto border rounded-2xl p-2 shadow-lg flex items-center gap-2 ${
              isDark 
                ? 'bg-slate-800 border-slate-700' 
                : 'bg-white border-slate-200'
            }`}
          >
            <button className={`p-3 transition-colors ${
              isDark 
                ? 'text-slate-500 hover:text-slate-300' 
                : 'text-slate-400 hover:text-primary'
            }`}>
              <span className="material-symbols-outlined">attach_file</span>
            </button>
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                className={`w-full bg-transparent border-none outline-none focus:ring-0 font-medium ${
                  isDark 
                    ? 'text-slate-100 placeholder-slate-500' 
                    : 'text-slate-900 placeholder-slate-400'
                }`}
                placeholder="팀에게 질문하거나 명령을 내려주세요... (@멘션으로 특정 에이전트 호출)"
              />
              
              {/* Mention Dropdown */}
              {mentionState.isActive && mentionState.candidates.length > 0 && (
                <MentionDropdown
                  candidates={mentionState.candidates}
                  selectedIndex={mentionState.selectedIndex}
                  onSelect={(candidate) => {
                    const result = selectCandidate(candidate, inputValue, cursorPosition);
                    if (result) {
                      setInputValue(result.newValue);
                      setTimeout(() => {
                        inputRef.current?.setSelectionRange(
                          result.newCursorPosition,
                          result.newCursorPosition
                        );
                      }, 0);
                    }
                  }}
                  position={getMentionDropdownPosition()}
                />
              )}
            </div>
            <button 
              onClick={handleSend}
              className={`p-3 text-white rounded-xl hover:brightness-110
                         active:scale-95 transition-all flex items-center justify-center ${
                            isDark ? 'bg-slate-600' : 'bg-primary'
                          }`}
            >
              <span className="material-symbols-outlined">send</span>
            </button>
          </div>
        </footer>

        {/* Invite Modal */}
        {isInviteModalOpen && inviteSuggestions.length > 0 && (
          <InviteModal
            suggestions={inviteSuggestions}
            onAccept={handleAcceptInvite}
            onReject={handleRejectInvite}
            onClose={() => setIsInviteModalOpen(false)}
          />
        )}
      </main>
    </>
  );
};

export default ChatWindow;
