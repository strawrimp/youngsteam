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
  InviteSuggestion
} from './types';

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
  isArchiveLoading: boolean;

  // Team settings
  teamSettings: TeamSettings | null;

  // Invite system state
  inviteSuggestions: InviteSuggestion[];
  isInviteModalOpen: boolean;
  pendingInvites: InviteSuggestion[];

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
