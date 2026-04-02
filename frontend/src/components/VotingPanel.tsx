import React, { useState, useEffect } from 'react';
import { useConversationStore } from '../store';
import { api } from '../api';

export const VotingPanel: React.FC = () => {
  const { votingResults, modelStats, setModelStats } = useConversationStore();
  const [activeTab, setActiveTab] = useState<'voting' | 'stats'>('voting');
  const [statsLoading, setStatsLoading] = useState(false);

  // Load model stats
  const loadStats = async () => {
    setStatsLoading(true);
    try {
      const stats = await api.getModelStats();
      setModelStats(stats);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setStatsLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
    // Refresh stats every 30 seconds
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, [setModelStats]);

  return (
    <div className="flex flex-col h-full bg-white border-l border-neutral-300 overflow-hidden">
      {/* Tabs */}
      <div className="flex-shrink-0 border-b border-neutral-300 flex gap-0">
        <button
          onClick={() => setActiveTab('voting')}
          className={`flex-1 px-lg py-md text-sm font-medium transition-all ${
            activeTab === 'voting'
              ? 'text-agent-manager border-b-2 border-agent-manager'
              : 'text-neutral-600 border-b-2 border-transparent hover:text-neutral-900'
          }`}
        >
          투표
        </button>
        <button
          onClick={() => setActiveTab('stats')}
          className={`flex-1 px-lg py-md text-sm font-medium transition-all ${
            activeTab === 'stats'
              ? 'text-agent-manager border-b-2 border-agent-manager'
              : 'text-neutral-600 border-b-2 border-transparent hover:text-neutral-900'
          }`}
        >
          통계
        </button>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-lg">
        {activeTab === 'voting' && (
          <>
            {votingResults ? (
              <div className="space-y-lg">
                {/* Topic */}
                <div>
                  <h4 className="text-sm font-semibold text-neutral-900 mb-md">주제</h4>
                  <p className="text-base text-neutral-700">{votingResults.topic}</p>
                </div>

                {/* Candidates */}
                <div>
                  <h4 className="text-sm font-semibold text-neutral-900 mb-md">선택지</h4>
                  <div className="space-y-sm">
                    {votingResults.candidates.map((candidate, idx) => (
                      <div key={idx} className="px-md py-sm bg-neutral-50 rounded-sm text-sm text-neutral-700">
                        {idx + 1}. {candidate}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Votes */}
                <div>
                  <h4 className="text-sm font-semibold text-neutral-900 mb-md">투표 결과</h4>
                  <div className="space-y-md">
                    {Object.entries(votingResults.votes).map(([agentId, vote]) => (
                      <div key={agentId} className="border border-neutral-300 rounded-sm p-md">
                        <div className="flex items-center justify-between mb-md">
                          <span className="text-sm font-semibold text-neutral-900">{vote.agentName}</span>
                          <span className="px-sm py-xs bg-neutral-100 rounded-xs text-xs font-medium text-neutral-700">
                            {vote.choice}
                          </span>
                        </div>
                        <p className="text-xs text-neutral-600">
                          {vote.reasoning?.substring(0, 150)}
                          {vote.reasoning && vote.reasoning.length > 150 ? '...' : ''}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-md text-center">
                <p className="text-sm font-medium text-neutral-900">아직 투표 결과가 없습니다</p>
                <p className="text-xs text-neutral-600">
                  투표를 시작하면 결과가 여기 표시됩니다
                </p>
              </div>
            )}
          </>
        )}

        {activeTab === 'stats' && (
          <>
            {statsLoading ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-sm text-neutral-600">통계 로딩 중...</p>
              </div>
            ) : modelStats ? (
              <div className="space-y-lg">
                {/* Strategy Info */}
                <div>
                  <h4 className="text-sm font-semibold text-neutral-900 mb-md">하이브리드 전략</h4>
                  <p className="text-sm text-neutral-700">{modelStats.model_strategy}</p>
                </div>

                {/* Chart */}
                <div>
                  <p className="text-sm font-semibold text-neutral-900 mb-md">모델 사용 분포</p>
                  <div className="flex gap-sm bg-neutral-100 rounded-sm overflow-hidden h-6">
                    {modelStats.stats.v4_percent > 0 && (
                      <div
                        className="bg-agent-manager flex items-center justify-center"
                        style={{ width: `${modelStats.stats.v4_percent}%` }}
                      >
                        {modelStats.stats.v4_percent > 10 && (
                          <span className="text-xs font-semibold text-white">
                            V4: {modelStats.stats.v4_percent.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    )}
                    {modelStats.stats.r1_percent > 0 && (
                      <div
                        className="bg-agent-developer flex items-center justify-center"
                        style={{ width: `${modelStats.stats.r1_percent}%` }}
                      >
                        {modelStats.stats.r1_percent > 10 && (
                          <span className="text-xs font-semibold text-white">
                            R1: {modelStats.stats.r1_percent.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Stats Details */}
                <div className="space-y-sm">
                  <div className="flex justify-between items-center px-md py-sm bg-neutral-50 rounded-sm">
                    <span className="text-sm text-neutral-600">V4 호출</span>
                    <span className="text-sm font-semibold text-neutral-900">{modelStats.stats.v4_count}회</span>
                  </div>
                  <div className="flex justify-between items-center px-md py-sm bg-neutral-50 rounded-sm">
                    <span className="text-sm text-neutral-600">R1 호출</span>
                    <span className="text-sm font-semibold text-neutral-900">{modelStats.stats.r1_count}회</span>
                  </div>
                  <div className="flex justify-between items-center px-md py-sm bg-neutral-50 rounded-sm">
                    <span className="text-sm text-neutral-600">총 호출</span>
                    <span className="text-sm font-semibold text-neutral-900">{modelStats.stats.total}회</span>
                  </div>
                </div>

                {/* Descriptions */}
                <div className="space-y-sm text-xs text-neutral-700">
                  <div>
                    <strong>V4:</strong> {modelStats.description.v4}
                  </div>
                  <div>
                    <strong>R1:</strong> {modelStats.description.r1}
                  </div>
                </div>

                {/* Refresh button */}
                <button onClick={loadStats} className="btn w-full bg-agent-manager text-white">
                  새로고침
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-sm text-neutral-600">통계를 불러올 수 없습니다</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
