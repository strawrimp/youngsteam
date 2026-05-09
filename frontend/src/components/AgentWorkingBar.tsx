import React, { useEffect, useState } from 'react';
import { useConversationStore } from '../store';
import { getAgentConfig } from '../agentConfig';
import { WorkingAgent } from '../types';
import { useTheme } from '../hooks/useTheme';

/**
 * AgentWorkingBar — 입력창 위에 고정 표시되는 에이전트 작업 상태 바
 *
 * 각 에이전트의 실시간 진행 상태를 보여줍니다:
 * - 💭 생각 중 (thinking)
 * - 🔧 도구 사용 중 (tool_call) — 도구명 표시
 * - ✅ 완료 (done) — 2초 후 페이드아웃
 */
const AgentWorkingBar: React.FC = () => {
  const workingAgents = useConversationStore((state) => state.workingAgents);
  const { isDark } = useTheme();

  // 완료된 에이전트 중 일정 시간 경과 후 숨김 처리
  const [hiddenIds, setHiddenIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const doneAgents = workingAgents.filter(
      (a) => a.status === 'done' && a.doneAt && !hiddenIds.has(a.id)
    );
    if (doneAgents.length === 0) return;

    const timers = doneAgents.map((a) =>
      setTimeout(() => {
        setHiddenIds((prev) => new Set(prev).add(a.id));
      }, 2500)
    );

    return () => timers.forEach(clearTimeout);
  }, [workingAgents, hiddenIds]);

  // workingAgents가 변경되면 hiddenIds 초기화 (새 메시지 전송 시)
  useEffect(() => {
    const hasThinking = workingAgents.some((a) => a.status !== 'done');
    if (hasThinking) {
      setHiddenIds(new Set());
    }
  }, [workingAgents]);

  // 표시할 에이전트 (숨김 처리된 것 제외)
  const visibleAgents = workingAgents.filter((a) => !hiddenIds.has(a.id));
  const doneCount = visibleAgents.filter((a) => a.status === 'done').length;
  const totalCount = visibleAgents.length;
  const allDone = totalCount > 0 && doneCount === totalCount;

  // 모두 완료 후 0.5초 뒤 숨김
  const [shouldHide, setShouldHide] = useState(false);
  useEffect(() => {
    if (allDone && totalCount > 0) {
      const t = setTimeout(() => setShouldHide(true), 500);
      return () => clearTimeout(t);
    }
    setShouldHide(false);
  }, [allDone, totalCount]);

  // 렌더링 가드 — hooks 이후에 처리
  if (visibleAgents.length === 0) return null;
  if (shouldHide) return null;

  return (
    <div className={`px-4 pb-1 pt-1 transition-all duration-300 ${allDone ? 'opacity-40' : 'opacity-100'}`}>
      <div
        className={`max-w-input mx-auto flex items-center gap-1 px-3 py-2 rounded-xl border overflow-x-auto no-scrollbar ${
          isDark
            ? 'bg-slate-800/80 border-slate-700/60'
            : 'bg-slate-50 border-slate-200/80'
        }`}
      >
        {/* 진행 인디케이터 */}
        {!allDone && (
          <span className="material-symbols-outlined text-sm animate-spin text-primary flex-shrink-0">
            progress_activity
          </span>
        )}
        {allDone && (
          <span className="material-symbols-outlined text-sm text-emerald-500 flex-shrink-0">
            check_circle
          </span>
        )}

        {/* 에이전트 목록 */}
        <div className="flex items-center gap-2 min-w-0">
          {visibleAgents.map((agent) => (
            <AgentChip key={agent.id} agent={agent} isDark={isDark} />
          ))}
        </div>
      </div>
    </div>
  );
};

/**
 * 개별 에이전트 칩 — 아바타 + 이름 + 상태
 */
const AgentChip: React.FC<{ agent: WorkingAgent; isDark: boolean }> = ({
  agent,
  isDark,
}) => {
  const config = getAgentConfig(agent.role);
  const isDone = agent.status === 'done';

  // 상태 텍스트 결정
  const getStatusText = () => {
    if (isDone) return '완료';
    if (agent.stepType === 'tool_call') {
      return agent.stepDetail ? `${agent.stepDetail} 실행` : '도구 사용';
    }
    if (agent.stepType === 'tool_result') return '분석 중';
    return '생각 중';
  };

  // 상태 아이콘
  const getStatusIcon = () => {
    if (isDone) return '✓';
    if (agent.stepType === 'tool_call') return '🔧';
    return '💭';
  };

  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs whitespace-nowrap transition-all duration-300 ${
        isDone
          ? isDark
            ? 'bg-emerald-900/20 text-emerald-400'
            : 'bg-emerald-50 text-emerald-600'
          : isDark
            ? 'bg-slate-700/50 text-slate-300'
            : 'bg-white text-slate-600 shadow-sm'
      }`}
    >
      {/* 아바타 (색상 점) */}
      <div
        className="w-4 h-4 rounded flex items-center justify-center flex-shrink-0"
        style={{ backgroundColor: isDone ? '#10B981' : config.color }}
      >
        <span className="text-white" style={{ fontSize: '9px' }}>
          {getStatusIcon()}
        </span>
      </div>

      {/* 이름 */}
      <span className="font-semibold">{agent.name}</span>

      {/* 상태 */}
      <span className={`font-normal ${isDark ? 'text-slate-400' : 'text-slate-400'}`}>
        {getStatusText()}
      </span>
    </div>
  );
};

export default AgentWorkingBar;
