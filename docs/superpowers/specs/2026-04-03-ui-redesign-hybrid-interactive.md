# UI Redesign: Hybrid Interactive Style

**Date**: 2026-04-03  
**Author**: Sisyphus (via brainstorming skill)  
**Status**: Approved

---

## Overview

AI 가상 회사의 UI를 현대적이고 인터랙티브한 **Hybrid Interactive** 스타일로 전면 재설계합니다. Glassmorphism + 인터랙티브 요소 + 진행 표시줄을 결합하여 사용자 경험을 극대화합니다.

### Design Goals
1. **Modern Aesthetic**: 2024년 최신 SaaS 트렌드 반영
2. **Enhanced Interactivity**: 더 많은 사용자 피드백과 인터랙션
3. **Information Density**: 더 많은 정보를 효율적으로 표시
4. **System Integration**: 다크/라이트 모드 자동 전환

---

## Design Decisions

### Q1: UI Priority?
**A**: Full Redesign (selected)

### Q2: Default Theme?
**C**: Auto-switch (system preference)

### Q3: Color Palette?
**A**: Clean & Professional (neutral grays, white, slate)

### Q4: Card Style?
**A**: 4-column cards with icons (selected)

### Q5: Approach?
**Approach 3: Hybrid Interactive** (selected)
- Glassmorphism cards + interactive elements
- Real-time status updates
- Micro-interactions
- Progress indicators
- Context menus

---

## Section 1: Header & Layout

### **Header** (40px)
- **Title**: "AI 가상 회사" + Inter, 시스템 폰트, semi-bold
- **Status Indicators**:
  - 연결 상태 (녹색/빨간 점)
  - 활성 에이전트 수 (실시간 업데이트)
  - 모델 정보 (V4/R1 비율)

### **Main Layout Structure**
```
┌──────────┬──────────────────────┬──────────┐
│          │                      │          │
│  Agent   │     Chat Area        │  Voting  │
│  Panel   │                      │  Panel   │
│  280px   │      (flexible)       │  320px   │
│          │                      │          │
│          │                      │          │
└──────────┴──────────────────────┴──────────┘
```

**Responsive Behavior:**
- **Desktop (≥1024px)**: 3-column layout
- **Tablet (768px-1023px)**: 2-column (Agent Panel + Chat, Voting Panel below)
- **Mobile (<768px)**: Single column stack

### **Grid System**
```css
.container {
  display: grid;
  grid-template-columns: 280px 1fr 320px;
  gap: 16px;
  padding: 16px;
  height: calc(100vh - 72px); /* 72px = header height */
}

/* Responsive */
@media (max-width: 1023px) {
  .container {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
  }
}
```

---

## Section 2: Agent Panel

### **Agent Card Layout**
```
┌─────────────────────────────────────┐
│  ┌─────────────┐   ◃  Avatar │
│  │ 👤 Avatar     │   │  Name   │
│  │ Name + Role │   │  Role   │
│  └─────────────┘   │         │
│  ┌─────────────┐   │ ● Status │
│  │ Status      │   │   Dot   │
│  └─────────────┘   │         │
│  ┌─────────────┐   │ Last Msg │
│  │ Last Message │   │ Preview │
│  └─────────────┘   │         │
└─────────────────────────────────────┘
```

### **Glassmorphism Style**
```css
.agent-card {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.agent-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
}
```

### **Interactive Features**
- **Avatar**: 40px 원형, 배경색: 에이전트 역할 색상
- **Status Indicator**: 
  - 녹색 점: 온라인/활성
  - 회전 애니메이션 (1s)
  - 호버 시: glow 효과
- **Expand Button**: 
  - 클릭 시: 카드 확장
  - 전체 메시지 표시
  - 부드러운 전환 (300ms)

### **Quick Stats** (하단)
- 총 메시지 수
- 활성 에이전트 수
- 평균 응답 시간

### **Color Coding by Role**
- Manager: #4E7EBE (블루)
- Developer: #4A9B6F (그린)
- Designer: #7C6BA8 (퍼플)
- Researcher: #D4A055 (암버)

---

## Section 3: Chat Area

