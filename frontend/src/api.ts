import { Agent, ModelStats, VotingResult } from './types';

const API_BASE = 'http://localhost:8000';

export const api = {
  // Health check
  async getHealth() {
    const response = await fetch(`${API_BASE}/health`);
    return response.json();
  },

  // Get all agents
  async getAgents(): Promise<{ agents: Agent[] }> {
    const response = await fetch(`${API_BASE}/api/agents`);
    if (!response.ok) throw new Error('Failed to fetch agents');
    return response.json();
  },

  // Get model usage statistics
  async getModelStats(): Promise<ModelStats> {
    const response = await fetch(`${API_BASE}/api/stats/models`);
    if (!response.ok) throw new Error('Failed to fetch model stats');
    return response.json();
  },

  // Reset model statistics
  async resetModelStats() {
    const response = await fetch(`${API_BASE}/api/stats/models/reset`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to reset stats');
    return response.json();
  },

  // Start voting
  async startVoting(topic: string, candidates: string[], conversationId: string): Promise<VotingResult> {
    const response = await fetch(`${API_BASE}/api/voting/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic,
        candidates,
        conversation_id: conversationId,
      }),
    });
    if (!response.ok) throw new Error('Failed to start voting');
    return response.json();
  },

  // Get voting result
  async getVotingResult(votingId: string): Promise<VotingResult> {
    const response = await fetch(`${API_BASE}/api/voting/${votingId}/result`);
    if (!response.ok) throw new Error('Failed to fetch voting result');
    return response.json();
  },
};
