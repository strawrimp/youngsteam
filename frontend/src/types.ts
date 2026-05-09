// API Response Types

// Reply context for message threading
export interface ReplyInfo {
  id: string;
  name: string;
  content: string;    // 앞 30자 truncate
  role: string;
}

export interface Agent {
  id: string;
  name: string;
  role: 'manager' | 'developer' | 'designer' | 'researcher' | 'bot';
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
  senderType: 'user' | 'agent' | 'system';
  agentName?: string;
  agentRole?: string;
  content: string;
  timestamp: Date;
  type?: 'text' | 'status' | 'error' | 'image';
  replyTo?: ReplyInfo;
  imageUrl?: string; // base64 data URL or server URL for images
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

// ==================== Agent Response Types ====================

export interface AgentResponse {
  agentId: string;
  agentName: string;
  agentRole: string;
  content: string;
  timestamp: Date;
}

// ==================== Agent Working State ====================

export type AgentStepType = 'thinking' | 'tool_call' | 'tool_result' | 'response';

export interface WorkingAgent {
  id: string;
  name: string;
  role: string;
  status: 'thinking' | 'working' | 'done';
  stepType?: AgentStepType;
  stepDetail?: string;   // 도구명 등 상세 정보
  doneAt?: number;        // 완료 시간 (fadeout용)
}

// ==================== Archive Types ====================

export interface ArchivedConversation {
  id: string;
  title: string;
  started_at: string | null;
  ended_at: string | null;
  message_count: number;
  tags?: string[];
  category?: string;
  summary?: string;
  reference_code?: string;  // #C-YYMMDD-NNN
}

export interface ConversationDetail {
  id: string;
  title: string;
  started_at: string | null;
  ended_at: string | null;
  messages: {
    id: string;
    agent_id: string | null;
    agent_name: string | null;
    content: string;
    created_at: string | null;
    sender_type: string;
    type: string;
  }[];
}

// ==================== Live Discussion Types ====================

export interface DiscussionParticipant {
  agent_id: string;
  agent_name: string;
  agent_role: string;
}

export interface DiscussionInfo {
  discussion_id: string;
  topic: string;
  num_rounds: number;
  current_round: number;
  current_agent_index: number;
  status: 'active' | 'completed' | 'error';
  summary: string | null;
  participants: DiscussionParticipant[];
}

export interface DiscussionMessage {
  discussion_id: string;
  agent_id: string;
  agent_name: string;
  agent_role: string;
  content: string;
  round: number;
  message_index: number;
}

// ==================== Model Stats Types ====================

export interface ModelStats {
  status: string;
  model_strategy: string;
  stats: {
    v4_calls: number;
    r1_calls: number;
    total_calls: number;
    [key: string]: unknown;
  };
  description?: Record<string, string>;
}

