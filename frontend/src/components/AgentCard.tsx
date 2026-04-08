import React from 'react';
import { Agent, AgentResponse } from '../types';

interface AgentCardProps {
  agent: Agent;
  response?: AgentResponse;
  isTyping?: boolean;
}

const AGENT_COLORS: Record<string, string> = {
  manager: '#4E7EBE',
  developer: '#4A9B6F',
  designer: '#7C6BA8',
  researcher: '#D4A055',
};

const AGENT_EMOJIS: Record<string, string> = {
  manager: '👔',
  developer: '💻',
  designer: '🎨',
  researcher: '📚',
};

const AGENT_LABELS: Record<string, string> = {
  manager: '관리자 (CEO)',
  developer: '개발자',
  designer: '디자이너',
  researcher: '연구원',
};

export const AgentCard: React.FC<AgentCardProps> = ({ agent, response, isTyping }) => {
  const agentColor = AGENT_COLORS[agent.role] || '#64748b';
  const agentEmoji = AGENT_EMOJIS[agent.role] || '🤖';
  const agentLabel = AGENT_LABELS[agent.role] || agent.role;
  const hasResponse = !!response;

  return (
    <div className="glass-card hover-lift animate-fade-in-up dark:bg-slate-700/50 bg-white">
      {/* Agent Header */}
      <div className="flex items-start gap-md mb-md">
        {/* Avatar */}
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl flex-shrink-0 shadow-md"
          style={{ backgroundColor: agentColor }}
        >
          {agentEmoji}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <h4 className="text-base font-semibold dark:text-slate-100 text-slate-900 mb-xs">
            {agent.name}
          </h4>
          <p className="text-xs dark:text-slate-400 text-slate-600">{agentLabel}</p>
        </div>
      </div>

      {/* Status Indicator */}
      <div className="flex items-center gap-sm mb-md">
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            isTyping ? 'bg-blue-500 animate-pulse' : hasResponse ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'
          }`}
        />
        <span className={`text-xs font-medium ${hasResponse ? 'text-emerald-600 dark:text-emerald-400' : 'dark:text-slate-400 text-slate-600'}`}>
          {isTyping ? '타이핑 중...' : hasResponse ? '✓ 응답 완료' : '○ 대기 중'}
        </span>
      </div>

      {/* Response Preview */}
      {hasResponse && response && (
        <div className="mt-md pt-md border-t dark:border-slate-600 border-slate-200 animate-fade-in">
          <p className="text-xs dark:text-slate-300 text-slate-700 line-clamp-3 leading-relaxed">
            {response.content.substring(0, 120)}
            {response.content.length > 120 ? '...' : ''}
          </p>
          <p className="text-xs dark:text-slate-500 text-slate-500 mt-xs">
            {response.timestamp.toLocaleTimeString('ko-KR', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>
      )}
    </div>
  );
};
