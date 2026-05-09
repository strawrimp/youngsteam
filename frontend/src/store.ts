import { create } from 'zustand';
import { 
  Agent, 
  Message, 
  VotingResult, 
  ModelStats, 
  AgentResponse, 
  ArchivedConversation, 
  ConversationDetail, 
  TeamSettings,
  InviteSuggestion,
  DiscussionInfo,
  DiscussionMessage as DiscussionMessageType,
  ReplyInfo,
  WorkingAgent,
  AgentStepType,
} from './types';
import { api } from './api';

// Task execution types
export interface TaskStep {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'response';
  content: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  success?: boolean;
}

export interface TaskExecution {
  agentId: string;
  agentName: string;
  task: string;
  status: 'running' | 'complete' | 'error';
  steps: TaskStep[];
  finalResponse?: string;
  startedAt: Date;
}

interface ConversationStore {
  // Conversation state
  conversationId: string;
  messages: Message[];
  isConnected: boolean;
  isLoading: boolean;
  processingStatus: string;
  isSending: boolean;

  // WebSocket reference
  wsInstance: WebSocket | null;

  // Agent state
  agents: Agent[];
  agentResponses: Record<string, AgentResponse>;

  // Voting state
  votingResults: VotingResult | null;
  isVoting: boolean;

  // Model stats
  modelStats: ModelStats | null;

  // Archive state
  activeTab: 'dashboard' | 'archive' | 'settings';
  archiveConversations: ArchivedConversation[];
  selectedConversation: ConversationDetail | null;
  searchQuery: string;
  archiveLoading: boolean;

  // Team settings
  teamSettings: TeamSettings | null;

  // Invite system state
  inviteSuggestions: InviteSuggestion[];
  isInviteModalOpen: boolean;
  pendingInvites: InviteSuggestion[];

  // Live Discussion state
  isDebating: boolean;
  currentDiscussion: DiscussionInfo | null;
  discussionMessages: DiscussionMessageType[];
  discussionRound: number;

  // Reply state
  replyingTo: ReplyInfo | null;

  // Agent working state (real-time progress bar)
  workingAgents: WorkingAgent[];

  // Message persistence state
  isLoadingMessages: boolean;
  isAppReady: boolean;

  // Current conversation reference code (#C-YYMMDD-NNN)
  currentReferenceCode: string | null;

  // Actions
  setConversationId: (id: string) => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  setConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  setProcessingStatus: (status: string) => void;
  setWsInstance: (ws: WebSocket | null) => void;
  setIsSending: (sending: boolean) => void;

  setAgents: (agents: Agent[]) => void;
  addAgentResponse: (agentId: string, response: AgentResponse) => void;
  clearAgentResponses: () => void;

  setVotingResults: (results: VotingResult) => void;
  setIsVoting: (isVoting: boolean) => void;

  setModelStats: (stats: ModelStats) => void;

  // Archive actions
  setActiveTab: (tab: 'dashboard' | 'archive' | 'settings') => void;
  setArchiveConversations: (conversations: ArchivedConversation[]) => void;
  setSelectedConversation: (conversation: ConversationDetail | null) => void;
  setSearchQuery: (query: string) => void;
  setArchiveLoading: (loading: boolean) => void;

  // Team settings actions
  setTeamSettings: (settings: TeamSettings) => void;

  // Invite actions
  addPendingInvite: (invite: InviteSuggestion) => void;
  removePendingInvite: (agentId: string) => void;
  clearPendingInvites: () => void;

  // Live Discussion actions
  setIsDebating: (debating: boolean) => void;
  setCurrentDiscussion: (info: DiscussionInfo | null) => void;
  addDiscussionMessage: (msg: DiscussionMessageType) => void;
  setDiscussionRound: (round: number) => void;
  clearDiscussion: () => void;

  // Reply actions
  setReplyingTo: (info: ReplyInfo | null) => void;

  // Agent working actions
  setWorkingAgents: (agents: WorkingAgent[]) => void;
  updateAgentStep: (agentId: string, stepType: AgentStepType, stepDetail?: string) => void;
  removeWorkingAgent: (agentId: string) => void;
  clearWorkingAgents: () => void;

  // Message persistence actions
  loadRecentMessages: () => Promise<void>;
  resetConversation: () => void;
  setIsAppReady: (ready: boolean) => void;
  setCurrentReferenceCode: (code: string | null) => void;

  // Task execution state
  taskExecutions: Record<string, TaskExecution>;
  activeTaskAgentId: string | null;
  isTaskPanelOpen: boolean;

