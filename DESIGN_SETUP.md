# Design System Implementation Guide

This document provides step-by-step instructions for integrating Tailwind CSS and the design system into the AI Virtual Company project.

## Prerequisites

- Node.js 18+ with npm/bun
- Existing Vite + React setup
- All files from this commit available

## Phase 1: Install Dependencies

### Step 1: Install Tailwind CSS and related packages

```bash
cd frontend

# Using npm
npm install -D tailwindcss postcss autoprefixer @tailwindcss/forms

# Or using bun
bun add -d tailwindcss postcss autoprefixer @tailwindcss/forms
```

### Step 2: Verify configuration files

The following files should already exist from the design system commit:
- `../tailwind.config.ts` — design tokens and component classes
- `../postcss.config.cjs` — PostCSS plugin configuration
- `src/styles/globals.css` — Tailwind directives and base component styles

### Step 3: Update Vite configuration

Edit `vite.config.ts` to ensure CSS is being processed correctly. The config should look like:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
})
```

No additional Tailwind configuration is needed in Vite — PostCSS will handle it automatically.

### Step 4: Update main.tsx entry point

Edit `src/main.tsx` to import the Tailwind CSS file:

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './styles/globals.css'  // ← Add this line
import './index.css'            // Keep existing styles if any

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### Step 5: Update HTML base styles

Edit `index.html` to add the Geist font import in the `<head>`:

```html
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />

    <!-- Add Geist font -->
    <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&display=swap" rel="stylesheet">

    <title>AI 가상 회사</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

## Phase 2: Refactor Existing Components

### Step 1: Create color constants file

Create `frontend/src/constants/colors.ts`:

```typescript
export const AGENT_COLORS = {
  manager: '#4E7EBE',     // Leadership blue
  developer: '#4A9B6F',   // Technical green
  designer: '#7C6BA8',    // Creative purple
  researcher: '#D4A055',  // Analytical amber
} as const;

export const SEMANTIC_COLORS = {
  success: '#2F855A',
  warning: '#C05621',
  error: '#C53030',
  info: '#2D3748',
} as const;

export const NEUTRAL_COLORS = {
  white: '#FFFFFF',
  surface: '#F7F9FC',
  hover: '#EDF2F7',
  active: '#E2E8F0',
  border: '#E1E7F0',
  textPrimary: '#1A202C',
  textSecondary: '#718096',
  textTertiary: '#A0AEC0',
} as const;
```

### Step 2: Update ChatWindow.tsx

Replace CSS Modules imports with Tailwind classes:

**Before:**
```typescript
import styles from './ChatWindow.module.css'

export const ChatWindow: React.FC = () => {
  return (
    <div className={styles.container}>
      <div className={styles.messages}>
        {messages.map(msg => (
          <div key={msg.id} className={styles.message}>
            {msg.content}
          </div>
        ))}
      </div>
      <input className={styles.input} placeholder="메시지 입력..." />
    </div>
  )
}
```

**After:**
```typescript
import { AGENT_COLORS } from '../constants/colors'

export const ChatWindow: React.FC = () => {
  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex-1 overflow-y-auto p-lg space-y-lg">
        {messages.map(msg => (
          <div
            key={msg.id}
            className={msg.senderType === 'user'
              ? 'message-user'
              : 'message-agent'
            }
            style={msg.senderType !== 'user' ? {
              borderLeftColor: AGENT_COLORS[msg.agentName?.toLowerCase() as keyof typeof AGENT_COLORS] || AGENT_COLORS.manager
            } : {}}
          >
            {msg.senderType !== 'user' && (
              <div className="text-xs font-semibold mb-md"
                   style={{ color: AGENT_COLORS[msg.agentName?.toLowerCase() as keyof typeof AGENT_COLORS] || AGENT_COLORS.manager }}>
                {msg.agentName}
              </div>
            )}
            <div className="text-base leading-normal">
              {msg.content}
            </div>
          </div>
        ))}
      </div>
      <div className="border-t border-neutral-300 p-lg">
        <input
          className="input"
          placeholder="메시지 입력..."
          onChange={(e) => setInput(e.target.value)}
        />
      </div>
    </div>
  )
}
```

### Step 3: Update AgentPanel.tsx

