// API Response Types
export interface Agent {
  id: string;
  name: string;
  role: 'manager' | 'developer' | 'designer' | 'researcher';
}

export interface Message {
  id: string;
  conversationId: string;
  senderType: 'user' | 'agent';
  agentName?: string;
  content: string;
  timestamp: Date;
  type?: 'text' | 'status' | 'error';
}

export interface Vote {
  agentId: string;
  agentName: string;
  choice: string;
  reasoning: string;
}

export interface VotingResult {
  conversationId: string;
  topic: string;
  candidates: string[];
  votes: Record<string, Vote>;
  timestamp: string;
  votingId: string;
}

export interface ModelStats {
  status: string;
  model_strategy: string;
  stats: {
    v4_count: number;
    r1_count: number;
    total: number;
    v4_percent: number;
    r1_percent: number;
  };
  description: {
    v4: string;
    r1: string;
    hybrid_selection: string;
  };
}

// WebSocket Message Types
export interface WSMessage {
  type: 'status' | 'agent_response' | 'error' | 'voting_result';
  status?: string;
  message?: string;
  agent_id?: string;
  agent_name?: string;
  content?: string;
  timestamp?: string;
  error?: string;
}

// UI State Types
export interface AgentResponse {
  agentId: string;
  agentName: string;
  agentRole: string;
  content: string;
  timestamp: Date;
}
