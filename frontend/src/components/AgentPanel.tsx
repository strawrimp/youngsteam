import React, { useEffect } from 'react';
import { useConversationStore } from '../store';
import { api } from '../api';
import { Agent } from '../types';
import styles from './AgentPanel.module.css';

const AGENT_COLORS: Record<string, string> = {
  manager: '#0066cc',
  developer: '#00aa44',
  designer: '#9900ff',
  researcher: '#ff9900',
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
    <div className={styles.agentPanel}>
      <h3 className={styles.title}>에이전트 팀</h3>
      <div className={styles.agentsList}>
        {agents.length === 0 ? (
          <div className={styles.empty}>에이전트 로딩 중...</div>
        ) : (
          agents.map((agent) => {
            const response = agentResponses[agent.id];
            const hasResponse = !!response;

            return (
              <div
                key={agent.id}
                className={`${styles.agentCard} ${hasResponse ? styles.hasResponse : ''}`}
                style={{
                  borderLeftColor: AGENT_COLORS[agent.role],
                }}
              >
                <div className={styles.agentHeader}>
                  <div
                    className={styles.agentBadge}
                    style={{ backgroundColor: AGENT_COLORS[agent.role] }}
                  >
                    {agent.name[0]}
                  </div>
                  <div className={styles.agentInfo}>
                    <div className={styles.agentName}>{agent.name}</div>
                    <div className={styles.agentRole}>
                      {AGENT_LABELS[agent.role] || agent.role}
                    </div>
                  </div>
                </div>

                <div className={styles.statusIndicator}>
                  {hasResponse ? (
                    <span className={styles.statusDone}>✓ 응답 완료</span>
                  ) : (
                    <span className={styles.statusWaiting}>○ 대기 중</span>
                  )}
                </div>

                {hasResponse && (
                  <div className={styles.responsePreview}>
                    <p>{response.content.substring(0, 100)}...</p>
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
