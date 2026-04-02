import { create } from 'zustand';

interface Message {
  id: string;
  conversationId: string;
  senderType: 'user' | 'agent';
  agentName?: string;
  content: string;
  timestamp: Date;
}

interface ConversationStore {
  conversationId: string;
  messages: Message[];
  isConnected: boolean;
  isLoading: boolean;

  setConversationId: (id: string) => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  setConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
}

export const useConversationStore = create<ConversationStore>((set) => ({
  conversationId: '',
  messages: [],
  isConnected: false,
  isLoading: false,

  setConversationId: (id: string) => set({ conversationId: id }),
  addMessage: (message: Message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  clearMessages: () => set({ messages: [] }),
  setConnected: (connected: boolean) => set({ isConnected: connected }),
  setLoading: (loading: boolean) => set({ isLoading: loading }),
}));
