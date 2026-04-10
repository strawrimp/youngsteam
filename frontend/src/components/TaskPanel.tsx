/**
 * TaskPanel - 에이전트에게 업무를 지시하고 실시간 실행 과정을 확인하는 패널
 */

import React, { useState, useRef, useEffect } from 'react';
import { useConversationStore, TaskStep } from '../store';
import { useTheme } from '../hooks/useTheme';

interface TaskPanelProps {
  onClose: () => void;
  onExecuteTask: (agentId: string, agentName: string, agentRole: string, soulPrompt: string, task: string) => void;
}

const STEP_ICONS: Record<string, string> = {
  thinking: '🧠',
  tool_call: '🔧',
  tool_result: '📋',
  response: '✅',
};

const STEP_LABELS: Record<string, string> = {
  thinking: '분석 중',
  tool_call: '도구 호출',
  tool_result: '결과 수신',
  response: '최종 답변',
};

const STEP_COLORS: Record<string, string> = {
  thinking: 'border-slate-400 bg-slate-950/40',
  tool_call: 'border-amber-400 bg-amber-950/40',
  tool_result: 'border-emerald-400 bg-emerald-950/40',
  response: 'border-violet-400 bg-violet-950/40',
};

const TOOL_ICONS: Record<string, string> = {
  web_search: '🌐',
  execute_python: '🐍',
};

function StepCard({ step }: { step: TaskStep }) {
  const [isExpanded, setIsExpanded] = useState(step.type !== 'tool_result');
  const colorClass = STEP_COLORS[step.type] || 'border-slate-600 bg-slate-900/40';
  const icon = STEP_ICONS[step.type] || '•';
  const label = STEP_LABELS[step.type] || step.type;

  return (
    <div className={`rounded-lg border ${colorClass} mb-2 overflow-hidden`}>
      <button
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:opacity-80 transition-opacity"
        onClick={() => setIsExpanded((v) => !v)}
      >
        <span className="text-base">{icon}</span>
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex-1">
          {label}
          {step.tool_name && (
            <span className="ml-2 font-mono text-amber-300">
              {TOOL_ICONS[step.tool_name] || '🔧'} {step.tool_name}
            </span>
          )}
        </span>
        {step.success === false && (
          <span className="text-red-400 text-xs">실패</span>
        )}
        <span className="text-slate-500 text-xs">{isExpanded ? '▲' : '▼'}</span>
      </button>

      {isExpanded && (
        <div className="px-3 pb-3">
          {/* Tool args */}
          {step.tool_args && Object.keys(step.tool_args).length > 0 && (
            <div className="mb-2 text-xs text-slate-400 font-mono bg-black/30 rounded p-2">
              {JSON.stringify(step.tool_args, null, 2)}
            </div>
          )}
          {/* Content */}
          <div className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
            {step.content}
          </div>
        </div>
      )}
    </div>
  );
}

