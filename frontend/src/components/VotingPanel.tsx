import React, { useState } from 'react';
import { useConversationStore } from '../store';
import { api } from '../api';
import { DebateResult } from '../types';
import { useTheme } from '../hooks/useTheme';
import { getAgentConfig, getRoleTailwindClass } from '../agentConfig';

interface VotingPanelProps {
  consensusPercentage?: number;
  activeContext?: {
    title: string;
    description: string;
  };
  stats?: {
    cpu?: number;
    tokens?: number;
  };
}

const VotingPanel: React.FC<VotingPanelProps> = ({
  consensusPercentage = 82,
  activeContext = {
    title: '현재 활성 프로젝트 없음',
    description: '채팅에서 명령을 내리면 에이전트들이 컨텍스트를 생성합니다.',
  },
  stats = {
    cpu: 24,
    tokens: 1.2,
  },
}) => {
  const [activeTab, setActiveTab] = useState<'vote' | 'debate' | 'stats'>('vote');
  const agentResponses = useConversationStore((state) => state.agentResponses);
  const agents = useConversationStore((state) => state.agents);
  const isConnected = useConversationStore((state) => state.isConnected);
  const processingStatus = useConversationStore((state) => state.processingStatus);
  const { isDark } = useTheme();

  // Debate state
  const [debateTopic, setDebateTopic] = useState('');
  const [debateMode, setDebateMode] = useState('debate');
  const [debateRounds, setDebateRounds] = useState(2);
  const [isDebating, setIsDebating] = useState(false);
  const [debateResult, setDebateResult] = useState<DebateResult | null>(null);
  const [debateError, setDebateError] = useState<string | null>(null);

  const handleStartDebate = async () => {
    if (!debateTopic.trim()) {
      setDebateError('토론 주제를 입력해주세요.');
      return;
    }

    setIsDebating(true);
    setDebateError(null);
    setDebateResult(null);

    try {
      const agentIds = agents.map(a => a.id);
      const result = await api.startDebate(debateTopic, agentIds, debateRounds, debateMode);
      setDebateResult(result);
    } catch (error) {
      setDebateError(error instanceof Error ? error.message : '토론 시작 실패');
    } finally {
      setIsDebating(false);
    }
  };

  // Color map for debate messages — single source: agentConfig
  const getAgentColor = (agentName: string): string => {
    const agent = agents.find(a => a.name === agentName || a.display_name === agentName);
    if (agent) return getAgentConfig(agent.id, agents).color;
    return '#6B7280';
  };

  return (
    <aside className={`hidden lg:flex flex-col w-panel border-l ${
      isDark 
        ? 'bg-slate-900 border-slate-800' 
        : 'bg-white border-slate-100'
    }`}>
      <div className="p-6">
        <h3 className={`font-headline font-bold text-lg mb-1 text-2xl ${
          isDark ? 'text-slate-100' : 'text-slate-900'
        }`}>
          운영 허브
        </h3>
        <p className={`text-xs mb-6 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
          에이전트 투표, 토론, 시스템 통계를 한눈에 확인하세요
        </p>

        {/* Tabs */}
        <div className={`flex rounded-lg p-1 mb-6 ${
          isDark ? 'bg-slate-800' : 'bg-slate-100'
        }`}>
          <button
            onClick={() => setActiveTab('vote')}
            className={`flex-1 rounded-md py-2 text-[10px] font-bold uppercase tracking-wider transition-all ${
              activeTab === 'vote'
                ? isDark
                  ? 'bg-slate-700 shadow-sm text-slate-300'
                  : 'bg-white shadow-sm text-primary'
                : isDark
                  ? 'text-slate-500 hover:text-slate-300'
                  : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            투표
          </button>
          <button
            onClick={() => setActiveTab('debate')}
            className={`flex-1 rounded-md py-2 text-[10px] font-bold uppercase tracking-wider transition-all ${
              activeTab === 'debate'
                ? isDark
                  ? 'bg-slate-700 shadow-sm text-slate-300'
                  : 'bg-white shadow-sm text-primary'
                : isDark
                  ? 'text-slate-500 hover:text-slate-300'
                  : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            토론
          </button>
          <button
            onClick={() => setActiveTab('stats')}
            className={`flex-1 rounded-md py-2 text-[10px] font-bold uppercase tracking-wider transition-all ${
              activeTab === 'stats'
                ? isDark
                  ? 'bg-slate-700 shadow-sm text-slate-300'
                  : 'bg-white shadow-sm text-primary'
                : isDark
                  ? 'text-slate-500 hover:text-slate-300'
                  : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            통계
          </button>
        </div>

        {/* 투표 탭 */}
        {activeTab === 'vote' && (
          <div className="space-y-4">
            {/* 연결 상태 */}
            <div className={`flex items-center gap-2 text-xs font-bold px-3 py-2 rounded-lg ${
              isConnected 
                ? isDark ? 'bg-emerald-900/30 text-emerald-400' : 'bg-emerald-50 text-emerald-700'
                : isDark ? 'bg-red-900/30 text-red-400' : 'bg-red-50 text-red-600'
            }`}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-400'}`} />
              {isConnected ? '백엔드 연결됨' : '연결 끊김'}
            </div>

            {/* 합의 상태 */}
            <div>
              <div className="flex justify-between items-end mb-2">
                <span className={`text-[10px] font-bold uppercase tracking-wider ${
                  isDark ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  합의 상태
                </span>
                <span className={`text-xs font-bold ${
                  isDark ? 'text-emerald-400' : 'text-emerald-600'
                }`}>
                  {consensusPercentage}% 조화
                </span>
              </div>
              <div className={`h-1.5 w-full rounded-full overflow-hidden flex ${
                isDark ? 'bg-slate-800' : 'bg-slate-100'
              }`}>
                <div className="bg-slate-500 h-full w-[45%]"></div>
                <div className="bg-emerald-500 h-full w-[25%]"></div>
                <div className="bg-purple-500 h-full w-[12%]"></div>
              </div>
            </div>

            {/* 에이전트 응답 요약 */}
            {Object.keys(agentResponses).length > 0 ? (
              <div>
                <h4 className={`text-[10px] font-bold uppercase tracking-widest mb-3 ${
                  isDark ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  에이전트 응답 ({Object.keys(agentResponses).length}명)
                </h4>
                <div className="space-y-2">
                  {Object.entries(agentResponses).map(([agentId, response]) => {
                    const agent = agents.find(a => a.id === agentId);
                    const colorClass = getRoleTailwindClass(agent?.role || '', isDark);
                    return (
                      <div key={agentId} className={`p-3 rounded-lg border ${colorClass}`}>
                        <p className="text-[10px] font-bold uppercase tracking-wider mb-1">
                          {response.agentName}
                        </p>
                        <p className="text-[10px] leading-relaxed line-clamp-2">
                          {response.content.slice(0, 80)}…
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className={`text-center py-6 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                <span className="material-symbols-outlined text-3xl block mb-2">how_to_vote</span>
                <p className="text-xs font-medium mb-1">아직 투표가 없습니다</p>
                <p className="text-[11px] leading-relaxed">
                  채팅에 메시지를 보내면 에이전트들이<br/>
                  각자의 관점에서 의견을 제시하고 투표합니다
                </p>
              </div>
            )}

            {/* 처리 상태 */}
            {processingStatus && (
              <div className={`text-[10px] text-center py-1 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
                {processingStatus}
              </div>
            )}
          </div>
        )}

        {/* 토론 탭 */}
        {activeTab === 'debate' && (
          <div className="space-y-4">
            {/* 주제 입력 */}
            <div>
              <label className={`block text-[10px] font-bold uppercase tracking-wider mb-2 ${
                isDark ? 'text-slate-500' : 'text-slate-400'
              }`}>
                토론 주제
              </label>
              <textarea
                value={debateTopic}
                onChange={(e) => setDebateTopic(e.target.value)}
                placeholder="예: 신규 기능의 기술 스택 선정에 대해 토론해 주세요..."
                className={`w-full px-3 py-2 border rounded-lg text-xs resize-none focus:ring-2 focus:ring-primary focus:border-primary ${
                  isDark 
                    ? 'bg-slate-800 border-slate-700 text-slate-100 placeholder-slate-500'
                    : 'border-slate-200 bg-white text-slate-900 placeholder-slate-400'
                }`}
                rows={3}
                disabled={isDebating}
              />
            </div>

            {/* 설정 */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className={`block text-[10px] font-bold uppercase tracking-wider mb-1 ${
                  isDark ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  방식
                </label>
                <select
                  value={debateMode}
                  onChange={(e) => setDebateMode(e.target.value)}
                  className={`w-full px-2 py-1.5 border rounded-lg text-xs focus:ring-2 focus:ring-primary ${
                    isDark 
                      ? 'bg-slate-800 border-slate-700 text-slate-100'
                      : 'border-slate-200 bg-white text-slate-900'
                  }`}
                  disabled={isDebating}
                >
                  <option value="debate">토론</option>
                  <option value="brainstorm">브레인스토밍</option>
                  <option value="consensus">합의</option>
                </select>
              </div>
              <div>
                <label className={`block text-[10px] font-bold uppercase tracking-wider mb-1 ${
                  isDark ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  라운드
                </label>
                <select
                  value={debateRounds}
                  onChange={(e) => setDebateRounds(Number(e.target.value))}
                  className={`w-full px-2 py-1.5 border rounded-lg text-xs focus:ring-2 focus:ring-primary ${
                    isDark 
                      ? 'bg-slate-800 border-slate-700 text-slate-100'
                      : 'border-slate-200 bg-white text-slate-900'
                  }`}
                  disabled={isDebating}
                >
                  <option value={1}>1</option>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                </select>
              </div>
            </div>

            {/* 시작 버튼 */}
            <button
              onClick={handleStartDebate}
              disabled={isDebating || !debateTopic.trim()}
              className={`w-full py-2.5 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                isDebating || !debateTopic.trim()
                  ? isDark 
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                    : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                  : isDark
                    ? 'bg-slate-600 text-white hover:bg-slate-500 active:scale-95'
                    : 'bg-primary text-white hover:brightness-110 active:scale-95'
              }`}
            >
              {isDebating ? (
                <>
                  <span className="animate-spin">⏳</span>
                  에이전트들이 토론 중...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-sm">play_arrow</span>
                  토론 시작
                </>
              )}
            </button>

            {/* 에러 */}
            {debateError && (
              <div className={`p-3 border rounded-lg text-xs ${
                isDark 
                  ? 'bg-red-900/30 border-red-800 text-red-300'
                  : 'bg-red-50 border-red-100 text-red-600'
              }`}>
                ❌ {debateError}
              </div>
            )}

            {/* 결과 */}
            {debateResult && (
              <div className="space-y-3">
                <div className={`border-t pt-3 ${isDark ? 'border-slate-700' : 'border-slate-100'}`}>
                  <h4 className={`text-[10px] font-bold uppercase tracking-widest mb-2 ${
                    isDark ? 'text-slate-500' : 'text-slate-400'
                  }`}>
                    토론 결과 ({debateResult.messages.length}개 메시지)
                  </h4>
                  
                  {/* 라운드별 메시지 */}
                  {Array.from({ length: debateResult.rounds }, (_, i) => i + 1).map(round => (
                    <div key={round} className="mb-3">
                      <p className={`text-[9px] font-bold mb-1 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>Round {round}</p>
                      {debateResult.messages
                        .filter(m => m.round === round)
                        .map((msg, idx) => {
                          const agentColor = getAgentColor(msg.agent);
                          return (
                            <div 
                              key={idx} 
                              className="p-2 rounded-lg mb-1 text-[10px] border"
                              style={{ 
                                borderColor: `${agentColor}20`,
                                backgroundColor: `${agentColor}10`
                              }}
                            >
                              <span className="font-bold" style={{ color: agentColor }}>
                                [{msg.agent}]
                              </span>
                              <p className={`mt-0.5 line-clamp-3 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>{msg.content}</p>
                            </div>
                          );
                        })}
                    </div>
                  ))}

                  {/* 최종 요약 */}
                  {debateResult.final_summary && (
                    <div className={`p-3 border rounded-lg ${
                      isDark 
                        ? 'bg-emerald-900/30 border-emerald-800'
                        : 'bg-emerald-50 border-emerald-100'
                    }`}>
                      <p className={`text-[9px] font-bold uppercase mb-1 ${
                        isDark ? 'text-emerald-400' : 'text-emerald-600'
                      }`}>최종 요약</p>
                      <p className={`text-[10px] leading-relaxed ${
                        isDark ? 'text-emerald-300' : 'text-emerald-700'
                      }`}>
                        {debateResult.final_summary}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 안내 */}
            {!debateResult && !isDebating && (
              <div className={`text-center py-4 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                <span className="material-symbols-outlined text-3xl block mb-2">forum</span>
                <p className="text-xs font-medium mb-1">토론을 시작해 보세요</p>
                <p className="text-[11px] leading-relaxed">
                  주제를 입력하면 AI 팀원들이 다양한 관점에서<br/>
                  심도 있는 토론을 진행합니다
                </p>
              </div>
            )}
          </div>
        )}

        {/* 통계 탭 */}
        {activeTab === 'stats' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3">
              <div className={`p-4 rounded-xl border ${
                isDark 
                  ? 'bg-slate-800 border-slate-700'
                  : 'bg-slate-50 border-slate-100'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-[10px] font-bold uppercase ${
                    isDark ? 'text-slate-500' : 'text-slate-400'
                  }`}>CPU 사용량</span>
                  <span className={`text-xs font-bold ${isDark ? 'text-slate-200' : 'text-slate-900'}`}>{stats.cpu}%</span>
                </div>
                <div className={`w-full h-1 rounded-full ${isDark ? 'bg-slate-700' : 'bg-slate-200'}`}>
                  <div className="bg-primary h-full rounded-full" style={{ width: `${stats.cpu}%` }} />
                </div>
              </div>

              <div className={`p-4 rounded-xl border ${
                isDark 
                  ? 'bg-slate-800 border-slate-700'
                  : 'bg-slate-50 border-slate-100'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-[10px] font-bold uppercase ${
                    isDark ? 'text-slate-500' : 'text-slate-400'
                  }`}>API 토큰</span>
                  <span className={`text-xs font-bold ${isDark ? 'text-slate-200' : 'text-slate-900'}`}>{stats.tokens}M</span>
                </div>
                <div className={`w-full h-1 rounded-full ${isDark ? 'bg-slate-700' : 'bg-slate-200'}`}>
                  <div className="bg-purple-500 h-full rounded-full" style={{ width: '65%' }} />
                </div>
              </div>

              <div className={`p-4 rounded-xl border ${
                isDark 
                  ? 'bg-slate-800 border-slate-700'
                  : 'bg-slate-50 border-slate-100'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-[10px] font-bold uppercase ${
                    isDark ? 'text-slate-500' : 'text-slate-400'
                  }`}>에이전트 응답</span>
                  <span className={`text-xs font-bold ${isDark ? 'text-slate-200' : 'text-slate-900'}`}>{Object.keys(agentResponses).length}명</span>
                </div>
                <div className={`w-full h-1 rounded-full ${isDark ? 'bg-slate-700' : 'bg-slate-200'}`}>
                  <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${Object.keys(agentResponses).length * 25}%` }} />
                </div>
              </div>
            </div>

            <div className="mt-4">
              <h4 className={`text-[10px] font-bold uppercase tracking-widest mb-3 ${
                isDark ? 'text-slate-500' : 'text-slate-400'
              }`}>활성 컨텍스트</h4>
              <div className={`border p-4 rounded-xl ${
                isDark 
                  ? 'bg-slate-800 border-slate-700'
                  : 'bg-slate-50 border-slate-100'
              }`}>
                <p className={`text-xs font-bold mb-1 ${isDark ? 'text-slate-400' : 'text-primary'}`}>{activeContext.title}</p>
                <p className={`text-[10px] leading-normal ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{activeContext.description}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};

export default VotingPanel;
