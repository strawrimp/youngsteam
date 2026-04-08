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
}));

// Expose store to window for dev/demo injection
if (typeof window !== 'undefined') {
  (window as any).__conversationStore = useConversationStore;
}
