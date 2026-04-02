# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-02

### Added (Design & Accessibility)
- WCAG AA accessibility compliance: Touch targets increased to 44px minimum (FINDING-001)
- Custom typography: Poppins font family for headers and UI elements (FINDING-002)
- Enhanced interaction states: Button hover effects, tab active states, smooth transitions (FINDING-007)
- Global focus rings: Keyboard navigation support with visible 2px blue outline (FINDING-002)
- Left accent bar: Increased from 3px to 6px for better visual hierarchy (FINDING-003)
- Empty state copy: Improved microcopy for better user guidance (FINDING-004)
- Color-coded agent indicators: Visual distinction for Manager, Developer, Designer, Researcher roles

### Frontend Structure
- React 18 + TypeScript with Vite dev server
- 3-column grid layout: Agent panel (left) | Chat window (center) | Voting panel (right)
- Responsive design: Breakpoints at 640px (mobile), 900px (tablet), 1200px (desktop)
- Zustand state management for conversation and agent state
- WebSocket integration for real-time updates

### Backend Foundation
- FastAPI server with WebSocket support
- PostgreSQL database schema for agents, conversations, messages, shared_memory, decisions, votes
- Async/await patterns for concurrent agent processing
- Agent manager with 4 specialized agents (manager, developer, designer, researcher)

### Known Limitations
- Backend agents not yet connected to frontend (WebSocket integration in progress)
- Image generation and analysis not yet implemented (Phase 4)
- Desktop-only responsive design (mobile layout deferred)
- Focus on visual polish; core multi-agent logic in development

---

For details on accessibility implementation, see the design audit findings in `.gstack/design-audit-report.md`.
