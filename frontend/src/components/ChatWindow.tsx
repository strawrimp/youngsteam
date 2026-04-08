import React, { useState, useRef, useEffect, useCallback } from 'react';
import MessageBubble, { MessageRole } from './MessageBubble';
import TypingIndicator from './TypingIndicator';
import { InviteModal } from './InviteModal';
import { useMention } from '../hooks/useMention';
import { useConversationStore } from '../store';
import { api } from '../api';
import { InviteSuggestion, MentionCandidate } from '../types';
import { useTheme } from '../hooks/useTheme';

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
                ? 'bg-blue-900/40 text-blue-300' 
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
      <main className={`flex-1 flex flex-col min-w-0 ${
        isDark ? 'bg-slate-900' : 'bg-white'
      }`}>
        {/* Chat Stream Area */}
        <div className={`flex-1 overflow-y-auto p-8 flex flex-col gap-8 no-scrollbar ${
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
            <div className={`flex-1 flex flex-col items-center justify-center gap-3 py-16 ${
              isDark ? 'text-slate-500' : 'text-slate-400'
            }`}>
              <span className="material-symbols-outlined text-5xl">forum</span>
              <p className="text-sm font-medium">경영진 팀에게 명령을 내리세요</p>
              <p className={`text-xs ${
                isDark ? 'text-slate-600' : 'text-slate-400'
              }`}>@멘션으로 특정 에이전트를 호출할 수 있습니다</p>
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
                placeholder="경영진 팀에게 명령을 내리세요... (@멘션 가능)"
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
                           isDark ? 'bg-blue-600' : 'bg-primary'
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
