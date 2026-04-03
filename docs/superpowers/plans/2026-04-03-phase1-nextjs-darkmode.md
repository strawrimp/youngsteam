# AI Virtual Company v2 - Phase 1: Next.js 15 + Dark Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create new Next.js 15 frontend with dark mode design system and 3-column layout, connecting to existing FastAPI backend

**Architecture:** Migrate from React+Vite to Next.js 15, implement dark mode with CSS Variables, create 3-column dashboard layout (Agent Panel + Main Chat + Context Panel), integrate shadcn/ui components

**Tech Stack:** Next.js 15, TypeScript, Tailwind CSS v4, shadcn/ui, Zustand, WebSocket, FastAPI

---

## Pre-requisites

### Step 1: Verify backend is running

```bash
curl -s http://localhost:8000/health
```

Expected: `{"status":"healthy","environment":"development"}`

### Step 2: Check current frontend structure

```bash
ls -la /Users/maegmini/my-ai-company/frontend/src/
```

Expected: components/, main.tsx, store.ts, api.ts, types.ts

---

## Task 1: Create Next.js 15 Project

**Files:**
- Create: `/Users/maegmini/my-ai-company/frontend-next/`
- Delete: NOT deletion - new project directory

- [ ] **Step 1: Create Next.js 15 project**

```bash
cd /Users/maegmini/my-ai-company
npx create-next-app@latest frontend-next \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --use-npm \
  --no-turbopack \
  --yes
```

Expected: Next.js 15 project created in frontend-next/

- [ ] **Step 2: Install dependencies**

```bash
cd /Users/maegmini/my-ai-company/frontend-next
npm install zustand @radix-ui/react-slot class-variance-authority clsx tailwind-merge lucide-react
```

Expected: Dependencies installed

- [ ] **Step 3: Verify dev server starts**

```bash
cd /Users/maegmini/my-ai-company/frontend-next
npm run dev &
sleep 10
curl -s http://localhost:3000 | head -20
```

Expected: HTML page returned

- [ ] **Step 4: Commit**

```bash
cd /Users/maegmini/my-ai-company
git add frontend-next/
git commit -m "feat: create Next.js 15 project base"
```

---

## Task 2: Set Up Dark Mode Design System

**Files:**
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/app/globals.css`
- Modify: `/Users/maegmini/my-ai-company/frontend-next/src/app/layout.tsx`

- [ ] **Step 1: Create dark mode CSS variables**

```css
/* /Users/maegmini/my-ai-company/frontend-next/src/app/globals.css */

@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  /* Dark mode tokens - will be applied by default */
  --bg-primary: #0a0a0a;
  --bg-secondary: #111111;
  --bg-elevated: #1a1a1a;
  --bg-muted: #1f1f1f;
  
  --border: rgba(255, 255, 255, 0.08);
  --border-hover: rgba(255, 255, 255, 0.15);
  
  --text-primary: #fafafa;
  --text-secondary: #a1a1a1;
  --text-muted: #737373;
  
  /* Agent colors */
  --agent-manager: #5B8DEF;
  --agent-developer: #4ADE80;
  --agent-designer: #A78BFA;
  --agent-researcher: #FCD34D;
  
  /* Status colors */
  --success: #22c55e;
  --error: #ef4444;
  --warning: #f59e0b;
}

