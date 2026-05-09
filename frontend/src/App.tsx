import React, { useState, useEffect } from 'react';
import { useConversationStore } from './store';
import { api } from './api';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import ConversationArchive from './components/ConversationArchive';
import ArchiveView from './components/ArchiveView';
import AdminSettings from './components/AdminSettings';
import DiscussionPanel from './components/DiscussionPanel';
import TaskPanel from './components/TaskPanel';
import Header from './components/Header';
import MobileSidebar from './components/MobileSidebar';
import ErrorBoundary from './components/ErrorBoundary';
import { useTheme } from './hooks/useTheme';
import { getFallbackAgents } from './agentConfig';

const App: React.FC = () => {
  const [activeAgentId, setActiveAgentId] = useState('manager');
  
  // Mobile sidebar state
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  
  // Discussion state (local state)
  const [isDiscussionOpen, setIsDiscussionOpen] = useState(false);
  const [activeDiscussionId, setActiveDiscussionId] = useState<string | null>(null);
  
  // Theme
  const { isDark } = useTheme();

  // Get store actions and state
  const {
    conversationId,
    setConversationId,
    setConnected,
    setWsInstance,
    addMessage,
    setProcessingStatus,
    addAgentResponse,
    activeTab,
    wsInstance,
    isTaskPanelOpen,
    setTaskPanelOpen,
    startTaskExecution,
    addTaskStep,
    completeTaskExecution,
    failTaskExecution,
    setIsDebating,
    setCurrentDiscussion,
    addDiscussionMessage,
    setDiscussionRound,
    clearDiscussion,
    loadRecentMessages,
    isAppReady,
    setIsAppReady,
    // Agent working bar
    setWorkingAgents,
    updateAgentStep,
    removeWorkingAgent,
    clearWorkingAgents,
  } = useConversationStore();

  // Fetch agents, settings, and recent messages on mount
  useEffect(() => {
    const initApp = async () => {
      try {
        // Load all data in parallel
        const [agentsData, settingsData] = await Promise.all([
          api.getAgents().catch(err => {
            console.error('[App] Failed to fetch agents:', err);
            return null;
          }),
          api.getTeamSettings().catch(err => {
            console.error('[App] Failed to fetch team settings:', err);
            return null;
          }),
        ]);

        if (agentsData && agentsData.agents && agentsData.agents.length > 0) {
          useConversationStore.getState().setAgents(agentsData.agents);
          console.log('[App] Loaded agents:', agentsData.agents.length);
        } else {
          // ★ 폴백: 백엔드 실패 시 agentConfig DEFAULTS 사용
          const fallbackAgents = getFallbackAgents();
          useConversationStore.getState().setAgents(fallbackAgents);
          console.warn('[App] Backend unavailable — using fallback agents:', fallbackAgents.length);
        }
        if (settingsData) {
          useConversationStore.getState().setTeamSettings(settingsData);
          console.log('[App] Loaded team settings:', settingsData);
        }

        // Load recent conversation messages
        await useConversationStore.getState().loadRecentMessages();
      } catch (err) {
        console.error('[App] Init error:', err);
      } finally {
        setIsAppReady(true);
      }
    };

    initApp();
  }, []);

  
  // Initialize WebSocket connection on mount (auto-reconnect with backoff)
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectAttempt = 0;
    const MAX_RECONNECT_ATTEMPTS = 10;
    const BASE_DELAY_MS = 1000;

    const connect = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}`;

        console.log(`[WebSocket] Connecting (attempt ${reconnectAttempt + 1})...`);
        ws = new WebSocket(`${wsUrl}/ws`);

        ws.onopen = () => {
          console.log('[WebSocket] Connected successfully');
          setConnected(true);
          setWsInstance(ws!);
          reconnectAttempt = 0; // Reset on successful connect

          // Only generate new conversationId if not already restored from DB
          const currentConvId = useConversationStore.getState().conversationId;
          if (!currentConvId) {
            const newConvId = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            setConversationId(newConvId);
          }
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('[WebSocket] Message received:', data);

            if (data.error && !data.type) {
              console.error('[WebSocket] Backend error:', data.error);
              setProcessingStatus(`❌ ${data.error}`);
              addMessage({
                id: `msg_error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                conversationId: conversationId,
                senderType: 'system',
                agentName: 'system',
                content: `⚠️ 오류: ${data.error}`,
                timestamp: new Date(),
              });
              return;
            }

            if (data.type === 'status') {
              setProcessingStatus(data.message || data.status);
            } else if (data.type === 'agents_thinking') {
              // ★ 에이전트 작업 시작 — WorkingBar 표시
              const agents = (data.agents || []).map((a: any) => ({
                id: a.id,
                name: a.name,
                role: a.role,
                status: 'thinking' as const,
              }));
              setWorkingAgents(agents);
              console.log('[WorkingBar] Agents thinking:', agents.map((a: any) => a.name).join(', '));
            } else if (data.type === 'agent_step') {
              console.log('[Tool Use] Step:', data.agent_name, data.step?.type, data.step?.tool_name || '');
              setProcessingStatus(
                data.step?.type === 'tool_call'
                  ? `🔧 ${data.agent_name}: ${data.step.tool_name} 실행 중...`
                  : data.step?.type === 'thinking'
                  ? `💭 ${data.agent_name}: 분석 중...`
                  : data.step?.type === 'tool_result'
                  ? `✅ ${data.agent_name}: ${data.step.tool_name} 완료`
                  : `⏳ ${data.agent_name}: 처리 중...`
              );
              // ★ WorkingBar 상태 업데이트
              updateAgentStep(
                data.agent_id,
                data.step?.type || 'thinking',
                data.step?.tool_name,
              );
            } else if (data.type === 'agent_done') {
              // ★ 에이전트 작업 완료 — WorkingBar에서 제거
              removeWorkingAgent(data.agent_id);
              console.log('[WorkingBar] Agent done:', data.agent_name);
            } else if (data.type === 'agent_response') {
              const responseContent = data.content || data.response || '';
              addAgentResponse(data.agent_id, {
                agentId: data.agent_id,
                agentName: data.agent_name,
                agentRole: data.agent_role || data.agent_id,
                content: responseContent,
                timestamp: new Date(),
              });

              addMessage({
                id: `msg_${Date.now()}_${Math.random()}`,
                conversationId: conversationId,
                senderType: 'agent',
                agentName: data.agent_name,
                agentRole: data.agent_role || data.agent_id,
                content: responseContent,
                timestamp: new Date(),
              });
            } else if (data.type === 'discussion_mode') {
              console.log('[Discussion] Mode activated:', data.discussion_id);
            } else if (data.type === 'discussion_start') {
              setIsDebating(true);
              setCurrentDiscussion({
                discussion_id: data.discussion_id,
                topic: data.topic,
                num_rounds: data.num_rounds,
                current_round: 1,
                current_agent_index: 0,
                status: 'active',
                summary: null,
                participants: data.participants || [],
              });
              setProcessingStatus(`🗣️ 토론 시작: ${data.topic}`);
            } else if (data.type === 'discussion_round_change') {
              setDiscussionRound(data.round);
              setProcessingStatus(`🗣️ 토론 라운드 ${data.round}/${data.total_rounds}`);
            } else if (data.type === 'discussion_message') {
              addDiscussionMessage({
                discussion_id: data.discussion_id,
                agent_id: data.agent_id,
                agent_name: data.agent_name,
                agent_role: data.agent_role,
                content: data.content,
                round: data.round,
                message_index: data.message_index,
              });
              setProcessingStatus(`🗣️ ${data.agent_name} 발언 완료`);
            } else if (data.type === 'discussion_end') {
              const statusEmoji = data.status === 'completed'
                ? '✅'
                : data.status === 'cancelled'
                  ? '⏹️'
                  : '❌';

              // ★ 토론 메시지를 일반 메시지로 영구 저장 (라이브로 이미 표시된 내용을 대화 기록에 남김)
              const store = useConversationStore.getState();
              const discMsgs = store.discussionMessages;
              if (discMsgs.length > 0) {
                // 이미 라이브로 discussionMessages에 표시 중이므로,
                // clearDiscussion 전에 일반 messages로 이관하여 대화 기록에 영구 보존
                for (const dMsg of discMsgs) {
                  addMessage({
                    id: `msg_disc_${dMsg.discussion_id}_${dMsg.message_index}`,
                    conversationId: conversationId,
                    senderType: 'agent',
                    agentName: dMsg.agent_name,
                    agentRole: dMsg.agent_role,
                    content: dMsg.content,
                    timestamp: new Date(),
                  });
                }
              }

              if (data.summary) {
                addMessage({
                  id: `msg_disc_end_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                  conversationId: conversationId,
                  senderType: 'agent',
                  agentName: 'manager',
                  content: `${statusEmoji} **토론 ${data.status === 'cancelled' ? '중단' : '요약'}**\n\n${data.summary}`,
                  timestamp: new Date(),
                });
              }
              clearDiscussion();
              setProcessingStatus(
                data.status === 'completed'
                  ? '✅ 토론이 완료되었습니다.'
                  : data.status === 'cancelled'
                    ? '⏹️ 토론이 중단되었습니다.'
                    : '❌ 토론이 중단되었습니다.'
              );
            } else if (data.type === 'discussion_stopped') {
              console.log('[Discussion] Stop confirmed for:', data.conversation_id);
            } else if (data.type === 'archive_updated') {
              console.log('[Archive] Updated:', data.title, data.category);
              window.dispatchEvent(
                new CustomEvent('archive_updated', {
                  detail: {
                    conversation_id: data.conversation_id,
                    title: data.title,
                    category: data.category,
                    tags: data.tags,
                  },
                })
              );
            } else if (data.type === 'conversation_closed') {
              // ★ 새 대화: 백엔드에서 기존 대화 종료 완료 → 프론트엔드 리셋
              console.log('[App] Conversation closed by server, resetting:', data.old_conversation_id);
              useConversationStore.getState().resetConversation();
            } else if (data.type === 'DISCUSSION_STARTED') {
              setActiveDiscussionId(data.discussion_id);
              setIsDiscussionOpen(true);
            } else if (data.type === 'DISCUSSION_MESSAGE') {
              // 레거시 토론 메시지
            } else if (data.type === 'DISCUSSION_ENDED') {
              setIsDiscussionOpen(false);
              setActiveDiscussionId(null);
            } else if (data.type === 'task_start') {
              const store = useConversationStore.getState();
              store.startTaskExecution(
                data.agent_id,
                data.agent_name,
                data.task,
              );
              console.log('[Task] Started:', data.task);
            } else if (data.type === 'task_step') {
              const store = useConversationStore.getState();
              store.addTaskStep(data.agent_id, {
                type: data.step.type,
                content: data.step.content,
                tool_name: data.step.tool_name,
                tool_args: data.step.tool_args,
                success: data.step.success,
              });
            } else if (data.type === 'task_complete') {
              const store = useConversationStore.getState();
              store.completeTaskExecution(data.agent_id, data.final_response);
              addMessage({
                id: `msg_task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                conversationId: conversationId,
                senderType: 'agent',
                agentName: data.agent_name,
                content: `✅ **업무 완료**: ${data.task}\n\n${data.final_response}`,
                timestamp: new Date(),
              });
              console.log('[Task] Complete:', data.agent_name);
            } else if (data.type === 'task_error') {
              const store = useConversationStore.getState();
              store.failTaskExecution(data.agent_id, data.error);
              console.error('[Task] Error:', data.error);
            }
          } catch (error) {
            console.error('[WebSocket] Failed to parse message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error);
          setConnected(false);
        };

        ws.onclose = () => {
          console.log('[WebSocket] Disconnected');
          setConnected(false);
          setWsInstance(null);

          // Auto-reconnect with exponential backoff
          if (reconnectAttempt < MAX_RECONNECT_ATTEMPTS) {
            const delay = Math.min(BASE_DELAY_MS * Math.pow(2, reconnectAttempt), 30000);
            reconnectAttempt++;
            console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttempt}/${MAX_RECONNECT_ATTEMPTS})`);
            reconnectTimer = setTimeout(connect, delay);
          } else {
            console.warn('[WebSocket] Max reconnect attempts reached. Refresh to reconnect.');
          }
        };
      } catch (error) {
        console.error('[WebSocket] Failed to initialize:', error);
      }
    };

    connect();

    // Cleanup on unmount
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Mount once — conversationId is read from closure, not a reconnect trigger
 
  const handleSendMessage = async (message: string, options?: { targetAgentRole?: string; imageUrl?: string }) => {
    if (!wsInstance || wsInstance.readyState !== WebSocket.OPEN) {
      console.error('[App] WebSocket not connected');
      return;
    }
  
    try {
      const msgId = `msg_user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      // Add user message to store for immediate display
      addMessage({
        id: msgId,
        conversationId: conversationId,
        senderType: 'user',
        agentName: 'user',
        content: message,
        timestamp: new Date(),
        type: options?.imageUrl ? 'image' : 'text',
        imageUrl: options?.imageUrl,
      });

      // Send via WebSocket using the action format backend expects
      const payload: Record<string, unknown> = {
        action: 'chat',
        content: message,
        conversation_id: conversationId,
        sender_id: 'user',
        timestamp: new Date().toISOString(),
      };

      // 답장: 특정 에이전트만 응답하도록 타겟 지정
      if (options?.targetAgentRole) {
        payload.target_agent_role = options.targetAgentRole;
      }

      // ★ 이미지 첨부 — base64 data URL을 전송
      if (options?.imageUrl) {
        payload.image_data = options.imageUrl;
      }
  
      wsInstance.send(JSON.stringify(payload));
      console.log('[App] Message sent:', message, 
        options?.targetAgentRole ? `(target: ${options.targetAgentRole})` : '',
        options?.imageUrl ? '(with image)' : ''
      );
    } catch (error) {
      console.error('[App] Failed to send message:', error);
    }
  };
 
  const handleTabChange = (tab: 'dashboard' | 'archive' | 'settings') => {
    useConversationStore.getState().setActiveTab(tab);
  };

  const handleNewConversation = () => {
    if (!wsInstance || wsInstance.readyState !== WebSocket.OPEN) {
      console.error('[App] WebSocket not connected for new conversation');
      return;
    }

    // 백엔드에 기존 대화 종료 + 아카이빙 요청
    const currentConvId = useConversationStore.getState().conversationId;
    if (currentConvId) {
      wsInstance.send(JSON.stringify({
        action: 'new_conversation',
        conversation_id: currentConvId,
      }));
      console.log('[App] New conversation requested, closing:', currentConvId);
    } else {
      // conversationId 없으면 그냥 리셋
      useConversationStore.getState().resetConversation();
    }
  };

  const handleExecuteTask = (
    agentId: string,
    agentName: string,
    agentRole: string,
    soulPrompt: string,
    task: string,
  ) => {
    if (!wsInstance || wsInstance.readyState !== WebSocket.OPEN) {
      console.error('[App] WebSocket not connected for task execution');
      return;
    }
    wsInstance.send(JSON.stringify({
      action: 'execute_task',
      task,
      agent_id: agentId,
      agent_name: agentName,
      agent_role: agentRole,
      soul_prompt: soulPrompt,
    }));
    console.log('[App] Task dispatched to agent:', agentName, '-', task);
  };

  // Full-page loading screen while initializing
  if (!isAppReady) {
    return (
      <div className={`flex h-screen w-full items-center justify-center font-body ${
        isDark ? 'bg-slate-950 text-slate-100' : 'bg-surface-bright text-on-surface'
      }`}>
        <div className="flex flex-col items-center gap-3">
          <span className="material-symbols-outlined animate-spin text-4xl text-primary">
            progress_activity
          </span>
          <span className="text-sm text-slate-500">불러오는 중...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`
      flex h-screen w-full font-body overflow-hidden
      ${isDark 
        ? 'bg-slate-950 text-slate-100' 
        : 'bg-surface-bright text-on-surface'
      }
    `}>
      {/* Mobile Sidebar */}
      <MobileSidebar
        isOpen={isMobileSidebarOpen}
        onClose={() => setIsMobileSidebarOpen(false)}
        activeAgentId={activeAgentId}
        onAgentSelect={(id) => setActiveAgentId(id)}
      />

      {/* Left Sidebar - Navigation (Desktop/Tablet only) */}
      <Sidebar
        activeAgentId={activeAgentId}
        onAgentSelect={(id) => setActiveAgentId(id)}
      />

      {/* Main Content - Tab-based */}
      {activeTab === 'dashboard' ? (
        <div className="flex-1 flex min-h-0">
          {/* Center Area: Header + ChatWindow */}
          <div className="flex-1 flex flex-col min-w-0 min-h-0">
            {/* Header */}
            <Header
              status="syncing"
              activeTab="dashboard"
              onTabChange={handleTabChange}
              onMenuClick={() => setIsMobileSidebarOpen(true)}
              onNewConversation={handleNewConversation}
            />

            {/* Chat Stream */}
            <ErrorBoundary>
              <ChatWindow onSendMessage={handleSendMessage} />
            </ErrorBoundary>
          </div>

          {/* Right Panel - Task Panel or Conversation Archive */}
          {isTaskPanelOpen ? (
            <div className="w-80 flex-shrink-0 hidden lg:block">
              <TaskPanel
                onClose={() => setTaskPanelOpen(false)}
                onExecuteTask={handleExecuteTask}
              />
            </div>
          ) : (
            <div className="hidden lg:flex flex-col">
              {/* Task Panel Toggle Button */}
              <button
                onClick={() => setTaskPanelOpen(true)}
                className="m-2 px-3 py-2 rounded-lg bg-slate-800 border border-slate-700
                  text-slate-300 hover:bg-slate-700 hover:text-white transition-colors
                  text-xs font-medium flex items-center gap-1.5 whitespace-nowrap"
                title="업무 지시 패널 열기"
              >
                <span>⚡</span>
                <span>업무 지시</span>
              </button>
              <ConversationArchive />
            </div>
          )}
        </div>
      ) : activeTab === 'archive' ? (
        <ArchiveView />
      ) : activeTab === 'settings' ? (
        <AdminSettings />
      ) : null}

      {/* Discussion Panel */}
      {isDiscussionOpen && activeDiscussionId && (
        <DiscussionPanel
          projectId={conversationId || 'default'}
          discussionId={activeDiscussionId}
          onClose={() => {
            setIsDiscussionOpen(false);
            setActiveDiscussionId(null);
          }}
        />
      )}

      {/* Mobile Floating Button */}
      <div className="fixed bottom-10 right-10 lg:hidden">
        <button className={`
          w-14 h-14 rounded-full shadow-xl
          flex items-center justify-center hover:scale-105 transition-all
          ${isDark
            ? 'bg-slate-600 text-white'
            : 'bg-primary text-white'
          }
        `}>
          <span className="material-symbols-outlined">analytics</span>
        </button>
      </div>
    </div>
  );
};

export default App;