```typescript
import { AGENT_COLORS } from '../constants/colors'

export const AgentPanel: React.FC = () => {
  return (
    <aside className="w-sidebar-left border-r border-neutral-300 bg-white overflow-y-auto">
      <div className="p-lg space-y-md">
        {agents.map(agent => (
          <div
            key={agent.id}
            className="agent-card"
            style={{
              backgroundColor: AGENT_COLORS[agent.role as keyof typeof AGENT_COLORS] || AGENT_COLORS.manager
            }}
          >
            <div className="flex items-start justify-between mb-md">
              <div>
                <h3 className="text-lg font-semibold text-white mb-xs">
                  {agent.name}
                </h3>
                <span className="badge-solid text-xs">
                  {agent.role}
                </span>
              </div>
              <div className="flex-shrink-0">
                <span className={`inline-block w-2 h-2 rounded-full ${
                  agent.status === 'active' ? 'bg-success' :
                  agent.status === 'thinking' ? 'bg-agent-manager animate-pulse' :
                  'bg-neutral-400'
                }`} />
              </div>
            </div>
            <p className="text-sm text-white opacity-90">
              {agent.description}
            </p>
          </div>
        ))}
      </div>
    </aside>
  )
}
```

### Step 4: Update VotingPanel.tsx

```typescript
import { AGENT_COLORS } from '../constants/colors'

export const VotingPanel: React.FC = () => {
  return (
    <aside className="w-sidebar-right border-l border-neutral-300 bg-white overflow-y-auto">
      <div className="p-lg">
        <h2 className="text-xl font-semibold text-neutral-900 mb-lg">
          {isVoting ? '투표 진행 중' : '투표 결과'}
        </h2>

        {votingTopic && (
          <p className="text-sm text-neutral-600 mb-lg">
            주제: {votingTopic}
          </p>
        )}

        <div className="space-y-md">
          {candidates.map(candidate => (
            <div
              key={candidate.id}
              className="card cursor-pointer transition-all hover:shadow-md"
              style={{
                borderLeft: `4px solid ${AGENT_COLORS[candidate.agentRole as keyof typeof AGENT_COLORS] || AGENT_COLORS.manager}`,
                backgroundColor: isVoted
                  ? 'rgba(' + Object.values(AGENT_COLORS)[0].replace('#', '') + ', 0.1)'
                  : 'white'
              }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-neutral-900">
                    {candidate.agentName}
                  </h3>
                  <p className="text-sm text-neutral-600">
                    {candidate.choice}
                  </p>
                </div>
                {isVoted && (
                  <div className="flex-shrink-0 text-success">
                    ✓
                  </div>
                )}
              </div>

              {isVoted && candidate.votes !== undefined && (
                <div className="mt-md">
                  <div className="text-xs text-neutral-600 mb-xs">
                    {candidate.votes}/{totalVotes}
                  </div>
                  <div className="w-full bg-neutral-300 rounded-full h-1">
                    <div
                      className="h-1 rounded-full transition-all duration-300"
                      style={{
                        width: `${(candidate.votes / totalVotes) * 100}%`,
                        backgroundColor: AGENT_COLORS[candidate.agentRole as keyof typeof AGENT_COLORS] || AGENT_COLORS.manager
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {!isVoting && (
          <button className="btn w-full mt-lg">
            새로운 투표 시작
          </button>
        )}
      </div>
    </aside>
  )
}
```

### Step 5: Update App.tsx main layout

```typescript
export const App: React.FC = () => {
  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header className="border-b border-neutral-300 bg-white px-2xl py-lg">
        <h1 className="text-3xl font-semibold text-neutral-900">
          AI 가상 회사
        </h1>
        <p className="text-sm text-neutral-600 mt-xs">
          멀티-에이전트 협력 시스템
        </p>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Responsive layout */}
        <div className="hidden desktop:block">
          <AgentPanel />
        </div>

        <main className="flex-1 overflow-hidden">
          <ChatWindow />
        </main>

        <div className="hidden desktop:block">
          <VotingPanel />
        </div>

        {/* Tablet/Mobile tabs */}
        <div className="desktop:hidden">
          {/* Tab navigation would go here */}
        </div>
      </div>

      {/* Connection status indicator */}
      <footer className="border-t border-neutral-300 bg-neutral-50 px-lg py-xs">
        <p className="text-xs text-neutral-600">
          {isConnected ? '✓ 연결됨' : '○ 연결 대기 중...'}
        </p>
      </footer>
    </div>
  )
}
```

## Phase 3: Clean up old CSS

Once all components are migrated to Tailwind classes:

