import React, { useEffect } from 'react';
import { useConversationStore } from '../store';
import { api } from '../api';
import { AgentCard } from './AgentCard';

export const AgentPanel: React.FC = () => {
  const { agents, setAgents, agentResponses } = useConversationStore();

  // Load agents on mount
  useEffect(() => {
    const loadAgents = async () => {
      try {
        const data = await api.getAgents();
        setAgents(data.agents);
      } catch (error) {
        console.error('Failed to load agents:', error);
      }
    };

    loadAgents();
  }, [setAgents]);

  return (
    <div className="flex flex-col h-full glass-panel overflow-hidden animate-fade-in dark:bg-slate-800/50 bg-white/50">
      {/* Header */}
      <div className="flex-shrink-0 border-b dark:border-slate-700 border-slate-200 px-lg py-md dark:bg-slate-800/70 bg-white">
        <h3 className="text-lg font-semibold dark:text-slate-100 text-slate-900">에이전트 팀</h3>
        <p className="text-xs dark:text-slate-400 text-slate-600 mt-xs">{agents.length}명의 팀원이 준비되었습니다</p>
      </div>

      {/* Agents list */}
      <div className="flex-1 overflow-y-auto p-lg space-y-md scrollbar-thin">
        {agents.length === 0 ? (
          <div className="flex items-center justify-center h-full text-center">
            <div className="animate-pulse">
              <div className="text-4xl mb-md">⏳</div>
              <p className="text-sm dark:text-slate-400 text-slate-600">에이전트 팀을 준비 중입니다.</p>
            </div>
          </div>
        ) : (
          agents.map((agent, index) => {
            const response = agentResponses[agent.id];

            return (
              <div
                key={agent.id}
                className="animate-fade-in-up"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <AgentCard
                  agent={agent}
                  response={response}
                  isTyping={false}
                />
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
