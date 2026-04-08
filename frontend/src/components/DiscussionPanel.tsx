import React, { useState, useEffect } from 'react';
import { useConversationStore } from '../store';

interface DiscussionMessage {
  id: string;
  discussionId: string;
  agentId: string;
  agentName: string;
  agentRole: string;
  content: string;
  timestamp: Date;
}

interface DiscussionPanelProps {
  projectId: string;
  discussionId?: string;
  onClose?: () => void;
}

const DiscussionPanel: React.FC<DiscussionPanelProps> = ({
  projectId,
  discussionId,
  onClose,
}) => {
  const [messages, setMessages] = useState<DiscussionMessage[]>([]);
  const [isOpen, setIsOpen] = useState(true);
  const wsInstance = useConversationStore((state) => state.wsInstance);

  const agents = useConversationStore((state) => state.agents);

  useEffect(() => {
    if (!wsInstance) return;

    const handleDiscussionMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'DISCUSSION_MESSAGE' && data.discussionId === discussionId) {
          setMessages((prev) => [...prev, data.message]);
        }
      } catch (error) {
        console.error('Failed to parse discussion message:', error);
      }
    };

    wsInstance.addEventListener('message', handleDiscussionMessage);
    return () => {
      wsInstance.removeEventListener('message', handleDiscussionMessage);
    };
  }, [wsInstance, discussionId]);

  const getAgentInfo = (agentId: string) => {
    const agent = agents.find((a) => a.id === agentId);
    return agent || { name: 'Unknown', role: 'unknown' };
  };

  return (
    <div className="fixed right-0 top-0 bottom-0 w-96 bg-white shadow-xl 
                 transform transition-transform duration-300 ease-in-out
                 z-50 ${isOpen ? 'translate-x-0' : 'translate-x-full'}">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-slate-600">
              forum
            </span>
            <h3 className="text-lg font-semibold text-slate-800">
              사이드 토론
            </h3>
          </div>
          <button
            onClick={() => {
              setIsOpen(false);
              onClose?.();
            }}
            className="text-slate-400 hover:text-slate-600"
          >
            ✕
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-slate-400">
              <span className="material-symbols-outlined text-5xl mb-2">
                chat_bubble
              </span>
              <p className="text-sm">토론 메시지가 없습니다</p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className="bg-slate-50 rounded-lg p-3"
              >
                <div className="flex items-start gap-2 mb-2">
                  <span className="text-2xl">
                    {getAgentInfo(message.agentId).emoji || '🤖'}
                  </span>
                  <div>
                    <div className="font-medium text-sm text-slate-800">
                      {message.agentName}
                    </div>
                    <div className="text-xs text-slate-500">
                      {message.agentRole}
                    </div>
                  </div>
                </div>
                <p className="text-sm text-slate-600 mt-1">
                  {message.content}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Private Label */}
        <div className="px-4 py-2 bg-yellow-50 border-t border-yellow-200">
          <p className="text-xs text-yellow-800 flex items-center gap-1">
            <span className="material-symbols-outlined text-sm">
              lock
            </span>
            에이전트 전용 (사용자에게 비공개)
          </p>
        </div>
      </div>
    </div>
  );
};

export default DiscussionPanel;
