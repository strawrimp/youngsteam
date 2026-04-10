import React, { useState, useEffect } from 'react';
import { useConversationStore } from './store';
import { api } from './api';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import VotingPanel from './components/VotingPanel';
import ArchiveView from './components/ArchiveView';
import AdminSettings from './components/AdminSettings';
import DiscussionPanel from './components/DiscussionPanel';
import TaskPanel from './components/TaskPanel';
import Header from './components/Header';
import MobileSidebar from './components/MobileSidebar';
import ErrorBoundary from './components/ErrorBoundary';
import { useTheme } from './hooks/useTheme';

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
  } = useConversationStore();

  // Fetch agents and team settings on mount
  useEffect(() => {
    // Fetch agents from backend
    api.getAgents()
      .then(data => {
        useConversationStore.getState().setAgents(data.agents);
        console.log('[App] Loaded agents:', data.agents.length);
      })
      .catch(err => {
        console.error('[App] Failed to fetch agents:', err);
      });

    // Fetch team settings
    api.getTeamSettings()
      .then(data => {
        useConversationStore.getState().setTeamSettings(data);
        console.log('[App] Loaded team settings:', data);
      })
      .catch(err => {
        console.error('[App] Failed to fetch team settings:', err);
      });
  }, []);

  
  // Initialize WebSocket connection on mount
  useEffect(() => {
    const initWebSocket = () => {
      try {
        // Use dynamic hostname to support both localhost and deployed environments
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
 
        // Backend runs on port 8001, frontend on port 5173
        // For development: connect to localhost:8001
        // For production: connect to same host on port 8001
        const backendPort = (import.meta.env.VITE_BACKEND_PORT as string) || '8001';
        const wsUrl = `${protocol}//${host}:${backendPort}`;
 
        console.log('[WebSocket] Connecting to:', `${wsUrl}/ws`);
 
        const ws = new WebSocket(`${wsUrl}/ws`);
 
        ws.onopen = () => {
          console.log('[WebSocket] Connected successfully');
          setConnected(true);
          setWsInstance(ws);
 
          // Initialize conversation ID
          if (!conversationId) {
            const newConvId = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            setConversationId(newConvId);
          }
        };
 
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('[WebSocket] Message received:', data);
 
            if (data.type === 'status') {
              setProcessingStatus(data.message || data.status);
            } else if (data.type === 'agent_step') {
              // Tool Use 실시간 단계 스트리밍 (채팅 중 도구 사용 표시)
              console.log('[Tool Use] Step:', data.agent_name, data.step?.type, data.step?.tool_name || '');
              // Store에 임시 상태로 표시 (나중에 agent_response로 덮어씀)
              setProcessingStatus(
                data.step?.type === 'tool_call'
                  ? `🔧 ${data.agent_name}: ${data.step.tool_name} 실행 중...`
                  : data.step?.type === 'thinking'
                  ? `💭 ${data.agent_name}: 분석 중...`
                  : data.step?.type === 'tool_result'
                  ? `✅ ${data.agent_name}: ${data.step.tool_name} 완료`
                  : `⏳ ${data.agent_name}: 처리 중...`
              );
            } else if (data.type === 'agent_response') {
              // Add agent response to store
              addAgentResponse(data.agent_id, {
                agentId: data.agent_id,
                agentName: data.agent_name,
                agentRole: data.agent_id,
                content: data.content,
                timestamp: new Date(),
              });
 
              // Also add to messages for display
              addMessage({
                id: `msg_${Date.now()}_${Math.random()}`,
                conversationId: conversationId,
                senderType: 'agent',
                agentName: data.agent_name,
                content: data.content,
                timestamp: new Date(),
              });
            } else if (data.type === 'DISCUSSION_STARTED') {
              // 토론 시작 알림
              setActiveDiscussionId(data.discussion_id);
              setIsDiscussionOpen(true);
            } else if (data.type === 'DISCUSSION_MESSAGE') {
              // 토론 메시지 수신 (기존 논의)
              // TODO: 토론 메시지 UI 구현 후 여기서 처리
            } else if (data.type === 'DISCUSSION_ENDED') {
              // 토론 종료 알림
              setIsDiscussionOpen(false);
              setActiveDiscussionId(null);
            } else if (data.type === 'task_start') {
              // 에이전트 업무 시작
              const store = useConversationStore.getState();
              store.startTaskExecution(
                data.agent_id,
                data.agent_name,
                data.task,
              );
              console.log('[Task] Started:', data.task);
            } else if (data.type === 'task_step') {
              // 업무 수행 단계 수신
              const store = useConversationStore.getState();
              store.addTaskStep(data.agent_id, {
                type: data.step.type,
                content: data.step.content,
                tool_name: data.step.tool_name,
                tool_args: data.step.tool_args,
                success: data.step.success,
              });
            } else if (data.type === 'task_complete') {
              // 업무 완료
              const store = useConversationStore.getState();
              store.completeTaskExecution(data.agent_id, data.final_response);
              // 결과를 채팅 메시지로도 표시
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
              // 업무 오류
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
        };
      } catch (error) {
        console.error('[WebSocket] Failed to initialize:', error);
      }
    };
 
    initWebSocket();
  }, [conversationId]);
 
  const handleSendMessage = async (message: string) => {
    if (!wsInstance || wsInstance.readyState !== WebSocket.OPEN) {
      console.error('[App] WebSocket not connected');
      return;
    }
  
    try {
      // Add user message to store for immediate display
      addMessage({
        id: `msg_user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        conversationId: conversationId,
        senderType: 'user',
        agentName: 'user',
        content: message,
        timestamp: new Date(),
      });

      // Send via WebSocket using the action format backend expects
      const payload = {
        action: 'chat',
        content: message,
        conversation_id: conversationId,
        sender_id: 'user',
        timestamp: new Date().toISOString(),
      };
  
      wsInstance.send(JSON.stringify(payload));
      console.log('[App] Message sent:', message);
    } catch (error) {
      console.error('[App] Failed to send message:', error);
    }
  };
 
  const handleTabChange = (tab: 'dashboard' | 'archive' | 'settings') => {
    useConversationStore.getState().setActiveTab(tab);
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
            />

            {/* Chat Stream */}
            <ErrorBoundary>
              <ChatWindow onSendMessage={handleSendMessage} />
            </ErrorBoundary>
          </div>

          {/* Right Panel - Task Panel or Voting Panel */}
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
              <VotingPanel />
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
