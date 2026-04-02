import React, { useEffect } from 'react';
import { useConversationStore } from '../store';
import { api } from '../api';
import { Agent } from '../types';

const AGENT_COLORS: Record<string, string> = {
  manager: '#0066CC',
  developer: '#00AA44',
  designer: '#8B5CF6',
  researcher: '#F59E0B',
};

const AGENT_LABELS: Record<string, string> = {
  manager: '관리자 (CEO)',
  developer: '개발자',
  designer: '디자이너',
  researcher: '연구원',
};

export const AgentPanel: React.FC = () => {
  const { agents, setAgents, agentResponses, clearAgentResponses } = useConversationStore();

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
    <div className="flex flex-col h-full bg-white border-r border-neutral-300 overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-neutral-300 px-lg py-md">
        <h3 className="text-lg font-semibold text-neutral-900">에이전트 팀</h3>
      </div>

      {/* Agents list */}
      <div className="flex-1 overflow-y-auto p-lg space-y-md">
        {agents.length === 0 ? (
          <div className="flex items-center justify-center h-full text-center">
            <p className="text-sm text-neutral-600">에이전트 팀을 준비 중입니다.</p>
          </div>
        ) : (
          agents.map((agent) => {
            const response = agentResponses[agent.id];
            const hasResponse = !!response;

            return (
              <div
                key={agent.id}
                className="rounded-sm border border-neutral-300 bg-white p-sm transition-all hover:shadow-sm"
                style={{
                  borderLeftWidth: '4px',
                  borderLeftColor: AGENT_COLORS[agent.role],
                }}
              >
                {/* Agent header */}
                <div className="flex items-start gap-md mb-md">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-white font-semibold text-sm flex-shrink-0"
                    style={{ backgroundColor: AGENT_COLORS[agent.role] }}
                  >
                    {agent.name[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-semibold text-neutral-900">{agent.name}</h4>
                    <p className="text-xs text-neutral-600">
                      {AGENT_LABELS[agent.role] || agent.role}
                    </p>
                  </div>
                </div>

                {/* Status indicator */}
                <div className="flex items-center gap-xs">
                  <span className={`inline-block w-1.5 h-1.5 rounded-full ${hasResponse ? 'bg-success' : 'bg-agent-manager'}`} />
                  <span className={`text-xs font-medium ${hasResponse ? 'text-success' : 'text-neutral-600'}`}>
                    {hasResponse ? '✓ 응답 완료' : '○ 대기 중'}
                  </span>
                </div>

                {/* Response preview */}
                {hasResponse && (
                  <div className="mt-md pt-md border-t border-neutral-200">
                    <p className="text-xs text-neutral-700 truncate">
                      {response.content.substring(0, 100)}
                      {response.content.length > 100 ? '...' : ''}
                    </p>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
