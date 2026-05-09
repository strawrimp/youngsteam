import React, { useState, useRef, useEffect, useCallback } from 'react';
import MessageBubble, { MessageRole } from './MessageBubble';
import TypingIndicator from './TypingIndicator';
import AgentWorkingBar from './AgentWorkingBar';
import { InviteModal } from './InviteModal';
import { useMention } from '../hooks/useMention';
import { useConversationStore } from '../store';
import { api } from '../api';
import { InviteSuggestion, MentionCandidate, ReplyInfo } from '../types';
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
  onSendMessage?: (message: string, options?: { targetAgentRole?: string; imageUrl?: string }) => void;
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
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const inputContainerRef = useRef<HTMLDivElement>(null);
  const lastEscTimeRef = useRef<number>(0); // ESC double-tap 감지용
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ★ 이미지 첨부 상태
  const [attachedImage, setAttachedImage] = useState<{
    dataUrl: string;
    fileName: string;
  } | null>(null);

  // ★ 스마트 스크롤: 유저 메시지 전송 후 첫 에이전트 응답 위치로 스크롤
  const pendingSmartScrollRef = useRef(false);
  const prevMessageCountRef = useRef(0);
  
  // Theme
  const { isDark } = useTheme();

  // Get messages from store
  const storeMessages = useConversationStore((state) => state.messages);
  const processingStatus = useConversationStore((state) => state.processingStatus);
  const agents = useConversationStore((state) => state.agents);
  const conversationId = useConversationStore((state) => state.conversationId);
  const wsInstance = useConversationStore((state) => state.wsInstance);
  const isDebating = useConversationStore((state) => state.isDebating);
  const discussionMessages = useConversationStore((state) => state.discussionMessages);
  const discussionRound = useConversationStore((state) => state.discussionRound);
  const currentDiscussion = useConversationStore((state) => state.currentDiscussion);
  const replyingTo = useConversationStore((state) => state.replyingTo);
  const setReplyingTo = useConversationStore((state) => state.setReplyingTo);
  const workingAgents = useConversationStore((state) => state.workingAgents);

  const displayMessages = storeMessages.length > 0 ? storeMessages : (propsMessages || []);

  // Mention hook
  const handleMentionAgent = useCallback(async (agentId: string) => {
    // ★ openclaw-bot: WebSocket 전용 → API mention 호출 없이 early return
    if (agentId === 'openclaw-bot') {
      console.log('[Mention] openclaw-bot handles via WebSocket, skipping API mention');
      return;
    }
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

  // ★ 스마트 스크롤 시스템
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // 마지막 유저 메시지를 화면 상단에 배치
  const scrollToLastUserMessage = () => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const userBubbles = container.querySelectorAll('[data-is-user="true"]');
    if (userBubbles.length === 0) {
      container.scrollTop = container.scrollHeight;
      return;
    }
    const lastUserBubble = userBubbles[userBubbles.length - 1] as HTMLElement;
    const containerRect = container.getBoundingClientRect();
    const bubbleRect = lastUserBubble.getBoundingClientRect();
    container.scrollTop = bubbleRect.top - containerRect.top + container.scrollTop - 16;
    pendingSmartScrollRef.current = false;
  };

  const scrollToBottom = () => {
    const container = scrollContainerRef.current;
    if (container) container.scrollTop = container.scrollHeight;
  };

  // ★ 핵심 스크롤 로직 — displayMessages 변화에만 반응
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container || displayMessages.length === 0) return;

    const currentCount = displayMessages.length;
    const prevCount = prevMessageCountRef.current;

    // 메시지가 늘어났을 때만 동작
    if (currentCount <= prevCount) {
      prevMessageCountRef.current = currentCount;
      return;
    }

    // 초기 로드 (0 → N): 맨 아래로
    if (prevCount === 0) {
      scrollToBottom();
      prevMessageCountRef.current = currentCount;
      return;
    }

    if (pendingSmartScrollRef.current) {
      const lastMsg = displayMessages[displayMessages.length - 1];
      const isAgentMsg = lastMsg && (lastMsg as any).senderType === 'agent';
      if (isAgentMsg) {
        // 첫 에이전트 응답 → 유저 메시지 위치로 스크롤
        scrollToLastUserMessage();
      } else {
        // 유저 메시지 방금 추가됨 → 맨 아래로
        scrollToBottom();
      }
    }
    // pendingSmartScrollRef === false → 아무것도 안 함 (사용자가 자유롭게 읽음)

    prevMessageCountRef.current = currentCount;
  }, [displayMessages]);

  // workingAgents 변화 → 에이전트 대기중일 때만 레이아웃 보정
  useEffect(() => {
    if (workingAgents.length > 0 && pendingSmartScrollRef.current) {
      // AgentWorkingBar 등장으로 컨테이너 높이 줄어듦 → 유저 메시지 위치 재계산
      const t = setTimeout(() => {
        const container = scrollContainerRef.current;
        if (!container) return;
        const userBubbles = container.querySelectorAll('[data-is-user="true"]');
        if (userBubbles.length > 0) {
          const lastUserBubble = userBubbles[userBubbles.length - 1] as HTMLElement;
          const containerRect = container.getBoundingClientRect();
          const bubbleRect = lastUserBubble.getBoundingClientRect();
          const userAtTop = bubbleRect.top - containerRect.top;
          // 유저 메시지가 화면 위쪽에 있으면 위치 유지, 아니면 맨 아래로
          if (userAtTop < 0) {
            container.scrollTop = bubbleRect.top - containerRect.top + container.scrollTop - 16;
          }
        } else {
          scrollToBottom();
        }
      }, 50);
      return () => clearTimeout(t);
    }
  }, [workingAgents]);

  // textarea 자동 높이 조절 (내용에 따라 1~5줄)
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }, [inputValue]);

  // ★ 이미지 파일 선택 핸들러
  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 이미지 파일만 허용 (최대 10MB)
    if (!file.type.startsWith('image/')) {
      alert('이미지 파일만 첨부할 수 있습니다.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      alert('10MB 이하의 이미지만 첨부할 수 있습니다.');
      return;
    }

    // base64로 변환하여 미리보기
    const reader = new FileReader();
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result as string;
      setAttachedImage({ dataUrl, fileName: file.name });
      inputRef.current?.focus();
    };
    reader.readAsDataURL(file);

    // input 리셋 (같은 파일 재선택 가능)
    e.target.value = '';
  };

  // ★ 이미지 첨부 취소
  const handleRemoveImage = () => {
    setAttachedImage(null);
  };

  // ★ 이미지와 메시지 함께 전송
  const handleSendWithImage = () => {
    const text = inputValue.trim();
    const hasImage = !!attachedImage;

    if (!text && !hasImage) return;

    if (!onSendMessage) return;

    // ★ 스마트 스크롤 활성화
    pendingSmartScrollRef.current = true;

    const imageDataUrl = hasImage ? attachedImage!.dataUrl : undefined;

    // 답장: 해당 에이전트만 응답
    if (replyingTo && replyingTo.role !== 'user') {
      onSendMessage(text || '(이미지)', { targetAgentRole: replyingTo.role, imageUrl: imageDataUrl });
      setReplyingTo(null);
    } else {
      onSendMessage(text || '(이미지)', { imageUrl: imageDataUrl });
    }

    setInputValue('');
    setAttachedImage(null);
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
  };

  const handleSend = () => {
    // 이미지가 첨부된 경우 handleSendWithImage로 위임
    if (attachedImage) {
      handleSendWithImage();
      return;
    }

    const text = inputValue.trim();
    if (!text) return;

    if (onSendMessage) {
      // ★ 스마트 스크롤 활성화 — 첫 에이전트 응답에서 유저 메시지 위치로 스크롤
      pendingSmartScrollRef.current = true;

      // 답장: 해당 에이전트만 응답
      if (replyingTo && replyingTo.role !== 'user') {
        onSendMessage(text, { targetAgentRole: replyingTo.role });
        setReplyingTo(null);
      } else {
        onSendMessage(text);
      }
      setInputValue('');
      // textarea 높이 리셋
      if (inputRef.current) {
        inputRef.current.style.height = 'auto';
      }
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
    // ESC 더블 탭: 토론 즉시 중단
    if (e.key === 'Escape') {
      const now = Date.now();
      const lastEsc = lastEscTimeRef.current;
      lastEscTimeRef.current = now;

      if (isDebating && now - lastEsc < 500) {
        // 더블 ESC 감지 → 토론 중단
        e.preventDefault();
        if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
          const convId = conversationId || '';
          console.log('[Discussion] ESC double-tap → stopping discussion');
          wsInstance.send(JSON.stringify({
            action: 'stop_debate',
            conversation_id: convId,
          }));
          useConversationStore.getState().setProcessingStatus('⏹️ 토론 중단 중...');
        }
        return;
      }

      // 단일 ESC: 답장 바 닫기
      if (replyingTo) {
        e.preventDefault();
        setReplyingTo(null);
        return;
      }
      return;
    }

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

    if (e.key === 'Enter' && !e.shiftKey && !(e as any).nativeEvent?.isComposing) {
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

  // Start discussion handler
  const handleStartDiscussion = () => {
    if (!wsInstance || wsInstance.readyState !== WebSocket.OPEN) {
      console.error('[Discussion] WebSocket not connected');
      return;
    }
    if (isDebating) return;

    // Guard: ensure conversationId is set
    const convId = conversationId || `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    if (!conversationId) {
      useConversationStore.getState().setConversationId(convId);
    }

    const topic = inputValue.trim() || '이 주제에 대해 토론해봅시다';

    console.log('[Discussion] Starting:', { topic, conversationId: convId });

    // ★ 토론 주제를 사용자 메시지로 채팅에 추가 (대화 흐름에서 계속 보이게)
    useConversationStore.getState().addMessage({
      id: `msg_user_disc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      conversationId: convId,
      senderType: 'user',
      agentName: 'user',
      content: `🗣️ **토론 시작**: ${topic}`,
      timestamp: new Date(),
    });

    wsInstance.send(JSON.stringify({
      action: 'start_debate',
      topic,
      conversation_id: convId,
    }));

    setInputValue('');
    useConversationStore.getState().setProcessingStatus('🗣️ 토론 시작 중...');
  };

  return (
    <>
      <main className={`flex-1 flex flex-col min-w-0 min-h-0 ${
        isDark ? 'bg-slate-900' : 'bg-white'
      }`}>
        {/* ★ Discussion Topic Banner — 스크롤 영역 밖에 항상 고정 */}
        {isDebating && currentDiscussion && (
          <div className={`flex-shrink-0 px-4 py-2.5 border-b ${
            isDark
              ? 'bg-slate-900/95 border-slate-700/50 backdrop-blur-sm'
              : 'bg-white/95 border-amber-200 backdrop-blur-sm'
          }`}>
            <div className="flex items-center gap-2 max-w-input mx-auto">
              <span className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold ${
                isDark
                  ? 'bg-amber-900/30 text-amber-300'
                  : 'bg-amber-50 text-amber-700'
              }`}>
                <span className="material-symbols-outlined text-sm">forum</span>
                토론 진행 중
              </span>
              <div className={`flex-1 min-w-0 px-3 py-1 rounded-lg text-sm font-medium truncate ${
                isDark
                  ? 'bg-slate-800 text-slate-200'
                  : 'bg-amber-50/50 text-slate-700'
              }`}>
                <span className={`text-xs ${isDark ? 'text-amber-400' : 'text-amber-500'}`}>주제:</span>{' '}
                {currentDiscussion.topic}
              </div>
              <span className={`px-2 py-1 rounded-lg text-[10px] font-bold tracking-wider flex-shrink-0 ${
                isDark
                  ? 'bg-amber-900/30 text-amber-400'
                  : 'bg-amber-100 text-amber-600'
              }`}>
                R{discussionRound}/{currentDiscussion.num_rounds}
              </span>
            </div>
          </div>
        )}

        {/* Chat Stream Area */}
        <div ref={scrollContainerRef} className={`flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-2 no-scrollbar min-h-0 ${
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

            // 1) agentRole 필드 직접 사용 (가장 정확)
            // 2) agents 배열에서 name으로 role 조회
            // 3) 폴백: user → 'user', agent → 'manager'
            let role: string;
            if ((message as any).role) {
              role = (message as any).role;
            } else if (message.agentRole) {
              role = message.agentRole;
            } else {
              const agentByName = agents.find(a => a.name === message.agentName);
              role = agentByName?.role || (isUser ? 'user' : 'manager');
            }

            const name = (message as any).name || message.agentName || (isUser ? '나' : 'Unknown');

            return (
              <MessageBubble
                key={message.id}
                role={role as MessageRole}
                name={name}
                content={message.content}
                isCode={false}
                isUser={isUser}
                messageId={message.id}
                replyTo={(message as any).replyTo as ReplyInfo | undefined}
                imageUrl={(message as any).imageUrl as string | undefined}
                onReply={() => {
                  setReplyingTo({
                    id: message.id,
                    name: isUser ? '나' : name,
                    content: message.content,
                    role: role,
                  });
                  inputRef.current?.focus();
                }}
              />
            );
          })}

          {/* Discussion Round Divider — 라운드 전환 표시 */}
          {isDebating && currentDiscussion && (
            <div className="flex justify-center">
              <span className={`px-4 py-1 rounded-full text-[10px] font-bold tracking-widest ${
                isDark
                  ? 'bg-amber-900/30 text-amber-400 border border-amber-800/30'
                  : 'bg-amber-50 text-amber-600 border border-amber-200'
              }`}>
                라운드 {discussionRound}/{currentDiscussion.num_rounds}
              </span>
            </div>
          )}

          {/* Discussion Messages (live in chat stream) */}
          {discussionMessages.map((dMsg, idx) => (
            <MessageBubble
              key={`disc_${dMsg.discussion_id}_${idx}`}
              role={dMsg.agent_role as MessageRole}
              name={dMsg.agent_name}
              content={dMsg.content}
              isCode={false}
              isUser={false}
            />
          ))}

          {/* Discussion Active Indicator — stays in scroll area */}
          {isDebating && (
            <div className="flex justify-center">
              <div className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs ${
                isDark ? 'bg-slate-800 text-slate-400' : 'bg-slate-100 text-slate-500'
              }`}>
                <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                토론 진행 중...
              </div>
            </div>
          )}

          {/* 스크롤 끝 여유 — 하단 UI 요소에 의해 메시지가 가려지지 않도록 */}
          <div ref={messagesEndRef} className="h-2" />
        </div>

        {/* Status & Typing — pinned above input */}
        {(processingStatus || isTyping) && (
          <div className={`px-4 pb-1 flex justify-center ${
            isDark ? 'text-slate-400' : 'text-slate-500'
          }`}>
            <div className="flex items-center gap-1.5 text-xs">
              {processingStatus && !isTyping && (
                <>{processingStatus}</>
              )}
              {isTyping && <TypingIndicator agentName={typingAgentName} />}
            </div>
          </div>
        )}

        {/* Input Section */}
        <footer className="px-4 pb-3 pt-0">
          {/* Agent Working Bar — 입력창 바로 위, footer 내부에 배치 */}
          <AgentWorkingBar />
          {/* Reply Bar — above input */}
          {replyingTo && (
            <div className={`max-w-input mx-auto mb-1 flex items-center gap-2 px-3 py-1.5 rounded-xl border ${
              isDark 
                ? 'bg-slate-800 border-slate-700' 
                : 'bg-slate-50 border-slate-200'
            }`}>
              <span className="material-symbols-outlined text-xs text-primary">reply</span>
              <div className="flex-1 min-w-0 flex items-center gap-1.5">
                <span className="text-xs font-bold text-primary flex-shrink-0">
                  {replyingTo.name}
                </span>
                <span className={`text-[11px] truncate ${
                  isDark ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  {replyingTo.content.slice(0, 40)}{replyingTo.content.length > 40 ? '...' : ''}
                </span>
              </div>
              <button
                onClick={() => setReplyingTo(null)}
                className={`p-0.5 rounded flex-shrink-0 ${
                  isDark ? 'text-slate-500 hover:text-slate-300' : 'text-slate-400 hover:text-slate-600'
                }`}
              >
                <span className="material-symbols-outlined text-sm">close</span>
              </button>
            </div>
          )}
          {/* ★ 이미지 미리보기 — 입력창 위 */}
          {attachedImage && (
            <div className={`max-w-input mx-auto mb-1 flex items-center gap-2 px-3 py-2 rounded-xl border ${
              isDark
                ? 'bg-slate-800 border-slate-700'
                : 'bg-slate-50 border-slate-200'
            }`}>
              <div className="relative flex-shrink-0">
                <img
                  src={attachedImage.dataUrl}
                  alt="preview"
                  className="w-14 h-14 object-cover rounded-lg border"
                />
                <button
                  onClick={handleRemoveImage}
                  className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center text-xs shadow-md hover:bg-red-600"
                >
                  ×
                </button>
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-medium truncate ${
                  isDark ? 'text-slate-300' : 'text-slate-600'
                }`}>
                  {attachedImage.fileName}
                </p>
                <p className={`text-[10px] ${
                  isDark ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  이미지 첨부됨
                </p>
              </div>
            </div>
          )}
          {/* ★ 숨겨진 파일 입력 */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageSelect}
            className="hidden"
          />
          <div 
            ref={inputContainerRef}
            className={`relative max-w-input mx-auto border rounded-xl px-1.5 py-1.5 shadow-lg flex items-end gap-1 ${
              isDark 
                ? 'bg-slate-800 border-slate-700' 
                : 'bg-white border-slate-200'
            }`}
          >
            {/* 왼쪽 버튼 그룹 — 동일 높이 h-10 통일 */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className={`h-10 w-10 flex items-center justify-center rounded-lg transition-colors flex-shrink-0 ${
                isDark 
                  ? 'text-slate-500 hover:text-slate-300 hover:bg-slate-700' 
                  : 'text-slate-400 hover:text-primary hover:bg-slate-50'
              }`}
              title="이미지 첨부"
            >
              <span className="material-symbols-outlined text-xl">attach_file</span>
            </button>
            <button
              onClick={handleStartDiscussion}
              disabled={isDebating}
              className={`h-10 px-2.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap flex items-center justify-center gap-1 flex-shrink-0 ${
                isDebating
                  ? isDark
                    ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                    : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                  : isDark
                    ? 'bg-amber-900/30 text-amber-400 hover:bg-amber-900/50 border border-amber-800/30'
                    : 'bg-amber-50 text-amber-600 hover:bg-amber-100 border border-amber-200'
              }`}
              title={isDebating ? '토론 진행 중...' : '체인형 토론 시작'}
            >
              {isDebating ? (
                <>
                  <span className="material-symbols-outlined text-xs animate-spin">progress_activity</span>
                  토론중
                </>
              ) : (
                <>
                  <span>🗣️</span>
                  토론
                </>
              )}
            </button>
            {/* textarea */}
            <div className="flex-1 relative min-w-0">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyPress}
                rows={1}
                className={`w-full bg-transparent border-none outline-none focus:ring-0 font-medium resize-none overflow-y-auto py-2.5 ${
                  isDark 
                    ? 'text-slate-100 placeholder-slate-500' 
                    : 'text-slate-900 placeholder-slate-400'
                }`}
                style={{ maxHeight: '120px' }}
                placeholder="메시지를 입력하세요... (@멘션 · #C-YYMMDD-NNN 과거 대화 참조)"
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
            {/* 전송 버튼 */}
            <button 
              onClick={handleSend}
              className={`h-10 w-10 text-white rounded-xl hover:brightness-110
                         active:scale-95 transition-all flex items-center justify-center flex-shrink-0 ${
                            isDark ? 'bg-slate-600' : 'bg-primary'
                          }`}
            >
              <span className="material-symbols-outlined text-xl">send</span>
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