### **Message Layout** (Glassmorphism)
```
┌─────────────────────────────────────┐
│  Messages Container (scrollable)  │
│  ┌───────────────────────────┐  │
│  │ User Message             │  │
│  │ (right-aligned)           │  │
│  │  Avatar + Bubble       │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ Agent Message            │  │
│  │ (left-aligned)           │  │
│  │  Avatar + Card          │  │
│  │  Name + Timestamp        │  │
│  │  Content                 │  │
│  └───────────────────────────┘  │
└─────────────────────────────────────┘
```

### **Message Styles**
```css
/* User Message */
.user-message {
  background: rgba(79, 70, 229, 0.15); /* Purple */
  backdrop-filter: blur(10px);
  border-radius: 12px 12px 4px 12px;
  margin-left: auto;
  max-width: 70%;
}

/* Agent Message */
.agent-message {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 12px 4px 12px 12px;
  max-width: 70%;
}
```

### **Input Area**
```
┌─────────────────────────────────────┐
│  Textarea + Send Button          │
│  ┌─────────────┬────────────┐  │
│  │ Placeholder  │   Send 🚀  │  │
│  └─────────────┴────────────┘  │
└─────────────────────────────────────┘
```

### **Interactive Features**
- **Message Bubbles**:
  - 타이핑 애니메이션 (0.3s)
  - 호버 시: 미세한 그림자 효과
- **Timestamps**: 
  - 상대적 시간 (예: "2분 전")
  - 호버 시: 정확한 시간 표시
- **Typing Indicator**: 
  - 에이전트가 타이핑 중일 때 애니메이션
  - 점 3개가 순차적으로 깜빰임
- **Auto-scroll**: 
  - 새 메시지 시 부드러운 스크롤

---

## Section 4: Voting Panel

### **Tab Navigation**
```
┌─────────────────────────────────────┐
│  [투표] [통계]                     │
│  ─────────────────────────────── │
│  Active Tab: Underline + Bold     │
└─────────────────────────────────────┘
```

### **Voting View**
```
┌─────────────────────────────────────┐
│  Topic Card                        │
│  ┌───────────────────────────┐  │
│  │ Current Discussion Topic   │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ Candidates                │  │
│  │ 1. Option A               │  │
│  │ 2. Option B               │  │
│  │ 3. Option C               │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ Vote Cards (by Agent)     │  │
│  │ - Agent Avatar + Name      │  │
│  │ - Choice Badge             │  │
│  │ - Reasoning Preview        │  │
│  └───────────────────────────┘  │
└─────────────────────────────────────┘
```

### **Stats View**
```
┌─────────────────────────────────────┐
│  Model Usage Chart                 │
│  ┌───────────────────────────┐  │
│  │ V4 Usage: 70%             │  │
│  │ R1 Usage: 30%             │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ Stats Cards               │  │
│  │ - Total Calls             │  │
│  │ - Avg Response Time       │  │
│  │ - Cost Savings            │  │
│  └───────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## Section 5: Interactive Features

### **Context Menu**
- **Trigger**: Right-click on agent card
- **Options**:
  - View Full History
  - Export Conversation
  - Mute Agent
  - Request Clarification

### **Keyboard Shortcuts**
- `Cmd/Ctrl + K`: Focus input
- `Cmd/Ctrl + Enter`: Send message
- `Cmd/Ctrl + 1-4`: Switch agent tabs
- `Escape`: Close expanded view

### **Progress Indicators**
```css
.progress-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4E7EBE, #4A9B6F);
  animation: progress 1.5s ease-in-out;
}
```

---

## Section 6: Color & Typography

### **Color Palette**
```css
:root {
  /* Background */
  --bg-primary: #0f0f23;
  --bg-secondary: #1a1a2e;
  --bg-tertiary: #252530;
  
  /* Text */
  --text-primary: #ffffff;
  --text-secondary: rgba(255, 255, 255, 0.7);
  --text-tertiary: rgba(255, 255, 255, 0.5);
  
  /* Accent Colors */
  --accent-manager: #4E7EBE;
  --accent-developer: #4A9B6F;
  --accent-designer: #7C6BA8;
  --accent-researcher: #D4A055;
  
  /* Glassmorphism */
  --glass-bg: rgba(255, 255, 255, 0.15);
  --glass-border: rgba(255, 255, 255, 0.2);
  --glass-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}
