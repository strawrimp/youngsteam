// API Response Types
export interface Agent {
  id: string;
  name: string;
  role: 'manager' | 'developer' | 'designer' | 'researcher';
  display_name?: string;
  emoji?: string;
  badge_text?: string;
  icon?: string;
  color?: string;
  status?: string;
}

export interface TeamSettings {
  team_name: string;
  team_subtitle: string;
  team_icon: string;
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

// Debate Types
export interface DebateMessage {
  round: number;
  agent: string;
  content: string;
}

export interface DebateResult {
  status: string;
  debate_id: string;
  topic: string;
  mode: string;
  rounds: number;
  message_count: number;
  final_summary: string;
  messages: DebateMessage[];
}

// ==================== Invite System Types ====================

// 초대 제안
export interface InviteSuggestion {
  agent_id: string;
  agent_name: string;
  agent_role: string;
  reason: string;
  confidence: number;
}

// 초대 제안 요청
export interface InviteSuggestionRequest {
  conversation_id: string;
  message: string;
  current_agent_ids: string[];
}

// 초대 제안 응답
export interface InviteSuggestionResponse {
  status: string;
  suggestions: InviteSuggestion[];
  message: string;
}

// 초대 승인 요청
export interface AcceptInviteRequest {
  conversation_id: string;
  agent_id: string;
}

// 초대 거부 요청
export interface RejectInviteRequest {
  conversation_id: string;
  agent_id: string;
  reason?: string;
}

// 에이전트 멘션 요청
export interface AgentMentionRequest {
  conversation_id: string;
  mentioned_agent_id: string;
  message: string;
  context?: string;
}

// 에이전트 멘션 응답
export interface AgentMentionResponse {
  status: string;
  mentioned_agent_id: string;
  agent_name: string;
  message: string;
}

// 멘션 자동완성 아이템
export interface MentionCandidate {
  id: string;
  name: string;
  role: string;
  display_name?: string;
  emoji?: string;
}

// ==================== Voting System Types ====================

// 투표 옵션
export interface VoteCandidate {
  id: string;
  label: string;
  description?: string;
}

// 투표 데이터
export interface Vote {
  id: string;
  discussion_id: string;
  agent_id: string;
  agent_name?: string;
  choice: string;
  reasoning?: string;
  created_at: string;
}

// 투표 세션
export interface VotingSession {
  discussion_id: string;
  project_id: string;
  topic: string;
  candidates: VoteCandidate[];
  eligible_voters: string[];
  votes: Record<string, Vote>;
  status: 'active' | 'completed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  winner?: string;
  is_tiebreaker?: boolean;
}

// 투표 결과
export interface VotingResult {
  discussion_id: string;
  topic: string;
  candidates: string[];
  votes: Record<string, { choice: string; reasoning?: string }>;
  final_decision: string;
  is_tiebreaker: boolean;
  timestamp: string;
  vote_count: number;
  breakdown: Record<string, number>;
}

// 투표 상태
export interface VotingStatus {
  discussion_id: string;
  status: 'active' | 'completed' | 'no_votes' | 'not_found';
  total_votes: number;
  vote_breakdown: Record<string, number>;
}