1. Remove `*.module.css` files from components
2. Keep `src/styles/globals.css` (the Tailwind entry point)
3. Remove any `index.css` if it only contained global styles
4. Update imports in component files

### Example cleanup:

```bash
# Remove old CSS module files
rm frontend/src/components/ChatWindow.module.css
rm frontend/src/components/AgentPanel.module.css
rm frontend/src/components/VotingPanel.module.css
```

## Phase 4: Install and configure shadcn/ui (Optional, Phase 3)

When ready to use pre-built components from shadcn/ui:

```bash
cd frontend

# Install shadcn/ui CLI
npm install -D shadcn-ui

# Or using bun
bun add -d shadcn-ui
```

Then initialize shadcn/ui:

```bash
npx shadcn-ui@latest init
```

When prompted:
- Use TypeScript: `y`
- Use CSS Variables: `n` (we're using Tailwind)
- Use PostCSS for import aliases: `y`

Then add specific components as needed:

```bash
npx shadcn-ui@latest add button
npx shadcn-ui@latest add input
npx shadcn-ui@latest add card
npx shadcn-ui@latest add tabs
```

## Verification Checklist

- [ ] Tailwind CSS dependencies installed
- [ ] `tailwind.config.ts` exists and references design tokens
- [ ] `postcss.config.cjs` exists
- [ ] `src/styles/globals.css` imported in `main.tsx`
- [ ] Geist font imported in `index.html`
- [ ] All agent colors visible and correctly applied
- [ ] Keyboard focus rings visible on interactive elements
- [ ] Touch targets are at least 44px × 44px
- [ ] Responsive layout works at 320px, 768px, and 1440px viewports
- [ ] No console errors or warnings

## Development Workflow

### Running the dev server

```bash
cd frontend
bun run dev
```

The Vite dev server will automatically compile Tailwind CSS and reload on changes.

### Testing responsive design

Use Chrome DevTools or Firefox Developer Tools to test at different breakpoints:

```javascript
// In browser console
window.matchMedia('(max-width: 767px)').matches     // Mobile
window.matchMedia('(min-width: 768px)').matches     // Tablet+
window.matchMedia('(min-width: 1440px)').matches    // Desktop
```

### Testing accessibility

1. **Keyboard navigation:** Tab through all elements
2. **Focus visibility:** All interactive elements should have visible focus rings
3. **Color contrast:** Use WebAIM Contrast Checker for text on colored backgrounds
4. **Reduced motion:** Use DevTools to test `prefers-reduced-motion: reduce`

```bash
# In DevTools → Rendering → Emulate CSS media feature preferences
```

## Troubleshooting

### Tailwind CSS not applying styles

**Problem:** Styles don't appear or are being overridden

**Solutions:**
1. Verify `src/styles/globals.css` is imported in `main.tsx`
2. Check that `tailwind.config.ts` references the correct paths
3. Restart the dev server: `Ctrl+C` and `bun run dev`
4. Clear browser cache: `Cmd+Shift+Delete` or `Ctrl+Shift+Delete`

### PostCSS errors in console

**Problem:** "PostCSS plugin tailwindcss not found"

**Solutions:**
1. Verify `postcss.config.cjs` exists in project root (not frontend/)
2. Reinstall dependencies: `rm -rf node_modules && bun install`
3. Check Node version is 18+: `node --version`

### Tailwind classes not recognized in IDE

**Problem:** TypeScript/ESLint warnings about unknown classes

**Solutions:**
1. Install Tailwind CSS IntelliSense extension (VS Code)
2. Add to `.vscode/settings.json`:
```json
{
  "tailwindCSS.experimental.classRegex": [
    ["clsx\\(([^)]*)\\)", "(?:'|\"|`)([^']*)(?:'|\"|`)"]
  ]
}
```

## Next Steps

1. **Phase 2 (Current):** Migrate all components to Tailwind CSS
2. **Phase 3:** Install shadcn/ui for pre-built accessible components
3. **Phase 4:** Add dark mode support using CSS variables
4. **Phase 5:** Create Storybook for component documentation

## Resources

- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Tailwind CSS IntelliSense](https://marketplace.visualstudio.com/items?itemName=bradlc.vscode-tailwindcss)
- [shadcn/ui](https://ui.shadcn.com/)
- [Geist Font](https://vercel.com/font)
- [WCAG 2.1 AA Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

**Last Updated:** 2026-04-02
**Status:** Design system ready for implementation
