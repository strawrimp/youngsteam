import { create } from 'zustand';
import { Agent, Message, VotingResult, ModelStats, AgentResponse } from './types';

interface ConversationStore {
  // Conversation state
  conversationId: string;
  messages: Message[];
  isConnected: boolean;
  isLoading: boolean;
  processingStatus: string;

  // Agent state
  agents: Agent[];
  agentResponses: Record<string, AgentResponse>;

  // Voting state
  votingResults: VotingResult | null;
  isVoting: boolean;

  // Model stats
  modelStats: ModelStats | null;

  // Actions
  setConversationId: (id: string) => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  setConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  setProcessingStatus: (status: string) => void;

  setAgents: (agents: Agent[]) => void;
  addAgentResponse: (agentId: string, response: AgentResponse) => void;
  clearAgentResponses: () => void;

  setVotingResults: (results: VotingResult) => void;
  setIsVoting: (isVoting: boolean) => void;

  setModelStats: (stats: ModelStats) => void;
}

export const useConversationStore = create<ConversationStore>((set) => ({
  // Initial state
  conversationId: '',
  messages: [],
  isConnected: false,
  isLoading: false,
  processingStatus: '',

  agents: [],
  agentResponses: {},

  votingResults: null,
  isVoting: false,

  modelStats: null,

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
}));