@layer base {
  html {
    color-scheme: dark;
  }
  
  body {
    @apply bg-[var(--bg-primary)] text-[var(--text-primary)];
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  
  * {
    @apply border-[var(--border)];
  }
}
```

- [ ] **Step 2: Update layout for dark mode**

```tsx
/* /Users/maegmini/my-ai-company/frontend-next/src/app/layout.tsx */

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Virtual Company",
  description: "Multi-agent collaboration system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="dark">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: Verify dark mode**

```bash
curl -s http://localhost:3000 | grep -o "bg-primary\|dark"
```

Expected: Contains dark mode classes

- [ ] **Step 4: Commit**

```bash
git add frontend-next/src/app/globals.css frontend-next/src/app/layout.tsx
git commit -m "feat: add dark mode design system"
```

---

## Task 3: Create Utility Functions (cn helper)

**Files:**
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/lib/utils.ts`

- [ ] **Step 1: Create cn utility**

```typescript
/* /Users/maegmini/my-ai-company/frontend-next/src/lib/utils.ts */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend-next/src/lib/utils.ts
git commit -m "feat: add cn utility function"
```

---

## Task 4: Create Zustand Stores

**Files:**
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/stores/agent-store.ts`
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/stores/chat-store.ts`
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/stores/vote-store.ts`

- [ ] **Step 1: Create agent store**

```typescript
/* /Users/maegmini/my-ai-company/frontend-next/src/stores/agent-store.ts */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

export interface Agent {
  id: string;
  name: string;
  role: 'manager' | 'developer' | 'designer' | 'researcher';
  status: 'idle' | 'thinking' | 'responding' | 'error';
}

interface AgentStore {
  agents: Agent[];
  selectedAgentId: string | null;
  setAgents: (agents: Agent[]) => void;
  updateAgentStatus: (id: string, status: Agent['status']) => void;
  selectAgent: (id: string | null) => void;
}

export const useAgentStore = create<AgentStore>()(
  subscribeWithSelector((set) => ({
    agents: [],
    selectedAgentId: null,
    
    setAgents: (agents) => set({ agents }),
    
    updateAgentStatus: (id, status) =>
      set((state) => ({
        agents: state.agents.map((a) =>
          a.id === id ? { ...a, status } : a
        ),
      })),
    
    selectAgent: (id) => set({ selectedAgentId: id }),
  }))
);
```

- [ ] **Step 2: Create chat store**

```typescript
/* /Users/maegmini/my-ai-company/frontend-next/src/stores/chat-store.ts */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

export interface Message {
  id: string;
  conversationId: string;
  senderType: 'user' | 'agent';
  agentName?: string;
  content: string;
  timestamp: Date;
  type: 'text' | 'error';
}

interface ChatStore {
  messages: Message[];
  isConnected: boolean;
  isLoading: boolean;
  processingStatus: string;
  conversationId: string;
  
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  clearMessages: () => void;
  setConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  setProcessingStatus: (status: string) => void;
  setConversationId: (id: string) => void;
}

export const useChatStore = create<ChatStore>()(
  subscribeWithSelector((set) => ({
    messages: [],
    isConnected: false,
    isLoading: false,
    processingStatus: '',
    conversationId: '',
    
    addMessage: (message) =>
      set((state) => ({ messages: [...state.messages, message] })),
    
    setMessages: (messages) => set({ messages }),
    
    clearMessages: () => set({ messages: [] }),
    
    setConnected: (isConnected) => set({ isConnected }),
    
    setLoading: (isLoading) => set({ isLoading }),
    
    setProcessingStatus: (processingStatus) => set({ processingStatus }),
    
    setConversationId: (conversationId) => set({ conversationId }),
  }))
);
```

- [ ] **Step 3: Create vote store**

```typescript
/* /Users/maegmini/my-ai-company/frontend-next/src/stores/vote-store.ts */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

export interface Vote {
  agentId: string;
  agentName: string;
  choice: string;
  reasoning: string;
}

export interface VotingResult {
  topic: string;
  candidates: string[];
  votes: Vote[];
  winner: string | null;
  isTied: boolean;
}

interface VoteStore {
  votingResults: VotingResult | null;
  isVoting: boolean;
  currentTopic: string | null;
  
  setVotingResults: (results: VotingResult) => void;
  setIsVoting: (isVoting: boolean) => void;
  setCurrentTopic: (topic: string | null) => void;
}

export const useVoteStore = create<VoteStore>()(
  subscribeWithSelector((set) => ({
    votingResults: null,
    isVoting: false,
    currentTopic: null,
    
    setVotingResults: (votingResults) => set({ votingResults }),
    
    setIsVoting: (isVoting) => set({ isVoting }),
    
    setCurrentTopic: (currentTopic) => set({ currentTopic }),
  }))
);
```

- [ ] **Step 4: Commit**

```bash
git add frontend-next/src/stores/
git commit -m "feat: add Zustand stores with subscribeWithSelector"
```

---

## Task 5: Create API Client

**Files:**
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/lib/api.ts`

- [ ] **Step 1: Create API client**

```typescript
/* /Users/maegmini/my-ai-company/frontend-next/src/lib/api.ts */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = {
  async getHealth() {
    const response = await fetch(`${API_BASE}/health`);
    return response.json();
  },

  async getAgents() {
    const response = await fetch(`${API_BASE}/api/agents`);
    if (!response.ok) throw new Error('Failed to fetch agents');
    return response.json();
  },

  async getModelStats() {
    const response = await fetch(`${API_BASE}/api/stats/models`);
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
  },

  async startVoting(topic: string, candidates: string[], conversationId: string) {
    const response = await fetch(`${API_BASE}/api/voting/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, candidates, conversation_id: conversationId }),
    });
    if (!response.ok) throw new Error('Failed to start voting');
    return response.json();
  },

  async getVotingResult(votingId: string) {
    const response = await fetch(`${API_BASE}/api/voting/${votingId}/result`);
    if (!response.ok) throw new Error('Failed to fetch result');
    return response.json();
  },
};
```

- [ ] **Step 2: Create WebSocket hook**

```typescript
/* /Users/maegmini/my-ai-company/frontend-next/src/hooks/useWebSocket.ts */

import { useEffect, useRef, useCallback } from 'react';
import { useChatStore } from '@/stores/chat-store';
import { useAgentStore } from '@/stores/agent-store';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const { setConnected, addMessage, setProcessingStatus, setLoading } = useChatStore();
  const { updateAgentStatus } = useAgentStore();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'status':
            setProcessingStatus(data.message || '');
            if (data.status === 'complete') {
              setLoading(false);
              setProcessingStatus('');
            }
            break;

          case 'agent_response':
            updateAgentStatus(data.agent_id, 'idle');
            addMessage({
              id: `msg-${Date.now()}-${Math.random()}`,
              conversationId: '',
              senderType: 'agent',
              agentName: data.agent_name,
              content: data.content,
              timestamp: new Date(data.timestamp || Date.now()),
              type: 'text',
            });
            break;

          case 'error':
            addMessage({
              id: `msg-${Date.now()}-error`,
              conversationId: '',
              senderType: 'agent',
              content: `오류: ${data.error}`,
              timestamp: new Date(),
              type: 'error',
            });
            break;
        }
      } catch (e) {
        console.error('Failed to parse message:', e);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      setConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnected(false);
    };
  }, [setConnected, addMessage, setProcessingStatus, setLoading, updateAgentStatus]);

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ content }));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { sendMessage };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend-next/src/lib/api.ts frontend-next/src/hooks/useWebSocket.ts
git commit -m "feat: add API client and WebSocket hook"
```

---

## Task 6: Create UI Components

**Files:**
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/components/ui/button.tsx`
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/components/ui/textarea.tsx`
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/components/ui/card.tsx`
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/components/AgentPanel.tsx`
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/components/ChatWindow.tsx`
- Create: `/Users/maegmini/my-ai-company/frontend-next/src/components/VotingPanel.tsx`

- [ ] **Step 1: Create Button component**

```tsx
/* /Users/maegmini/my-ai-company/frontend-next/src/components/ui/button.tsx */

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-[var(--agent-manager)] text-white hover:opacity-90",
        destructive: "bg-[var(--error)] text-white hover:opacity-90",
        outline: "border border-[var(--border)] bg-transparent hover:bg-[var(--bg-elevated)]",
        secondary: "bg-[var(--bg-elevated)] text-[var(--text-primary)] hover:opacity-80",
        ghost: "hover:bg-[var(--bg-elevated)]",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

- [ ] **Step 2: Create Textarea component**

```tsx
/* /Users/maegmini/my-ai-company/frontend-next/src/components/ui/textarea.tsx */

import * as React from "react";
import { cn } from "@/lib/utils";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[60px] w-full rounded-md border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-sm placeholder:text-[var(--text-muted)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Textarea.displayName = "Textarea";

export { Textarea };
```

- [ ] **Step 3: Create Card component**

```tsx
/* /Users/maegmini/my-ai-company/frontend-next/src/components/ui/card.tsx */

import * as React from "react";
import { cn } from "@/lib/utils";

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)]",
      className
    )}
    {...props}
  />
));
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-4", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-4 pt-0", className)} {...props} />
));
CardContent.displayName = "CardContent";

export { Card, CardHeader, CardContent };
```

- [ ] **Step 4: Commit**

```bash
git add frontend-next/src/components/ui/
git commit -m "feat: add shadcn/ui base components"
```

---

## Task 7: Create Main Layout and Page

**Files:**
- Modify: `/Users/maegmini/my-ai-company/frontend-next/src/app/page.tsx`

- [ ] **Step 1: Create AgentPanel component**

```tsx
/* /Users/maegmini/my-ai-company/frontend-next/src/components/AgentPanel.tsx */

'use client';

import { useAgentStore } from '@/stores/agent-store';

const AGENT_COLORS = {
  manager: 'var(--agent-manager)',
  developer: 'var(--agent-developer)',
  designer: 'var(--agent-designer)',
  researcher: 'var(--agent-researcher)',
};

export function AgentPanel() {
  const { agents, selectedAgentId, selectAgent } = useAgentStore();

  return (
    <aside className="w-60 border-r border-[var(--border)] bg-[var(--bg-secondary)] p-4">
      <h2 className="text-lg font-semibold mb-4">에이전트 팀</h2>
      <div className="space-y-2">
        {agents.length === 0 ? (
          <p className="text-sm text-[var(--text-muted)]">로딩 중...</p>
        ) : (
          agents.map((agent) => (
            <div
              key={agent.id}
              onClick={() => selectAgent(agent.id)}
              className={`p-3 rounded-lg cursor-pointer transition-colors ${
                selectedAgentId === agent.id
                  ? 'bg-[var(--bg-elevated)]'
                  : 'hover:bg-[var(--bg-elevated)]'
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: AGENT_COLORS[agent.role] }}
                />
                <span className="font-medium">{agent.name}</span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span
                  className={`w-2 h-2 rounded-full ${
                    agent.status === 'idle' ? 'bg-[var(--text-muted)]' : 'animate-pulse'
                  }`}
                  style={{
                    backgroundColor:
                      agent.status === 'idle'
                        ? 'var(--text-muted)'
                        : AGENT_COLORS[agent.role],
                  }}
                />
                <span className="text-xs text-[var(--text-muted)]">
                  {agent.status === 'idle' ? '대기 중' : '생각 중...'}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
```

- [ ] **Step 2: Create ChatWindow component**

```tsx
/* /Users/maegmini/my-ai-company/frontend-next/src/components/ChatWindow.tsx */

'use client';

import { useState, useRef, useEffect } from 'react';
import { useChatStore } from '@/stores/chat-store';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';

export function ChatWindow() {
  const { messages, isConnected, isLoading, processingStatus, addMessage, conversationId, setLoading } = useChatStore();
  const { sendMessage } = useWebSocket();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, processingStatus]);

  const handleSend = () => {
    if (!input.trim() || !isConnected) return;
    
    addMessage({
      id: `msg-${Date.now()}`,
      conversationId,
      senderType: 'user',
      content: input,
      timestamp: new Date(),
      type: 'text',
    });
    
    setLoading(true);
    sendMessage(input);
    setInput('');
  };

  return (
    <main className="flex-1 flex flex-col bg-[var(--bg-primary)]">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-[var(--border)] px-4 py-3 bg-[var(--bg-secondary)]">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-[var(--success)]' : 'bg-[var(--error)]'}`} />
          <span className="text-sm font-medium">
            {isConnected ? '✓ 연결됨' : '○ 연결 중단'}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !processingStatus && (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-center">
            <p className="text-2xl">👋</p>
            <p className="text-base font-medium">대화를 시작하세요</p>
            <p className="text-sm text-[var(--text-muted)]">
              메시지를 입력하면 4명의 에이전트가 함께 응답합니다
            </p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`p-3 rounded-lg ${
              message.senderType === 'user'
                ? 'bg-[var(--agent-manager)] text-white ml-8'
                : message.type === 'error'
                ? 'bg-[var(--error)] text-white'
                : 'bg-[var(--bg-elevated)] mr-8'
            }`}
          >
            {message.senderType !== 'user' && (
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold">{message.agentName}</span>
                <span className="text-xs text-[var(--text-muted)]">
                  {message.timestamp.toLocaleTimeString('ko-KR', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
            )}
            <p className="text-sm">{message.content}</p>
          </div>
        ))}

        {processingStatus && (
          <div className="bg-[var(--bg-elevated)] p-3 rounded-lg">
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <span className="w-2 h-2 rounded-full bg-[var(--agent-manager)] animate-pulse" />
                <span className="w-2 h-2 rounded-full bg-[var(--agent-manager)] animate-pulse" style={{ animationDelay: '0.2s' }} />
                <span className="w-2 h-2 rounded-full bg-[var(--agent-manager)] animate-pulse" style={{ animationDelay: '0.4s' }} />
              </div>
              <span className="text-sm">{processingStatus || '에이전트가 생각 중...'}</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 border-t border-[var(--border)] bg-[var(--bg-secondary)] p-4 space-y-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="메시지를 입력하세요... (Shift+Enter: 줄바꿈)"
          disabled={!isConnected || isLoading}
          className="max-h-[120px]"
        />
        <Button onClick={handleSend} disabled={!isConnected || !input.trim() || isLoading} className="w-full">
          {isLoading ? '전송 중...' : '전송'}
        </Button>
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Create VotingPanel component**

```tsx
/* /Users/maegmini/my-ai-company/frontend-next/src/components/VotingPanel.tsx */

'use client';

import { useVoteStore } from '@/stores/vote-store';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export function VotingPanel() {
  const { votingResults, isVoting, currentTopic } = useVoteStore();

  return (
    <aside className="w-72 border-l border-[var(--border)] bg-[var(--bg-secondary)] p-4">
      <h2 className="text-lg font-semibold mb-4">투표</h2>
      
      {!votingResults ? (
        <div className="text-center py-8">
          <p className="text-sm text-[var(--text-muted)]">
            아직 투표 결과가 없습니다
          </p>
          <p className="text-xs text-[var(--text-muted)] mt-2">
            투표를 시작하면 결과가 여기 표시됩니다
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <h3 className="font-medium">{votingResults.topic}</h3>
            </CardHeader>
            <CardContent>
              {votingResults.isTied ? (
                <p className="text-sm text-[var(--warning)]">동점 - 매니저 최종 결정 필요</p>
              ) : (
                <div>
                  <p className="text-sm font-medium">최종 결정: {votingResults.winner}</p>
                  <div className="mt-2 space-y-1">
                    {votingResults.votes.map((vote, i) => (
                      <div key={i} className="text-xs flex justify-between">
                        <span>{vote.agentName}:</span>
                        <span>{vote.choice}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </aside>
  );
}
```

- [ ] **Step 4: Create main page**

```tsx
/* /Users/maegmini/my-ai-company/frontend-next/src/app/page.tsx */

'use client';

import { useEffect } from 'react';
import { AgentPanel } from '@/components/AgentPanel';
import { ChatWindow } from '@/components/ChatWindow';
import { VotingPanel } from '@/components/VotingPanel';
import { useAgentStore } from '@/stores/agent-store';
import { useChatStore } from '@/stores/chat-store';
import { api } from '@/lib/api';

export default function Home() {
  const { setAgents } = useAgentStore();
  const { setConversationId, setConnected } = useChatStore();

  useEffect(() => {
    // Initialize conversation
    setConversationId(`conv-${Date.now()}`);
    
    // Fetch agents
    api.getAgents()
      .then((data) => {
        const agentsWithStatus = data.agents.map((a: any) => ({
          ...a,
          status: 'idle' as const,
        }));
        setAgents(agentsWithStatus);
      })
      .catch(console.error);

    // Check WebSocket connection via health
    api.getHealth().then(() => setConnected(true)).catch(() => setConnected(false));
  }, [setAgents, setConversationId, setConnected]);

  return (
    <div className="flex h-screen">
      <AgentPanel />
      <ChatWindow />
      <VotingPanel />
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend-next/src/components/
git commit -m "feat: add AgentPanel, ChatWindow, VotingPanel components"
```

---

## Task 8: Verify End-to-End

**Files:**
- No file changes - verification only

- [ ] **Step 1: Verify frontend loads**

```bash
curl -s http://localhost:3000 | grep -o "AI Virtual Company\|에이전트\|투표"
```

Expected: Contains Korean text from components

- [ ] **Step 2: Test API connection**

```bash
curl -s http://localhost:8000/api/agents | head -50
```

Expected: JSON with agents array

- [ ] **Step 3: Take screenshot**

```bash
# Using browser to verify UI
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: complete Phase 1 - Next.js 15 + Dark Mode"
```

---

## Summary

**Completed Tasks:**
- Task 1: Next.js 15 Project created
- Task 2: Dark mode design system with CSS Variables
- Task 3: Utility functions (cn helper)
- Task 4: Zustand stores with subscribeWithSelector
- Task 5: API client and WebSocket hook
- Task 6: shadcn/ui base components (Button, Textarea, Card)
- Task 7: Main layout with 3 panels
- Task 8: Verification

**Next Phase:** Phase 2 - DebateEngine + AgentMessageBroker

---

**Plan complete and saved to `/Users/maegmini/my-ai-company/docs/superpowers/plans/2026-04-03-phase1-nextjs-darkmode.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**