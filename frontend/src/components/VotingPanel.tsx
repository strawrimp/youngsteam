import React, { useState, useEffect } from 'react';
import { useConversationStore } from '../store';
import { api } from '../api';
import styles from './VotingPanel.module.css';

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
    <div className={styles.votingPanel}>
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'voting' ? styles.active : ''}`}
          onClick={() => setActiveTab('voting')}
        >
          투표
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'stats' ? styles.active : ''}`}
          onClick={() => setActiveTab('stats')}
        >
          통계
        </button>
      </div>

      {activeTab === 'voting' && (
        <div className={styles.tabContent}>
          {votingResults ? (
            <div className={styles.votingContent}>
              <div className={styles.votingTopic}>
                <h4>주제</h4>
                <p>{votingResults.topic}</p>
              </div>

              <div className={styles.candidates}>
                <h4>선택지</h4>
                <div className={styles.candidatesList}>
                  {votingResults.candidates.map((candidate, idx) => (
                    <div key={idx} className={styles.candidateItem}>
                      {idx + 1}. {candidate}
                    </div>
                  ))}
                </div>
              </div>

              <div className={styles.votes}>
                <h4>투표 결과</h4>
                <div className={styles.votesList}>
                  {Object.entries(votingResults.votes).map(([agentId, vote]) => (
                    <div key={agentId} className={styles.voteItem}>
                      <div className={styles.voteHeader}>
                        <span className={styles.agentName}>{vote.agentName}</span>
                        <span className={styles.choice}>{vote.choice}</span>
                      </div>
                      <div className={styles.reasoning}>
                        <p>{vote.reasoning.substring(0, 150)}...</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className={styles.empty}>
              <p>아직 투표 결과가 없습니다</p>
              <p style={{ fontSize: '12px', color: '#999' }}>
                투표를 시작하면 결과가 여기 표시됩니다
              </p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'stats' && (
        <div className={styles.tabContent}>
          {statsLoading ? (
            <div className={styles.empty}>
              <p>통계 로딩 중...</p>
            </div>
          ) : modelStats ? (
            <div className={styles.statsContent}>
              <div className={styles.strategyInfo}>
                <h4>하이브리드 전략</h4>
                <p>{modelStats.model_strategy}</p>
              </div>

              <div className={styles.statsChart}>
                <div className={styles.chartTitle}>모델 사용 분포</div>
                <div className={styles.chartBar}>
                  <div
                    className={styles.v4Bar}
                    style={{
                      width: `${modelStats.stats.v4_percent}%`,
                    }}
                  >
                    {modelStats.stats.v4_percent > 10 && (
                      <span className={styles.barLabel}>
                        V4: {modelStats.stats.v4_percent.toFixed(1)}%
                      </span>
                    )}
                  </div>
                  <div
                    className={styles.r1Bar}
                    style={{
                      width: `${modelStats.stats.r1_percent}%`,
                    }}
                  >
                    {modelStats.stats.r1_percent > 10 && (
                      <span className={styles.barLabel}>
                        R1: {modelStats.stats.r1_percent.toFixed(1)}%
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className={styles.statsDetails}>
                <div className={styles.statItem}>
                  <span className={styles.label}>V4 호출</span>
                  <span className={styles.value}>{modelStats.stats.v4_count}회</span>
                </div>
                <div className={styles.statItem}>
                  <span className={styles.label}>R1 호출</span>
                  <span className={styles.value}>{modelStats.stats.r1_count}회</span>
                </div>
                <div className={styles.statItem}>
                  <span className={styles.label}>총 호출</span>
                  <span className={styles.value}>{modelStats.stats.total}회</span>
                </div>
              </div>

              <div className={styles.descriptions}>
                <div className={styles.desc}>
                  <strong>V4:</strong> {modelStats.description.v4}
                </div>
                <div className={styles.desc}>
                  <strong>R1:</strong> {modelStats.description.r1}
                </div>
              </div>

              <button className={styles.refreshBtn} onClick={loadStats}>
                새로고침
              </button>
            </div>
          ) : (
            <div className={styles.empty}>
              <p>통계를 불러올 수 없습니다</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