export default function TaskPanel({ onClose, onExecuteTask }: TaskPanelProps) {
  const { isDark } = useTheme();
  const [taskInput, setTaskInput] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const stepsEndRef = useRef<HTMLDivElement>(null);

  const {
    agents,
    taskExecutions,
    activeTaskAgentId,
    isTaskPanelOpen,
  } = useConversationStore();

  const activeExecution = activeTaskAgentId ? taskExecutions[activeTaskAgentId] : null;

  // Auto-scroll to bottom as steps come in
  useEffect(() => {
    stepsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeExecution?.steps.length]);

  // Pick first agent by default
  useEffect(() => {
    if (!selectedAgentId && agents.length > 0) {
      setSelectedAgentId(String(agents[0].id));
    }
  }, [agents]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskInput.trim() || !selectedAgentId) return;

    const agent = agents.find((a) => String(a.id) === selectedAgentId);
    if (!agent) return;

    onExecuteTask(
      String(agent.id),
      agent.name,
      agent.role,
      '', // soul_prompt (optional)
      taskInput.trim(),
    );
    setTaskInput('');
  };

  const agentColor: Record<string, string> = {
    manager: 'text-slate-400',
    developer: 'text-emerald-400',
    designer: 'text-violet-400',
    researcher: 'text-amber-400',
  };

  const agentEmoji: Record<string, string> = {
    manager: '👔',
    developer: '💻',
    designer: '🎨',
    researcher: '🔬',
  };

  const isRunning = activeExecution?.status === 'running';

  return (
    <div className="flex flex-col h-full bg-slate-900 border-l border-slate-700/50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <span className="text-lg">⚡</span>
          <span className="font-semibold text-slate-100 text-sm">업무 지시</span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-200 transition-colors"
        >
          <span className="material-symbols-outlined text-sm">close</span>
        </button>
      </div>

      {/* Task Form */}
      <form onSubmit={handleSubmit} className="px-4 py-3 border-b border-slate-700/50 space-y-3">
        {/* Agent Selector */}
        <div>
          <label className="text-xs text-slate-400 mb-1 block">담당 에이전트</label>
          <div className="flex flex-wrap gap-2">
            {agents.map((agent) => (
              <button
                key={agent.id}
                type="button"
                onClick={() => setSelectedAgentId(String(agent.id))}
                className={`
                  flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
                  border transition-all
                  ${selectedAgentId === String(agent.id)
                    ? 'border-slate-500 bg-slate-500/20 text-slate-300'
                    : 'border-slate-600 bg-slate-800 text-slate-400 hover:border-slate-500'
                  }
                `}
              >
                <span>{agentEmoji[agent.role] || '🤖'}</span>
                <span>{agent.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Task Input */}
        <div>
          <label className="text-xs text-slate-400 mb-1 block">업무 내용</label>
          <textarea
            value={taskInput}
            onChange={(e) => setTaskInput(e.target.value)}
            placeholder="예: 2024년 AI 트렌드를 조사해서 요약해줘&#10;예: 피보나치 수열 1000번째 값을 계산해줘&#10;예: 우리 앱에 필요한 로그인 API 설계를 해줘"
             rows={3}
            disabled={isRunning}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2
              text-sm text-slate-200 placeholder-slate-500
              focus:outline-none focus:border-slate-500
              disabled:opacity-50 resize-none"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                handleSubmit(e as unknown as React.FormEvent);
              }
            }}
          />
          <div className="text-xs text-slate-500 mt-1">Cmd+Enter로 전송</div>
        </div>

        <button
          type="submit"
          disabled={!taskInput.trim() || !selectedAgentId || isRunning}
          className="w-full py-2 rounded-lg text-sm font-semibold
            bg-slate-600 hover:bg-slate-500 text-white
            disabled:opacity-40 disabled:cursor-not-allowed
            transition-colors flex items-center justify-center gap-2"
        >
          {isRunning ? (
            <>
              <span className="animate-spin">⚙️</span>
              <span>업무 수행 중...</span>
            </>
          ) : (
            <>
              <span>⚡</span>
              <span>업무 지시</span>
            </>
          )}
        </button>
      </form>

      {/* Execution Steps */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {!activeExecution ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-sm gap-3 py-12">
            <span className="text-4xl">🤖</span>
            <p className="text-center">
              업무를 지시하면 에이전트가<br />
              웹 검색, 코드 실행으로<br />
              실제 작업을 수행합니다.
            </p>
            <div className="text-xs text-slate-600 text-center mt-2 space-y-1">
              <p>🌐 웹 검색으로 최신 정보 수집</p>
              <p>🐍 코드 작성 및 실행</p>
              <p>📊 데이터 분석 및 보고</p>
            </div>
          </div>
        ) : (
          <div>
            {/* Task header */}
            <div className="mb-3 p-2 bg-slate-800/50 rounded-lg border border-slate-700">
              <div className="text-xs text-slate-400 mb-0.5">
                {agentEmoji[agents.find(a => String(a.id) === activeExecution.agentId)?.role || ''] || '🤖'}{' '}
                {activeExecution.agentName}의 업무
              </div>
              <div className="text-sm text-slate-200 font-medium">{activeExecution.task}</div>
              {activeExecution.status === 'running' && (
                <div className="flex items-center gap-1.5 mt-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse" />
                  <span className="text-xs text-slate-400">진행 중...</span>
                </div>
              )}
              {activeExecution.status === 'complete' && (
                <div className="flex items-center gap-1.5 mt-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span className="text-xs text-emerald-400">완료</span>
                </div>
              )}
              {activeExecution.status === 'error' && (
                <div className="flex items-center gap-1.5 mt-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  <span className="text-xs text-red-400">오류 발생</span>
                </div>
              )}
            </div>

            {/* Steps */}
            {activeExecution.steps.map((step, idx) => (
              <StepCard key={idx} step={step} />
            ))}

            {/* Loading indicator */}
            {isRunning && (
              <div className="flex items-center gap-2 text-slate-400 text-sm mt-2">
                <div className="flex gap-1">
                  <span className="animate-bounce" style={{ animationDelay: '0ms' }}>•</span>
                  <span className="animate-bounce" style={{ animationDelay: '150ms' }}>•</span>
                  <span className="animate-bounce" style={{ animationDelay: '300ms' }}>•</span>
                </div>
                <span className="text-xs">처리 중...</span>
              </div>
            )}

            <div ref={stepsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}