```

### **Typography**
- **Font Family**: Inter, system-ui,blinkmacsystemfont, 'Segoe UI', sans-serif
- **Scale**:
  - **H1**: 2.5rem / 40px (titles)
  - **H2**: 1.5rem / 24px (section headers)
  - **H3**: 1.25rem / 20px (subsections)
  - **Body**: 1rem / 16px (normal text)
  - **Caption**: 0.875rem / 14px (small text)
- **Weights**:
  - **Light**: 300
  - **Regular**: 400
  - **Medium**: 500
  - **Semi-Bold**: 600
  - **Bold**: 700

---

## Section 7: Animations & Effects

### **Micro-interactions**
```css
/* Hover glow */
.hover-glow {
  box-shadow: 0 0 20px rgba(78, 70, 229, 0.3);
}

/* Click ripple */
@keyframes ripple {
  to {
    transform: scale(2);
    opacity: 0;
  }
}

/* Pulse effect */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
```

### **Transitions**
```css
/* Smooth transition */
.smooth-transition {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Bounce effect */
.bounce-enter {
  animation: bounceIn 0.5s;
}

@keyframes bounceIn {
  0% {
    opacity: 0;
    transform: translateY(10px);
  }
  60% {
    opacity: 1;
    transform: translateY(-5px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}
```

### **Loading States**
- **Skeleton**: Loading placeholder with pulse animation
- **Spinner**: Rotating icon for actions
- **Dots**: Three dots sequential fade

- **Progress**: Determinate/indeterminate progress bar

---

## Section 8: Technical Specs

### **Performance Targets**
- **First Contentful Paint**: < 1.5s
- **Time to Interactive**: < 3s
- **Bundle Size**: < 500KB (gzipped)
- **Lighthouse Score**: > 90

### **Browser Support**
- **Chrome**: 90+
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+
- **Mobile Safari**: 14+
- **Chrome Mobile**: 90+

### **Accessibility**
- **Keyboard Navigation**: 모든 인터랙티브 요소에 Tab 포커스
- **Focus Indicators**: 2px solid outline
- **ARIA Labels**: 모든 카드와 버튼에 label
- **Screen Reader**: 메시지 읽기 지원
- **Color Contrast**: WCAG AA 준수 (4.5:1)

- **Touch Targets**: 44px minimum

### **Responsive Breakpoints**
```css
/* Mobile */
@media (max-width: 767px) {
  .container {
    grid-template-columns: 1fr;
  }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1023px) {
  .container {
    grid-template-columns: 280px 1fr;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .container {
    grid-template-columns: 280px 1fr 320px;
  }
}
```

### **Code Quality**
- **TypeScript**: Strict mode
- **CSS**: Tailwind classes
- **Components**: Functional components
- **Testing**: Unit tests for critical paths
- **Documentation**: Storybook for UI components

---

## Section 9: Implementation Roadmap

### **Phase 1: Foundation** (1-2 days)
1. **Color & Typography System**
   - CSS 변수 정의
   - Tailwind 설정 업데이트
   - 기본 컴포넌트 스타일

2. **Glassmorphism Utilities**
   - 재사용 가능한 스타일 함수
   - backdrop-filter polyfills
   - 그라데이션 믹스인

### **Phase 2: Components** (3-4 days)
1. **Header Component**
   - 상태 표시줄
   - 테마 전환 버튼
   - 모델 정보

2. **Agent Card Component**
   - Glassmorphism 스타일
   - 인터랙티브 요소
   - 확장 애니메이션

3. **Message Components**
   - 사용자/에이전트 메시지
   - 타이핑 인디케이터
   - 타임스탬프

### **Phase 3: Integration** (2-3 days)
1. **Layout System**
   - 3-column 그리드
   - 반응형 레이아웃
   - 스크롤 동기화

2. **Interactive Features**
   - 컨텍스트 메뉴
   - 키보드 단축키
   - 진행 표시줄

3. **Testing & Polish**
   - 크로스 브라우저 테스트
   - 성능 최적화
   - 접근성 테스트

---

## Success Metrics
- **User Engagement**: +30% increase in session duration
- **Task Completion**: +25% faster task completion
- **Error Rate**: < 5% user errors
- **Performance**: < 2s average response time
- **Accessibility**: 100% WCAG AA compliance

---

## Next Steps
1. ✅ **Design Approved** (2026-04-03)
2. ⏳ **User Reviews Spec** (pending)
3. ⏳ **Invoke writing-plans skill** (pending)
