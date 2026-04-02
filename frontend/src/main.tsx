import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'
import './App.css'
import { ChatWindow } from './components/ChatWindow'
import { AgentPanel } from './components/AgentPanel'
import { VotingPanel } from './components/VotingPanel'
import { useConversationStore } from './store'
import { Message as MessageType, AgentResponse } from './types'
import { useEffect } from 'react'

const App: React.FC = () => {
  const {
    setConnected,
    setConversationId,
    addMessage,
    addAgentResponse,
    setProcessingStatus,
  } = useConversationStore();

  useEffect(() => {
    const conversationId = `conv-${Date.now()}`;
    setConversationId(conversationId);

    const ws = new WebSocket(`ws://localhost:8000/ws`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);

        switch (data.type) {
          case 'status':
            setProcessingStatus(data.message || '');
            break;

          case 'agent_response':
            const agentMsg: MessageType = {
              id: `msg-${Date.now()}-${Math.random()}`,
              conversationId,
              senderType: 'agent',
              agentName: data.agent_name,
              content: data.content,
              timestamp: new Date(data.timestamp || Date.now()),
              type: 'text',
            };
            addMessage(agentMsg);

            const response: AgentResponse = {
              agentId: data.agent_id,
              agentName: data.agent_name,
              agentRole: data.agent_name?.toLowerCase() || 'unknown',
              content: data.content,
              timestamp: new Date(data.timestamp || Date.now()),
            };
            addAgentResponse(data.agent_id, response);
            break;

          case 'error':
            const errorMsg: MessageType = {
              id: `msg-${Date.now()}-error`,
              conversationId,
              senderType: 'agent',
              content: `오류: ${data.error || 'Unknown error'}`,
              timestamp: new Date(),
              type: 'error',
            };
            addMessage(errorMsg);
            break;

          default:
            console.log('Unknown message type:', data.type);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      setConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [setConnected, setConversationId, addMessage, addAgentResponse, setProcessingStatus]);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>AI 가상 회사</h1>
        <p>멀티-에이전트 협력 시스템</p>
      </header>

      <div className="app-main">
        <aside className="app-sidebar-left">
          <AgentPanel />
        </aside>

        <main className="app-center">
          <ChatWindow />
        </main>

        <aside className="app-sidebar-right">
          <VotingPanel />
        </aside>
      </div>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
