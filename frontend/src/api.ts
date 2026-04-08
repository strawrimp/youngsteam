import { 
  Agent, 
  ModelStats, 
  VotingResult, 
  ArchivedConversation, 
  ConversationDetail, 
  DebateResult, 
  TeamSettings,
  InviteSuggestionRequest,
  InviteSuggestionResponse,
  AcceptInviteRequest,
  RejectInviteRequest,
  AgentMentionRequest,
  AgentMentionResponse,
  Vote,
  VotingStatus,
} from './types';

// Build API base URL dynamically using current host
const API_BASE = `http://${window.location.hostname}:8000`;

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

  // ==================== Archive API ====================

  // Get archived conversations list
  async getArchivedConversations(
    limit: number = 50,
    offset: number = 0
  ): Promise<{ status: string; conversations: ArchivedConversation[]; total: number }> {
    const response = await fetch(
      `${API_BASE}/api/archive/conversations?limit=${limit}&offset=${offset}`
    );
    if (!response.ok) throw new Error('Failed to fetch archived conversations');
    return response.json();
  },

  // Get specific conversation detail
  async getConversationDetail(
    conversationId: string
  ): Promise<{ status: string; conversation: ConversationDetail }> {
    const response = await fetch(
      `${API_BASE}/api/archive/conversations/${conversationId}`
    );
    if (!response.ok) throw new Error('Failed to fetch conversation detail');
    return response.json();
  },

  // Search archived conversations
  async searchConversations(
    query: string,
    limit: number = 20
  ): Promise<{ status: string; query: string; conversations: ArchivedConversation[]; count: number }> {
    const response = await fetch(
      `${API_BASE}/api/archive/search?q=${encodeURIComponent(query)}&limit=${limit}`
    );
    if (!response.ok) throw new Error('Failed to search conversations');
    return response.json();
  },

  // Delete archived conversation
  async deleteConversation(conversationId: string): Promise<{ status: string; message: string }> {
    const response = await fetch(
      `${API_BASE}/api/archive/conversations/${conversationId}`,
      { method: 'DELETE' }
    );
    if (!response.ok) throw new Error('Failed to delete conversation');
    return response.json();
  },

  // ==================== Team Settings API ====================

  // Get team settings
  async getTeamSettings(): Promise<TeamSettings> {
    const response = await fetch(`${API_BASE}/api/settings/team`);
    if (!response.ok) throw new Error('Failed to fetch team settings');
    return response.json();
  },

  // Update team settings
  async updateTeamSettings(data: Partial<TeamSettings>): Promise<TeamSettings> {
    const response = await fetch(`${API_BASE}/api/settings/team`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update team settings');
    return response.json();
  },

  // ==================== Agent CRUD API ====================

  // Update agent
  async updateAgent(id: string, data: Partial<Agent>): Promise<Agent> {
    const response = await fetch(`${API_BASE}/api/agents/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update agent');
    return response.json();
  },

  // Create agent
  async createAgent(data: {
    name: string;
    role: string;
    display_name?: string;
    emoji?: string;
    badge_text?: string;
    icon?: string;
    color?: string;
  }): Promise<Agent> {
    const response = await fetch(`${API_BASE}/api/agents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create agent');
    return response.json();
  },

  // Delete agent
  async deleteAgent(id: string): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE}/api/agents/${id}`, {
      method: 'DELETE' }
    );
    if (!response.ok) throw new Error('Failed to delete agent');
    return response.json();
  },

  // ==================== Debate API ====================

  // Start debate
  async startDebate(
    topic: string,
    agentIds?: string[],
    numRounds: number = 2,
    mode: string = 'debate'
  ): Promise<DebateResult> {
    const response = await fetch(`${API_BASE}/api/debate/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic,
        agent_ids: agentIds,
        num_rounds: numRounds,
        mode,
      }),
    });
    if (!response.ok) throw new Error('Failed to start debate');
    return response.json();
  },

  // ==================== Invite System API ====================

  // Suggest invite based on message analysis
  async suggestInvite(
    request: InviteSuggestionRequest
  ): Promise<InviteSuggestionResponse> {
    const response = await fetch(`${API_BASE}/api/agents/suggest-invite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error('Failed to suggest invite');
    return response.json();
  },

  // Accept invite suggestion
  async acceptInvite(request: AcceptInviteRequest): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE}/api/agents/accept-invite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error('Failed to accept invite');
    return response.json();
  },

  // Reject invite suggestion
  async rejectInvite(request: RejectInviteRequest): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE}/api/agents/reject-invite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error('Failed to reject invite');
    return response.json();
  },

  // Mention agent with @ syntax
  async mentionAgent(request: AgentMentionRequest): Promise<AgentMentionResponse> {
    const response = await fetch(`${API_BASE}/api/agents/mention`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error('Failed to mention agent');
    return response.json();
  },

  // ==================== Voting System API ====================

  // Start a voting session
  async startVotingSession(data: {
    project_id: string;
    discussion_id: string;
    topic: string;
    candidates: string[];
    agent_ids: string[];
  }): Promise<{ status: string; discussion_id: string; topic: string }> {
    const response = await fetch(`${API_BASE}/api/votes/session/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to start voting session');
    return response.json();
  },

  // Cast a vote
  async castVote(data: {
    discussion_id: string;
    agent_id: string;
    choice: string;
    reasoning?: string;
  }): Promise<Vote> {
    const response = await fetch(`${API_BASE}/api/votes/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to cast vote');
    return response.json();
  },

  // Complete voting session
  async completeVotingSession(data: {
    discussion_id: string;
    manager_agent_id?: string;
  }): Promise<VotingResult> {
    const response = await fetch(`${API_BASE}/api/votes/session/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to complete voting session');
    return response.json();
  },

  // Get voting status
  async getVotingStatus(discussionId: string): Promise<VotingStatus> {
    const response = await fetch(`${API_BASE}/api/votes/status/${discussionId}`);
    if (!response.ok) throw new Error('Failed to get voting status');
    return response.json();
  },

  // Get votes by discussion
  async getVotesByDiscussion(discussionId: string): Promise<Vote[]> {
    const response = await fetch(`${API_BASE}/api/votes/${discussionId}`);
    if (!response.ok) throw new Error('Failed to get votes');
    return response.json();
  },

  // Get vote results
  async getVoteResults(discussionId: string): Promise<{
    discussion_id: string;
    total_votes: number;
    results: Record<string, { count: number; reasoning: string[] }>;
  }> {
    const response = await fetch(`${API_BASE}/api/votes/${discussionId}/results`);
    if (!response.ok) throw new Error('Failed to get vote results');
    return response.json();
  },
};