  // Task execution actions
  startTaskExecution: (agentId: string, agentName: string, task: string) => void;
  addTaskStep: (agentId: string, step: TaskStep) => void;
  completeTaskExecution: (agentId: string, finalResponse: string) => void;
  failTaskExecution: (agentId: string, error: string) => void;
  setActiveTaskAgentId: (agentId: string | null) => void;
  setTaskPanelOpen: (open: boolean) => void;
  clearTaskExecution: (agentId: string) => void;
}

export const useConversationStore = create<ConversationStore>((set) => ({
  // Initial state
  conversationId: '',
  messages: [],
  isConnected: false,
  isLoading: false,
  processingStatus: '',
  isSending: false,

  wsInstance: null,

  agents: [],
  agentResponses: {},

  votingResults: null,
  isVoting: false,

  modelStats: null,

  // Archive state
  activeTab: 'dashboard',
  archiveConversations: [],
  selectedConversation: null,
  searchQuery: '',
  archiveLoading: false,

  // Team settings
  teamSettings: null,

  // Invite state
  inviteSuggestions: [],
  isInviteModalOpen: false,
  pendingInvites: [],

  // Live Discussion state
  isDebating: false,
  currentDiscussion: null,
  discussionMessages: [],
  discussionRound: 1,

  // Reply state
  replyingTo: null,

  // Agent working state
  workingAgents: [],

  // Message persistence state
  isLoadingMessages: false,
  isAppReady: false,
  currentReferenceCode: null,

  // Actions
  setConversationId: (id: string) => set({ conversationId: id }),
  addMessage: (message: Message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  clearMessages: () => set({ messages: [] }),
  setConnected: (connected: boolean) => set({ isConnected: connected }),
  setLoading: (loading: boolean) => set({ isLoading: loading }),
  setProcessingStatus: (status: string) => set({ processingStatus: status }),
  setWsInstance: (ws: WebSocket | null) => set({ wsInstance: ws }),
  setIsSending: (sending: boolean) => set({ isSending: sending }),

  setAgents: (agents: Agent[]) => set({ agents }),
  addAgentResponse: (agentId: string, response: AgentResponse) =>
    set((state) => ({
      agentResponses: {
        ...state.agentResponses,
        [agentId]: response,
      },
    })),
  clearAgentResponses: () => set({ agentResponses: {} }),

  setVotingResults: (results: VotingResult) => set({ votingResults: results }),
  setIsVoting: (isVoting: boolean) => set({ isVoting }),

  setModelStats: (stats: ModelStats) => set({ modelStats: stats }),

  // Archive actions
  setActiveTab: (tab: 'dashboard' | 'archive' | 'settings') => set({ activeTab: tab }),
  setArchiveConversations: (conversations: ArchivedConversation[]) => 
    set({ archiveConversations: conversations }),
  setSelectedConversation: (conversation: ConversationDetail | null) => 
    set({ selectedConversation: conversation }),
  setSearchQuery: (query: string) => set({ searchQuery: query }),
  setArchiveLoading: (loading: boolean) => set({ archiveLoading: loading }),

  // Team settings actions
  setTeamSettings: (settings: TeamSettings) => set({ teamSettings: settings }),

  // Invite actions
  addPendingInvite: (invite: InviteSuggestion) =>
    set((state) => ({
      pendingInvites: [...state.pendingInvites, invite],
    })),
  removePendingInvite: (agentId: string) =>
    set((state) => ({
      pendingInvites: state.pendingInvites.filter((i) => i.agent_id !== agentId),
    })),
  clearPendingInvites: () => set({ pendingInvites: [] }),

  // Live Discussion actions
  setIsDebating: (debating: boolean) => set({ isDebating: debating }),
  setCurrentDiscussion: (info: DiscussionInfo | null) => set({ currentDiscussion: info }),
  addDiscussionMessage: (msg: DiscussionMessageType) =>
    set((state) => ({
      discussionMessages: [...state.discussionMessages, msg],
    })),
  setDiscussionRound: (round: number) => set({ discussionRound: round }),
  clearDiscussion: () =>
    set({
      isDebating: false,
      currentDiscussion: null,
      discussionMessages: [],
      discussionRound: 1,
    }),

  // Reply actions
  setReplyingTo: (info: ReplyInfo | null) => set({ replyingTo: info }),

  // Agent working actions
  setWorkingAgents: (agents: WorkingAgent[]) => set({ workingAgents: agents }),
  updateAgentStep: (agentId: string, stepType: AgentStepType, stepDetail?: string) =>
    set((state) => ({
      workingAgents: state.workingAgents.map((a) =>
        a.id === agentId
          ? {
              ...a,
              status: stepType === 'response' ? 'done' : stepType === 'tool_call' ? 'working' : 'thinking',
              stepType,
              stepDetail,
              ...(stepType === 'response' ? { doneAt: Date.now() } : {}),
            }
          : a
      ),
    })),
  removeWorkingAgent: (agentId: string) =>
    set((state) => ({
      workingAgents: state.workingAgents.map((a) =>
        a.id === agentId ? { ...a, status: 'done' as const, doneAt: Date.now() } : a
      ),
    })),
  clearWorkingAgents: () => set({ workingAgents: [] }),

  // Message persistence actions
  setIsAppReady: (ready: boolean) => set({ isAppReady: ready }),
  setCurrentReferenceCode: (code: string | null) => set({ currentReferenceCode: code }),
  loadRecentMessages: async () => {
    set({ isLoadingMessages: true });
    try {
      // 아직 열려 있는(ended_at IS NULL) 대화만 조회
      // API에 include_ended=false 파라미터 전달
      const data = await api.getArchivedConversations(1, 0);
      if (!data.conversations || data.conversations.length === 0) {
        // 첫 사용 — 대화 없음
        set({ isLoadingMessages: false });
        return;
      }

      // 가장 최근 대화가 이미 종료되었으면 빈 채팅으로 시작
      const recentConv = data.conversations[0];
      if (recentConv.ended_at) {
        set({ isLoadingMessages: false });
        return;
      }

      // 열린 대화 → 메시지 로드
      const detail = await api.getConversationDetail(recentConv.id);
      if (!detail.conversation?.messages) {
        set({ isLoadingMessages: false });
        return;
      }

      // agents 배열에서 agent_id → role 매핑 구성
      const currentAgents = useConversationStore.getState().agents;
      const agentRoleMap = new Map<string, string>();
      for (const a of currentAgents) {
        agentRoleMap.set(a.id, a.role);
      }

      const messages: Message[] = detail.conversation.messages.map((msg) => {
        const isUser = msg.sender_type === 'user';
        const role = (msg.agent_id && agentRoleMap.get(msg.agent_id)) || undefined;
        return {
          id: msg.id,
          conversationId: recentConv.id,
          senderType: (isUser ? 'user' : 'agent') as Message['senderType'],
          agentName: msg.agent_name || (isUser ? '나' : '에이전트'),
          agentRole: role,
          content: msg.content,
          timestamp: msg.created_at ? new Date(msg.created_at) : new Date(),
        };
      });

      set({
        messages,
        conversationId: recentConv.id,
        isLoadingMessages: false,
        currentReferenceCode: recentConv.reference_code || null,
      });
    } catch (err) {
      console.error('[Store] Failed to load recent messages:', err);
      set({ isLoadingMessages: false });
    }
  },

  resetConversation: () => {
    const newConvId = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    set({
      messages: [],
      conversationId: newConvId,
      agentResponses: {},
      workingAgents: [],
      processingStatus: '',
      currentReferenceCode: null,
      isSending: false,
      replyingTo: null,
    });
    console.log('[Store] Conversation reset, new ID:', newConvId);
  },

  // Task execution state
  taskExecutions: {},
  activeTaskAgentId: null,
  isTaskPanelOpen: false,

  // Task execution actions
  startTaskExecution: (agentId, agentName, task) =>
    set((state) => ({
      taskExecutions: {
        ...state.taskExecutions,
        [agentId]: {
          agentId,
          agentName,
          task,
          status: 'running',
          steps: [],
          startedAt: new Date(),
        },
      },
      activeTaskAgentId: agentId,
      isTaskPanelOpen: true,
    })),

  addTaskStep: (agentId, step) =>
    set((state) => {
      const existing = state.taskExecutions[agentId];
      if (!existing) return state;
      return {
        taskExecutions: {
          ...state.taskExecutions,
          [agentId]: {
            ...existing,
            steps: [...existing.steps, step],
          },
        },
      };
    }),

  completeTaskExecution: (agentId, finalResponse) =>
    set((state) => {
      const existing = state.taskExecutions[agentId];
      if (!existing) return state;
      return {
        taskExecutions: {
          ...state.taskExecutions,
          [agentId]: {
            ...existing,
            status: 'complete',
            finalResponse,
          },
        },
      };
    }),

  failTaskExecution: (agentId, error) =>
    set((state) => {
      const existing = state.taskExecutions[agentId];
      if (!existing) return state;
      return {
        taskExecutions: {
          ...state.taskExecutions,
          [agentId]: {
            ...existing,
            status: 'error',
            finalResponse: error,
          },
        },
      };
    }),

  setActiveTaskAgentId: (agentId) => set({ activeTaskAgentId: agentId }),
  setTaskPanelOpen: (open) => set({ isTaskPanelOpen: open }),
  clearTaskExecution: (agentId) =>
    set((state) => {
      const { [agentId]: _, ...rest } = state.taskExecutions;
      return { taskExecutions: rest };
    }),
}));

// Expose store to window for dev/demo injection
if (typeof window !== 'undefined') {
  (window as any).__conversationStore = useConversationStore;
}
