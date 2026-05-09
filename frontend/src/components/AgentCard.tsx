import React from 'react';
import { Agent, AgentResponse } from '../types';
import { getAgentConfig } from '../agentConfig';

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
  bot: '#E85D3A',
};

const AGENT_EMOJIS: Record<string, string> = {
  manager: '👔',
  developer: '💻',
  designer: '🎨',
  researcher: '📚',
  bot: '🤖',
};

const AGENT_LABELS: Record<string, string> = {
  manager: '네오 비서실장',
  developer: '아서 개발부장',
  designer: '소피아 디자이너',
  researcher: '루나 연구소장',
  bot: '클로',
};

const AGENT_DESCRIPTIONS: Record<string, string> = {
  manager: '프로젝트 총괄 · 팀 조율 · 의사결정',
  developer: '아키텍처 설계 · 핵심 구현 · 코드 리뷰',
  designer: 'UX 설계 · 비주얼 디자인 · 브랜드 관리',
  researcher: '기술 분석 · 시장 조사 · 인사이트 도출',
  bot: 'Mac Mini 게이트웨이 · 기기 제어 · 실세계 작업 위임',
};

export const AgentCard: React.FC<AgentCardProps> = ({ agent, response, isTyping }) => {
  const agents = undefined; // standalone card doesn't need agents list
  const config = getAgentConfig(agent.id);
  const agentColor = AGENT_COLORS[agent.role] || '#64748b';
  const agentEmoji = AGENT_EMOJIS[agent.role] || '🤖';
  const agentLabel = AGENT_LABELS[agent.role] || agent.role;
  const agentDescription = AGENT_DESCRIPTIONS[agent.role] || config.description || '';
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
          {agentDescription && (
            <p className="text-[11px] dark:text-slate-500 text-slate-400 mt-1 leading-relaxed">
              {agentDescription}
            </p>
          )}
        </div>
      </div>

      {/* Status Indicator */}
      <div className="flex items-center gap-sm mb-md">
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            isTyping ? 'bg-slate-500 animate-pulse' : hasResponse ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'
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
