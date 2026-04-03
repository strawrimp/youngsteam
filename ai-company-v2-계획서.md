# AI 가상 회사 v2 — 4개 시스템 통합 설계

## Context

기존 시스템(`my-ai-company`)은 작동하지만 두 가지 핵심 문제가 있음:
1. **디자인이 프로페셔널하지 않음** — 다크 모드 + 프리미엄 SaaS로 재설계
2. **에이전트 간 대화/토론 기능 부재** — 에이전트가 서로 의견을 교환하지 못함

3개 오픈소스(Mission Control, ClawTeam, SwarmClaw) + 기존 시스템의 장점만 재조합하여 **최고의 멀티-에이전트 협업 도구**를 만든다.

---

## 각 시스템에서 가져올 것 / 버릴 것

### 기존 시스템 (my-ai-company)
| 가져올 것 ✅ | 버릴 것 ❌ |
|-------------|-----------|
| FastAPI 백엔드 구조 (Engine/Service/Agent 분리) | UI/프론트엔드 전체 |
| DeepSeek V4+R1 하이브리드 전략 | 단순 병렬 응답 방식 |
| VotingEngine (다수결+동점처리) | 에이전트별 독립 conversation_history |
| WebSocket 실시간 통신 기반 | Semaphore(2) 과도한 제한 |

### Mission Control (builderz-labs)
| 가져올 것 ✅ | 버릴 것 ❌ |
|-------------|-----------|
| SmartPoll + SSE 하이브리드 실시간 패턴 | 47개 패널 (과도, 우리는 5개면 충분) |
| SOUL 시스템 (에이전트 성격 정의 템플릿) | SQLite WAL (우리는 PostgreSQL 유지) |
| Agent Heartbeat 상태 추적 | RBAC 3단계 (불필요) |
| Agent-to-Agent Comms API 구조 | |
| Zustand + subscribeWithSelector 상태관리 | |

### SwarmClaw (swarmclawai)
| 가져올 것 ✅ | 버릴 것 ❌ |
|-------------|-----------|
| LLM 다중 제공자 추상화 (Handler 패턴) | 암호화폐 지갑 통합 |
| OpenAI 호환 엔드포인트 패칭 패턴 | Discord/Slack/Telegram 통합 (향후) |
| Failover + jittered backoff | 데몬 모드 |
| Task Board (queue/running/completed/cancelled) | |

### ClawTeam (HKUDS)
| 가져올 것 ✅ | 버릴 것 ❌ |
|-------------|-----------|
| Inbox/Outbox 에이전트 간 메시징 개념 | 파일 기반 전송 (WebSocket으로 대체) |
| Broadcast + Point-to-point 메시지 패턴 | tmux/git worktree 격리 (불필요) |
| 자동 주입 조율 프롬프트 개념 | CLI 명령어 인터페이스 |
| 리더-워커 토론 라운드 구조 | ZeroMQ P2P (WebSocket으로 대체) |

---

## 통합 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│                    Next.js 15 Frontend                       │
│    ┌──────────┬──────────────┬──────────┬─────────────┐     │
│    │ Agent    │ Chat +       │ Debate   │ Vote +      │     │
│    │ Panel    │ Discussion   │ Theater  │ Decision    │     │
│    │ [MC참고] │              │ [신규]   │ Log         │     │
│    └──────────┴──────────────┴──────────┴─────────────┘     │
│    Zustand Store [MC패턴] + Geist Font + Dark Theme          │
└────────────────────────┬─────────────────────────────────────┘
                         │ WebSocket + SSE [MC패턴]
┌────────────────────────▼─────────────────────────────────────┐
│                  FastAPI Backend (기존 확장)                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ConversationEngine (기존 확장)                        │   │
│  │  ├─ process_message()     [기존: User→Agents]        │   │
│  │  ├─ start_debate()        [신규: Agent↔Agent 토론]   │   │
│  │  └─ start_voting_with_discussion() [신규: 토론→투표] │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │ DebateEngine     │  │ AgentMessageBroker              │   │
│  │ [신규]           │  │ [ClawTeam Inbox/Outbox 개념]    │   │
│  │                  │  │                                 │   │
│  │ • multi-round    │  │ • send_to_agent()               │   │
│  │ • shared context │  │ • broadcast()                   │   │
│  │ • mode selection │  │ • get_inbox()                   │   │
│  │   (debate/       │  │ • message_history               │   │
│  │    brainstorm/   │  │                                 │   │
│  │    consensus)    │  │ Transport: WebSocket (not file) │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │ VotingEngine     │  │ LLMProviderService              │   │
│  │ (기존 확장)      │  │ [SwarmClaw Handler 패턴]        │   │
│  │                  │  │                                 │   │
│  │ • pre-vote       │  │ • DeepSeek V4/R1 [기존]        │   │
│  │   discussion     │  │ • OpenAI (추가)                 │   │
│  │ • context-aware  │  │ • Claude (추가)                 │   │
│  │   voting         │  │ • Ollama local (추가)           │   │
│  │ • decision log   │  │ • Failover [SwarmClaw패턴]      │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │ MemoryService    │  │ SOUL Personality [MC패턴]       │   │
│  │ (기존 확장)      │  │                                 │   │
│  │                  │  │ • 에이전트별 성격 템플릿         │   │
│  │ • debate logs    │  │ • {{AGENT_NAME}} 치환           │   │
│  │ • agent beliefs  │  │ • 토론 스타일 정의              │   │
│  │ • decision hist  │  │ • 역할별 전문성 가중치          │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
│                                                              │
│  DB: PostgreSQL (기존) ─ agents, messages, debates, votes    │
└──────────────────────────────────────────────────────────────┘
```

---

## 핵심 신규 기능: DebateEngine

현재 시스템의 가장 큰 약점을 해결하는 핵심 모듈.

### 토론 흐름

```
사용자: "새 기능을 출시해야 할까?"
    │
    ▼
[DebateEngine.start_debate()]
    │
    ▼
━━━━ Round 1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│                                                │
│  Manager → (사용자 질문 읽음)                    │
│    "리스크가 있다. 시장 반응을 먼저 봐야 한다"    │
│                                                │
│  Developer → (사용자 질문 + Manager 의견 읽음)    │
│    "기술적으로 준비됐다. 테스트 커버리지 92%"     │
│                                                │
│  Designer → (위 모두 읽음)                       │
│    "UX 관점에서 출시 가능하나 온보딩 개선 필요"    │
│                                                │
│  Researcher → (위 모두 읽음)                     │
│    "데이터: 경쟁사 출시 예정, 2주 내 선점 필요"   │
│                                                │
━━━━ Round 2 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│                                                │
│  Manager → (Round 1 전체 읽음)                   │
│    "Researcher 데이터 고려 시 출시가 맞다.       │
│     단, Designer의 온보딩 이슈는 해결해야"       │
│                                                │
│  Developer → (Round 1 + Manager R2 읽음)         │
│    "온보딩 개선은 3일이면 가능"                   │
│                                                │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    │
    ▼
[VotingEngine (토론 컨텍스트 포함)]
    │
    ▼
최종 결정 + 근거 기록
```

### 핵심 구현 파일

**`backend/engines/debate_engine.py` (신규)**
```python
class DebateEngine:
    async def start_debate(
        self,
        topic: str,
        agent_ids: List[str],
        num_rounds: int = 2,
        mode: str = "debate"  # debate | brainstorm | consensus
    ) -> DebateResult

    async def _run_round(
        self,
        round_num: int,
        topic: str,
        previous_messages: List[DebateMessage]
    ) -> List[DebateMessage]
```

**`backend/agents/agent_message_broker.py` (신규)**
```python
class AgentMessageBroker:
    async def send_to_agent(from_id, to_id, message, context)
    async def broadcast(from_id, message, context)
    def get_inbox(agent_id) -> List[Message]
    def get_debate_context(debate_id) -> List[Message]
```

**`backend/agents/base_agent.py` (확장)**
```python
# 기존 메서드 유지 + 추가:
async def respond_to_debate(
    self,
    topic: str,
    previous_messages: List[Dict],  # 다른 에이전트 의견
    round_num: int,
    mode: str = "debate"
) -> str
```

---

## LLM 다중 제공자 통합 (SwarmClaw 패턴)

**`backend/services/llm_provider_service.py` (신규 — DeepSeekService 확장)**
```python
class LLMProviderService:
    providers: Dict[str, ProviderHandler]  # SwarmClaw Handler 패턴

    # 기존 DeepSeek V4/R1 유지
    # + OpenAI, Claude, Ollama 추가
    # + Failover with jittered backoff

    async def call(
        self,
        provider: str,        # "deepseek" | "openai" | "claude" | "ollama"
        messages: List[Dict],
        task_type: str,
        fallback_providers: List[str] = []
    ) -> LLMResponse
```

기존 `DeepSeekService`를 `LLMProviderService`의 **하위 provider**로 래핑. 기존 코드 깨지지 않음.

---

## SOUL 성격 시스템 (Mission Control 패턴)

**`backend/agents/soul/` (신규 디렉토리)**
```
soul/
├── templates/
│   ├── manager.md     # "당신은 전략적 리더입니다. 항상 비즈니스 관점에서..."
│   ├── developer.md   # "당신은 기술 전문가입니다. 코드 품질을 최우선..."
│   ├── designer.md    # "당신은 사용자 경험 전문가입니다..."
│   └── researcher.md  # "당신은 데이터 기반 분석가입니다..."
├── debate_styles/
│   ├── assertive.md   # "상대 의견에 적극 반박하라"
│   ├── diplomatic.md  # "상대 의견을 존중하되 대안 제시"
│   └── analytical.md  # "데이터와 근거만으로 판단하라"
└── loader.py          # 템플릿 로딩 + {{변수}} 치환
```

현재 각 에이전트의 하드코딩된 system_prompt → SOUL 템플릿으로 교체.

---

## 프론트엔드 설계 (다크 모드 + 프리미엄 SaaS)

### 기술 스택
| 레이어 | 기술 | 출처 |
|--------|------|------|
| 프레임워크 | Next.js 15 + TypeScript | Mission Control 패턴 |
| 스타일 | Tailwind CSS v4 + CSS Variables | 다크 모드 토큰 |
| 컴포넌트 | shadcn/ui | 프리미엄 SaaS |
| 상태관리 | Zustand + subscribeWithSelector | Mission Control 패턴 |
| 실시간 | WebSocket + SSE (SmartPoll) | Mission Control 패턴 |
| 폰트 | Geist | Vercel 스타일 |

### 레이아웃 구조
```
┌─────────────────────────────────────────────────────────┐
│  ▸ AI Virtual Company          [🌙] [⚙]   ← 최소 헤더 │
├────────┬───────────────────────────────┬────────────────┤
│        │                               │                │
│ Agent  │   Main Area                   │  Context       │
│ Panel  │   ┌─ Chat Tab ──────────┐     │  Panel         │
│        │   │ 일반 대화            │     │                │
│ [MC    │   ├─ Debate Tab ────────┤     │  ┌─ Vote ──┐  │
│  패턴] │   │ 에이전트 토론 극장    │     │  │ 투표     │  │
│        │   ├─ History Tab ───────┤     │  ├─ Stats ─┤  │
│ • 상태 │   │ 결정 이력            │     │  │ 통계     │  │
│ • SOUL │   └─────────────────────┘     │  ├─ Log ───┤  │
│ • 하트 │                               │  │ 결정로그 │  │
│   비트 │   [Input Area]                │  └─────────┘  │
│        │                               │                │
├────────┼───────────────────────────────┼────────────────┤
│ 240px  │         flex-1                │    300px       │
└────────┴───────────────────────────────┴────────────────┘
```

### 다크 모드 토큰
```css
:root {
  --bg-primary: #0a0a0a;
  --bg-secondary: #111111;
  --bg-elevated: #1a1a1a;
  --border: rgba(255,255,255,0.08);
  --border-hover: rgba(255,255,255,0.15);
  --text-primary: #fafafa;
  --text-secondary: #888888;
  --agent-manager: #5B8DEF;
  --agent-developer: #4ADE80;
  --agent-designer: #A78BFA;
  --agent-researcher: #FCD34D;
}
```

---

## 프로젝트 구조 (최종)

```
ai-company-v2/
│
├── frontend/                          # Next.js 15
│   ├── app/
│   │   ├── layout.tsx                 # 다크 모드 루트
│   │   ├── page.tsx                   # 3-column 대시보드
│   │   └── api/                       # BFF (Backend-for-Frontend)
│   ├── components/
│   │   ├── ui/                        # shadcn
│   │   ├── agents/                    # AgentPanel, AgentCard, SoulEditor
│   │   ├── chat/                      # ChatWindow, MessageBubble
│   │   ├── debate/                    # DebateTheater, RoundView, AgentSpeech
│   │   └── voting/                    # VotePanel, DecisionLog
│   ├── stores/                        # Zustand [MC패턴]
│   │   ├── agent-store.ts
│   │   ├── chat-store.ts
│   │   ├── debate-store.ts
│   │   └── vote-store.ts
│   └── styles/globals.css             # 다크 모드 CSS Variables
│
├── backend/                           # FastAPI (기존 코드 확장)
│   ├── main.py                        # 기존 + debate/soul 엔드포인트
│   ├── config.py                      # 기존 + LLM provider 설정
│   ├── engines/
│   │   ├── conversation_engine.py     # 기존 확장: start_debate()
│   │   ├── debate_engine.py           # [신규] 멀티라운드 토론
│   │   └── voting_engine.py           # 기존 확장: pre-vote discussion
│   ├── agents/
│   │   ├── base_agent.py              # 확장: respond_to_debate()
│   │   ├── manager_agent.py           # 기존 유지
│   │   ├── developer_agent.py         # 기존 유지
│   │   ├── designer_agent.py          # 기존 유지
│   │   ├── researcher_agent.py        # 기존 유지
│   │   ├── agent_message_broker.py    # [신규] ClawTeam 개념
│   │   └── soul/                      # [신규] MC SOUL 패턴
│   │       ├── templates/
│   │       ├── debate_styles/
│   │       └── loader.py
│   ├── services/
│   │   ├── llm_provider_service.py    # [신규] SwarmClaw 패턴
│   │   ├── deepseek_service.py        # 기존 유지 (provider로 래핑)
│   │   └── memory_service.py          # 기존 확장
│   └── models/
│       ├── (기존 모델 유지)
│       ├── debate.py                  # [신규]
│       └── agent_message.py           # [신규]
│
└── shared/                            # 프론트/백엔드 공유 타입
    └── types.ts
```

---

## 실행 순서

### Phase 1: 프론트엔드 셸 (1주)
1. Next.js 15 프로젝트 생성
2. 다크 모드 디자인 시스템 구축 (CSS Variables + Tailwind)
3. 3-column 레이아웃 + shadcn 기본 컴포넌트
4. `/design-shotgun`으로 시안 생성 후 확정

### Phase 2: 백엔드 핵심 확장 (1주)
1. `DebateEngine` 구현 (멀티라운드 토론)
2. `AgentMessageBroker` 구현 (에이전트 간 메시징)
3. `base_agent.py`에 `respond_to_debate()` 추가
4. WebSocket에 debate 스트리밍 추가

### Phase 3: SOUL + LLM 다중 제공자 (1주)
1. SOUL 템플릿 시스템 구현
2. `LLMProviderService` 구현 (DeepSeek 래핑 + OpenAI/Claude 추가)
3. Failover 메커니즘

### Phase 4: 프론트엔드 기능 연결 (1주)
1. AgentPanel + Heartbeat 연결
2. ChatWindow + WebSocket 연결
3. DebateTheater UI (토론 실시간 스트리밍)
4. VotePanel + DecisionLog

### Phase 5: 통합 테스트 + 폴리싱 (1주)
1. 토론 → 투표 전체 흐름 테스트
2. 다크 모드 완성도 검증
3. 반응형 레이아웃 확인
4. 에러 핸들링 + 엣지 케이스

---

## 검증 방법

1. `cd ai-company-v2/frontend && npm run dev` → localhost:3000
2. `cd ai-company-v2/backend && uvicorn main:app --port 8000`
3. 채팅 전송 → 에이전트 응답 확인 (WebSocket)
4. 토론 시작 → 에이전트 간 대화 실시간 스트리밍 확인
5. 토론 후 투표 → 토론 컨텍스트 반영된 투표 결과 확인
6. 다크/라이트 모드 토글 확인
7. SOUL 편집 → 에이전트 응답 스타일 변화 확인

---

# AI 가상 회사 (Multi-Agent System) 구현 계획 (원본)

## Context

사용자는 대화형 웹 환경에서 다양한 역할(개발, 디자인, 연구)을 수행하는 AI 에이전트들이 동등하게 참여하여 투표로 의견을 수렴하는 "나만의 AI 가상 회사"를 구축하려고 합니다. 공유 메모리 시스템으로 모든 에이전트가 같은 컨텍스트를 유지하고, 사용자는 관리자 중심으로도 + 필요시 개별 에이전트와도 직접 대화할 수 있습니다.

이는 완전히 새로운 프로젝트로, 멀티-에이전트 협업 시스템의 기초 인프라부터 구축해야 합니다.

---

## 기술 스택 (확정)

| 계층 | 기술 |
|------|------|
| **백엔드** | Python 3.11+ + FastAPI |
| **프론트엔드** | React 18+ + TypeScript |
| **데이터베이스** | PostgreSQL 14+ |
| **AI 모델** | GLM (Zhipu AI) - 우선, 변경 가능한 구조 |
| **통신** | WebSocket (실시간) + REST API |
| **이미지 생성** | 외부 API (DALL-E, GLM Vision, 등) |
| **환경** | 로컬 개발 (Docker 또는 venv) |

---

## 핵심 설계 결정

1. **의견 수렴**: 투표 방식 (모든 에이전트 동등 참여)
2. **사용자 인터페이스**: 혼합형 (관리자 중심 + 직접 대화 가능)
3. **에이전트 간 통신**: 동기 (직접 프롬프트 교환, WebSocket으로 구현)
4. **공유 메모리 범위**: 회사 전략/목표 + 진행 중인 프로젝트 + 주요 결정사항과 근거
5. **자동화**: 정기 회의 없음 (모두 사용자 또는 에이전트 주도적)

---

## 시스템 아키텍처

### 전체 다이어그램 (텍스트 형식)

```
┌─────────────────────────────────────────────────┐
│        Frontend (React + TypeScript)             │
│  - ChatWindow, AgentPanel, VotingUI             │
│  - MemoryPanel, ImageInput/Output               │
│  - ConversationHistory, DecisionLog             │
└────────────────┬────────────────────────────────┘
                 │ WebSocket + REST API
┌────────────────▼────────────────────────────────┐
│      Backend (FastAPI - Python)                 │
│  ┌─ Agent Manager (에이전트 생명주기)           │
│  ├─ Conversation Engine (대화/토론 관리)        │
│  ├─ Voting Engine (투표/컨센서스)               │
│  ├─ Memory System (PostgreSQL 인터페이스)       │
│  ├─ GLM Wrapper (모델 통신 추상화)              │
│  ├─ Image Processor (생성/분석)                 │
│  └─ WebSocket Manager (실시간 통신)            │
└────────────────┬────────────────────────────────┘
                 │
         ┌───────▼────────┐
         │   PostgreSQL   │
         │  - conversations
         │  - messages
         │  - agents
         │  - shared_memory
         │  - decisions
         │  - votes
         └────────────────┘
```

---

## 백엔드 구조 (FastAPI)

### 파일 구조

```
backend/
├── main.py                    # 애플리케이션 진입점
├── config.py                  # 설정 (DB, API 키, 모델 등)
├── database.py                # PostgreSQL 연결 풀
├── requirements.txt           # 의존성
│
├── models/                    # 데이터 모델 (SQLAlchemy ORM)
│   ├── agent.py              # Agent 테이블
│   ├── conversation.py        # Conversation 테이블
│   ├── message.py            # Message 테이블
│   ├── shared_memory.py       # SharedMemory 테이블
│   ├── decision.py           # Decision 테이블
│   ├── vote.py               # Vote 테이블
│   └── image.py              # Image 테이블
│
├── schemas/                   # Pydantic 요청/응답 스키마
│   ├── agent.py              # AgentCreate, AgentResponse
│   ├── message.py            # MessageCreate, MessageResponse
│   ├── voting.py             # VotingRequest, VotingResponse
│   └── memory.py             # MemoryRequest, MemoryResponse
│
├── agents/                    # 에이전트 시스템
│   ├── base_agent.py         # BaseAgent 추상 클래스
│   ├── manager_agent.py      # ManagerAgent (관리자)
│   ├── developer_agent.py    # DeveloperAgent (코딩)
│   ├── designer_agent.py     # DesignerAgent (이미지)
│   ├── researcher_agent.py   # ResearcherAgent (조사/분석)
│   └── agent_factory.py      # 에이전트 팩토리 패턴
│
├── engines/
│   ├── conversation_engine.py # 대화 관리 및 라우팅
│   ├── voting_engine.py      # 투표 로직, 컨센서스 도출
│   └── discussion_engine.py  # 에이전트 간 토론 플로우
│
├── services/
│   ├── memory_service.py     # 공유 메모리 CRUD
│   ├── glm_service.py        # GLM API 통신 (확장 가능)
│   ├── image_service.py      # 이미지 생성/분석 (DALL-E, GLM Vision 등)
│   └── agent_service.py      # 에이전트 상태 관리
│
├── routes/                    # API 엔드포인트
│   ├── chat.py               # POST /chat, WebSocket /ws
│   ├── agents.py             # GET /agents, POST /agents/{id}
│   ├── voting.py             # POST /voting/start, /voting/vote
│   ├── memory.py             # GET/POST /memory
│   └── images.py             # POST /images/generate, /images/analyze
│
└── utils/
    ├── logging.py            # 로깅 설정
    └── validators.py         # 입력 검증
```

### 핵심 모듈 설명

**1. BaseAgent (agents/base_agent.py)**
```
- 모든 에이전트의 부모 클래스
- 속성: id, name, role, system_prompt, model
- 메서드:
  * think(context) → 추론 실행, GLM 호출
  * respond(message) → 메시지 처리
  * get_context() → 현재 대화 컨텍스트 반환
  * get_memory() → 공유 메모리 조회
```

**2. ConversationEngine (engines/conversation_engine.py)**
```
- 사용자 메시지 수신 → 적절한 에이전트로 라우팅
- 에이전트 응답 수집 및 포맷팅
- 토론 시작/진행/종료 관리
- WebSocket을 통한 실시간 메시지 배송
```

**3. VotingEngine (engines/voting_engine.py)**
```
- 투표 세션 생성 (topic, candidates)
- 각 에이전트의 투표 수집
- 컨센서스 도출:
  * 단순 다수결 (1에이전트 = 1표)
  * 동점 시: 관리자 에이전트의 최종 판단
- 투표 결과 저장 및 히스토리 유지
```

**4. MemoryService (services/memory_service.py)**
```
- shared_memory 테이블과 인터페이스
- CRUD 메서드
  * save(category, content, created_by)
  * fetch(category) → 최신 항목
  * history(category) → 변경 이력
  * search(keyword) → 키워드 검색
```

**5. GLMService (services/glm_service.py)** - 확장 가능 구조
```
- GLM API 호출 추상화
- 향후 모델 변경 시 이 부분만 수정
- 메서드:
  * call_model(prompt, system_prompt, temperature)
  * stream_response() → 스트리밍 응답
- 다른 모델(Claude, GPT 등) 추가 시:
  * 같은 인터페이스로 구현
  * ConversationEngine은 변경 없음
```

**6. ImageService (services/image_service.py)**
```
- DALL-E API 호출 (또는 Stable Diffusion, GLM Vision)
- 메서드:
  * generate(prompt) → 이미지 생성 → URL/경로 반환
  * analyze(image_path) → 이미지 분석 (GLM Vision)
  * store_image(url, metadata) → DB에 저장
```

---

## 프론트엔드 구조 (React + TypeScript)

### 파일 구조

```
frontend/src/
├── index.tsx
├── App.tsx
│
├── pages/
│   └── MainDashboard.tsx      # 메인 대시보드
│
├── components/
│   ├── ChatWindow.tsx         # 메인 채팅 영역
│   ├── AgentPanel.tsx         # 에이전트 목록 & 상태
│   ├── VotingInterface.tsx    # 투표 UI
│   ├── MemoryPanel.tsx        # 공유 메모리 뷰
│   ├── ConversationHistory.tsx # 대화 이력
│   ├── ImageInput.tsx         # 이미지 업로드
│   ├── ImageOutput.tsx        # 생성된 이미지 표시
│   └── Message.tsx            # 개별 메시지 컴포넌트
│
├── hooks/
│   ├── useWebSocket.ts        # WebSocket 연결
│   ├── useConversation.ts     # 대화 상태 관리
│   └── useVoting.ts           # 투표 상태 관리
│
├── services/
│   ├── api.ts                 # REST API 호출 (axios)
│   ├── websocket.ts           # WebSocket 매니저
│   └── store.ts               # 로컬 상태 관리 (Zustand 또는 Context)
│
├── styles/
│   ├── global.css
│   └── components.module.css
│
└── types/
    ├── agent.ts               # Agent 타입
    ├── message.ts             # Message 타입
    ├── voting.ts              # Voting 타입
    └── memory.ts              # Memory 타입
```

### 주요 컴포넌트 상세

**1. ChatWindow.tsx**
```
- 메시지 목록 (스크롤 가능)
- 입력 필드 (텍스트, 이미지)
- 에이전트별 색상 구분
- 타이핑 인디케이터 ("에이전트가 생각 중...")
```

**2. VotingInterface.tsx**
```
- 투표 주제 표시
- 각 에이전트의 의견 카드 (선택 가능)
- 투표 버튼
- 실시간 투표 진행률 바
- 결과 표시
```

**3. MemoryPanel.tsx**
```
- 카테고리별 탭 (전략, 목표, 프로젝트, 결정사항)
- 각 항목의 생성자, 생성일, 내용 표시
- 변경 이력 보기
- 검색 기능
```

---

## 데이터베이스 설계 (PostgreSQL)

### 필수 테이블 (SQL 스키마)

```sql
-- Agents 테이블
CREATE TABLE agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL,
  role VARCHAR(50) NOT NULL,  -- manager, developer, designer, researcher
  status VARCHAR(20) DEFAULT 'active',
  system_prompt TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversations 테이블
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(255),
  is_voting BOOLEAN DEFAULT FALSE,
  started_at TIMESTAMP DEFAULT NOW(),
  ended_at TIMESTAMP NULL
);

-- Messages 테이블
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
  content TEXT NOT NULL,
  message_type VARCHAR(20) DEFAULT 'text',  -- text, image, decision
  created_at TIMESTAMP DEFAULT NOW()
);

-- SharedMemory 테이블
CREATE TABLE shared_memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category VARCHAR(50) NOT NULL,  -- strategy, goal, project, decision
  content TEXT NOT NULL,
  created_by UUID REFERENCES agents(id),
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Decisions 테이블
CREATE TABLE decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id),
  topic TEXT NOT NULL,
  final_decision TEXT NOT NULL,
  voting_result JSONB,  -- {agent_id: choice, ...}
  created_at TIMESTAMP DEFAULT NOW()
);

-- Votes 테이블
CREATE TABLE votes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID REFERENCES decisions(id) ON DELETE CASCADE,
  agent_id UUID REFERENCES agents(id),
  choice TEXT NOT NULL,
  reasoning TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Images 테이블
CREATE TABLE images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url VARCHAR(500),
  local_path VARCHAR(255),
  metadata JSONB,
  created_by UUID REFERENCES agents(id),
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 에이전트 시스템 설계

### 에이전트 기본 구조

```python
# agents/base_agent.py
class BaseAgent:
    def __init__(self, agent_id, name, role, system_prompt):
        self.id = agent_id
        self.name = name
        self.role = role
        self.system_prompt = system_prompt

    async def think(self, conversation_context: str) -> str:
        """컨텍스트를 받아 GLM에 호출하고 응답 반환"""
        pass

    async def respond(self, message: str) -> str:
        """메시지를 처리하고 응답 생성"""
        pass

    def get_memory(self) -> dict:
        """공유 메모리 조회"""
        pass

    async def vote(self, topic: str, candidates: list) -> dict:
        """투표에 참여 (의견 + 추론)"""
        pass
```

### 각 에이전트 역할별 System Prompt 템플릿

**Manager Agent (관리자)**
```
당신은 AI 회사의 CEO입니다. 역할:
- 전략 수립 및 우선순위 결정
- 팀원들의 의견을 종합하여 최종 판단
- 목표 수립 및 진행 상황 추적

[공유 메모리: 현재 전략, 목표, 프로젝트]
[최근 팀 의견들]

이제 [사용자 요청]에 대해 당신의 의견을 제시하세요. 다른 팀원들의 의견도 고려하세요.
```

**Developer Agent (개발)**
```
당신은 AI 회사의 기술 리드입니다. 전문:
- Python, JavaScript, 아키텍처 설계
- 기술적 실현 가능성 평가
- 코드 작성 및 리뷰

[공유 메모리: 현재 기술 스택, 진행 중인 개발]

이제 [사용자 요청]에 대해 기술적 관점에서 답변하세요.
```

**Designer Agent (디자인)**
```
당신은 AI 회사의 디자인 리드입니다. 전문:
- UI/UX 설계
- 이미지 생성 및 분석 (DALL-E, Vision API 사용)
- 시각적 일관성 유지

[공유 메모리: 현재 디자인 시스템, 브랜드 가이드]

이제 [사용자 요청]에 대해 디자인 관점에서 답변하세요.
```

**Researcher Agent (연구)**
```
당신은 AI 회사의 리서치 리드입니다. 전문:
- 자료 조사 및 분석
- 시장 트렌드, 기술 분석
- 근거 기반 인사이트 제공

[공유 메모리: 최근 리서치 결과, 시장 정보]

이제 [사용자 요청]에 대해 리서치 관점에서 답변하세요.
```

---

## 토론 및 투표 엔진

### 투표 프로세스 (Step-by-Step)

```
1. 토론 주제 발의 (사용자 또는 에이전트)
   → 예: "새로운 기능 우선순위 결정"

2. 각 에이전트가 의견 제시 (순차적)
   → 각 에이전트: 의견 + 근거 생성 (GLM 호출)
   → 모두가 볼 수 있도록 채팅에 표시

3. 투표 시작 선언 (관리자 또는 사용자)

4. 각 에이전트가 투표 선택지 중 선택
   → DB에 votes 테이블에 저장

5. 컨센서스 도출
   - 단순 다수결: 가장 많은 표를 받은 항목
   - 동점: 관리자 에이전트가 최종 판단

6. 결과 발표 및 결정 저장
   → decisions 테이블에 저장
   → shared_memory에 기록
```

### 컨센서스 로직

```python
# engines/voting_engine.py
class VotingEngine:
    def calculate_consensus(votes: dict) -> tuple:
        """
        votes = {agent_id: choice}
        return (winning_choice, voting_breakdown)
        """
        vote_counts = Counter(votes.values())
        winner = vote_counts.most_common(1)[0]

        if len(vote_counts) > 1 and vote_counts[0][1] == vote_counts[1][1]:
            # 동점 → 관리자 에이전트의 판단 필요
            return None, "TIED"

        return winner, vote_counts

    async def resolve_tie(decision_topic: str, candidates: list) -> str:
        """관리자가 최종 판단"""
        manager = get_agent("manager")
        manager_vote = await manager.vote(decision_topic, candidates)
        return manager_vote["choice"]
```

---

## API 엔드포인트 (FastAPI)

### REST API

```
POST /chat/message
  요청: {text: string, conversation_id?: UUID}
  응답: {message_id: UUID, agent_responses: [...]}

GET /agents
  응답: [{id, name, role, status}]

POST /voting/start
  요청: {topic: string, candidates: [string]}
  응답: {voting_id: UUID}

POST /voting/vote
  요청: {voting_id: UUID, agent_id: UUID, choice: string}
  응답: {success: boolean}

GET /voting/{voting_id}/result
  응답: {winner: string, breakdown: {...}, tied: boolean}

GET /memory?category=strategy
  응답: [{id, category, content, created_by, created_at}]

POST /memory
  요청: {category: string, content: string}
  응답: {memory_id: UUID}

POST /images/generate
  요청: {prompt: string}
  응답: {image_url: string, image_id: UUID}

POST /images/analyze
  요청: {image_url: string}
  응답: {analysis: string}
```

### WebSocket

```
ws://localhost:8000/ws?conversation_id={uuid}

메시지 포맷 (양방향):
{
  type: "message" | "thinking" | "voting_update",
  agent_id: UUID,
  content: string,
  timestamp: ISO8601
}
```

---

## 구현 단계 (Phase-based)

### Phase 1: 기본 인프라 (1주)
**목표**: 프레임워크 구축, DB 스키마, 기본 통신

- [ ] FastAPI 서버 세팅 (config, DB 연결)
- [ ] PostgreSQL 데이터베이스 및 테이블 생성
- [ ] React 기본 구조 (ChatWindow 뼈대)
- [ ] WebSocket 연결 구현
- [ ] 간단한 echo 테스트 (사용자 메시지 → 에이전트 echo 반환)

**검증**:
- `curl localhost:8000/agents` 응답 확인
- WebSocket 연결 성공 확인

---

### Phase 2: 단일 에이전트 시스템 (1주)
**목표**: Manager Agent + Developer Agent 동작

- [ ] BaseAgent, ManagerAgent, DeveloperAgent 구현
- [ ] GLMService 구현 (GLM API 호출)
- [ ] ConversationEngine 구현 (라우팅)
- [ ] MemoryService 구현
- [ ] React ChatWindow 완성 (메시지 표시, 입력)

**검증**:
- 사용자가 "안녕"이라고 입력 → 관리자가 응답
- 사용자가 "이 코드를 검토해줄래?"라고 입력 → 개발자가 응답
- 공유 메모리에 저장된 내용 조회 가능

---

### Phase 3: 토론 엔진 및 투표 (1주)
**목표**: 다중 에이전트 토론 및 의견 수렴

- [ ] Researcher Agent, Designer Agent 추가
- [ ] VotingEngine 구현
- [ ] DiscussionEngine 구현 (모든 에이전트의 의견 수집)
- [ ] React VotingInterface 구현
- [ ] AgentPanel 구현

**검증**:
- "새 기능 우선순위 결정해줄래?"
  → 4명 에이전트가 모두 의견 제시
  → 투표 진행
  → 결과 표시 및 저장

---

### Phase 4: 이미지 처리 (1주)
**목표**: 이미지 생성/분석 기능

- [ ] ImageService 구현 (DALL-E)
- [ ] Designer Agent에 이미지 생성 능력 추가
- [ ] React ImageInput, ImageOutput 구현
- [ ] 이미지 업로드 및 분석 기능

**검증**:
- Designer: "로고를 디자인해줄래? '파란색 AI 로봇'"
- 로고 이미지 생성 및 채팅에 표시
- "이 디자인에 대해 의견을 주세요"
- 이미지 분석 결과 표시

---

### Phase 5: UI 고도화 및 최적화 (1주)
**목표**: 사용성 및 성능 개선

- [ ] ConversationHistory 구현
- [ ] MemoryPanel 고도화 (검색, 필터링)
- [ ] 스타일링 및 반응형 디자인
- [ ] 에러 처리 및 로깅
- [ ] 성능 최적화 (메시지 페이지네이션)

**검증**:
- 전체 UI 흐름이 자연스러운지 확인
- 대화 이력 조회 가능
- 메모리 검색 기능 정상 작동

---

## 확장성 가이드

### 새 에이전트 추가 (예: MarketingAgent)

```python
# Step 1: agents/marketing_agent.py 생성
class MarketingAgent(BaseAgent):
    def __init__(self, ...):
        super().__init__(...)
        self.role = "marketing"

# Step 2: agents/agent_factory.py 수정
def create_agent(role: str):
    if role == "marketing":
        return MarketingAgent(...)

# Step 3: config.py에 에이전트 초기화
AGENTS_CONFIG = {
    ...
    "marketing": {
        "system_prompt": "당신은 마케팅 리드입니다...",
    }
}

# Step 4: 프론트엔드 AgentPanel.tsx 수정
AGENT_COLORS = {
    ...
    "marketing": "#FF6B6B",  # 빨간색
}
```

### AI 모델 변경 (GLM → Claude)

```python
# Step 1: services/claude_service.py 생성
class ClaudeService:
    async def call_model(self, prompt, system_prompt):
        # Claude API 호출

# Step 2: services/__init__.py 수정
# GLMService → ClaudeService로 변경 (같은 인터페이스)

# Step 3: 나머지는 변경 없음 (BaseAgent, ConversationEngine 등)
```

---

## 배포 및 운영

### 로컬 개발 환경 구성

**Option A: venv 사용 (간단)**
```bash
# 백엔드
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 프론트엔드
cd frontend
npm install

# PostgreSQL
brew install postgresql
createdb ai_company

# 실행
cd backend && uvicorn main:app --reload
cd frontend && npm start
```

**Option B: Docker 사용 (권장)**
```dockerfile
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: ai_company
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### 필수 환경 변수 (.env)

```
# GLM API
GLM_API_KEY=xxxxxxxxxxxx
GLM_MODEL=glm-4
GLM_TEMPERATURE=0.7

# 이미지 생성 (DALL-E 또는 다른 서비스)
IMAGE_SERVICE=dall_e
OPENAI_API_KEY=xxxxxxxxxxxx

# 데이터베이스
DATABASE_URL=postgresql://user:password@localhost:5432/ai_company

# Flask/FastAPI
ENVIRONMENT=development
SECRET_KEY=your-secret-key

# WebSocket
WS_HOST=localhost
WS_PORT=8000
```

### 초기 데이터베이스 셋업

```bash
# 테이블 생성 및 초기 에이전트 등록
python backend/scripts/init_db.py

# 결과 확인
psql ai_company -c "SELECT * FROM agents;"
```

---

## 검증 계획

### Phase 1 검증
- [ ] 데이터베이스 연결 확인
- [ ] REST API 응답 확인 (Postman)
- [ ] 프론트엔드 로드 확인

### Phase 2 검증
```bash
# 테스트 시나리오
1. 사용자: "Hello"
2. 기대 결과: Manager Agent 응답
3. 메모리에 대화 저장되었는지 확인
```

### Phase 3 검증
```bash
# 토론 시나리오
1. 사용자: "새 기능 우선순위를 결정해주세요"
2. 기대:
   - Manager: 의견 제시
   - Developer: 의견 제시
   - Designer: 의견 제시
   - Researcher: 의견 제시
3. 투표 진행 및 결과 저장 확인
```

### Phase 4 검증
```bash
# 이미지 생성 시나리오
1. 사용자: "로고를 만들어줘"
2. Designer가 DALL-E 호출
3. 생성된 이미지가 채팅에 표시
4. 이미지 DB에 저장 확인
```

---

## 주요 기술 의존성

| 라이브러리 | 용도 | 버전 |
|-----------|------|------|
| FastAPI | 백엔드 프레임워크 | ^0.100 |
| SQLAlchemy | ORM | ^2.0 |
| psycopg2-binary | PostgreSQL 드라이버 | ^2.9 |
| python-socketio | WebSocket | ^5.9 |
| httpx | HTTP 클라이언트 | ^0.24 |
| pydantic | 데이터 검증 | ^2.0 |
| React | 프론트엔드 프레임워크 | ^18.0 |
| TypeScript | 타입 안정성 | ^5.0 |
| Zustand/Context | 상태 관리 | - |
| ws | WebSocket 클라이언트 | ^8.0 |
| axios | HTTP 클라이언트 | ^1.4 |

---

---

## 참조 아키텍처 분석: OpenClaw vs 우리 설계

### OpenClaw 아키텍처 개요

OpenClaw(WW-AI-Lab)는 멀티-에이전트 시스템의 실제 구현 사례입니다:

| 측면 | OpenClaw | 우리 설계 |
|------|----------|---------|
| **통신 패턴** | Gateway WS + RPC 도구 호출 | FastAPI WebSocket + 직접 프롬프트 교환 |
| **에이전트 협력** | `sessions_*` 도구로 크로스-세션 통신 | 동기적 직접 프롬프트 교환 (ConversationEngine) |
| **런타임** | Pi Agent Runtime (RPC 모드) | 직접 GLM API 호출 + BaseAgent 래퍼 |
| **상태 관리** | 세션별 독립적 토글 (thinking_level, verbose) | 공유 메모리 + 슬라이딩 윈도우 컨텍스트 |
| **도구 시스템** | 통합 도구 레지스트리 (browser, canvas, node) | 에이전트별 전문화된 기능 (ImageService, MemoryService) |
| **채널 지원** | 23+ 메시징 플랫폼 통합 | 웹 UI 단일 포커스 |
| **보안** | DM 페어링 + 알로우리스트 | X-API-Key 헤더 (Phase 2 TODO) |

### 배울 점: OpenClaw에서 검증된 패턴

**1. Gateway 패턴의 가치**
OpenClaw의 "중앙 제어 평면" 개념은 우리의 ConversationEngine과 유사합니다. 모든 에이전트 협력이 하나의 엔드포인트를 거치므로 로깅, 감시, 라우팅이 간단해집니다.
- 우리 설계: ConversationEngine이 이미 이 역할 수행 ✓

**2. 세션 격리와 크로스-세션 통신**
OpenClaw는 세션 간 메시지를 명시적으로 설계했습니다 (`sessions_send`, `sessions_history`). 우리는 단일 대화 세션으로 시작하지만, Phase 4-5에서 다중 병렬 토론(예: 2개의 독립적인 프로젝트 검토)을 지원해야 할 수 있습니다.
- **추천**: Phase 2에서 Conversation 모델에 `parent_conversation_id` 필드 추가 고려
- **이점**: 향후 마이크로-토론 기능이 필요할 때 준비 완료

**3. 에이전트 상태 추적의 세밀함**
OpenClaw의 에이전트 상태 머신(idle, working, speaking, tool-calling, error)은 우리의 "thinking" 상태보다 더 세분화되어 있습니다.
- **우리 설계**: 현재 ChatWindow에서 "에이전트 생각중" 표시만 함
- **개선안**: Phase 3에서 상태를 tool-calling, awaiting-consensus, error로 확장 고려

**4. 로컬 우선 아키텍처**
OpenClaw의 "최소 외부 의존성"은 좋은 원칙입니다. 우리도:
- PostgreSQL: 필수 (ORM으로 관리 용이)
- GLM API: 선택적 (다른 모델로 교체 가능)
- DALL-E: 선택적 (로컬 모델로 교체 가능)
- ✓ 이미 설계에 반영됨

### 우리 설계가 OpenClaw와 다른 이유

**1. 투표 기반 의견 수렴 (vs 도구 기반 협력)**
OpenClaw는 에이전트들이 도구를 호출하면서 협력합니다. 우리는 **투표로 의견을 수렴**합니다.
- 이것은 의도적 설계 결정입니다 (사용자 요청 기반)
- 장점: 모든 에이전트의 의견이 동등하게 평가됨
- 비용: 도구 기반 협력보다 덜 유연함

**2. 동기적 프롬프트 교환 (vs 비동기 도구 호출)**
우리의 "에이전트 A → 에이전트 B의 의견 요청 → 동기 응답"은 OpenClaw의 비동기 도구 호출보다 간단하지만, 확장성이 낮을 수 있습니다.
- **이점**: 구현이 간단, 토론의 흐름이 명확
- **비용**: 장시간 실행되는 도구(웹 탐색 등)는 지원 어려움
- **Phase 4+에서 검토**: 필요시 비동기 도구 호출로 확장

**3. 공유 메모리 vs 세션별 상태**
OpenClaw는 각 세션이 자신의 설정(thinking_level, verbose 등)을 가집니다.
우리는 모든 에이전트가 **동일한 공유 메모리**에 접근합니다.
- **이점**: 에이전트 간 일관된 컨텍스트, 회사 지식 축적
- **비용**: 메모리 쓰기 충돌 가능성 → Phase 3에서 optimistic locking 구현 (TODOS.md)

### 구현 영향도: 낮음

현재 우리 설계는 OpenClaw와 충분히 독립적입니다. OpenClaw의 패턴(Gateway, 상태 머신, 세션 격리)을 **선택적으로** 도입할 수 있지만, 급할 필요 없습니다.

**다음 프로젝트 주기에서 고려할 항목**:
1. Phase 5 완료 후, 다중 병렬 대화(마이크로-토론) 필요시 OpenClaw의 세션 격리 패턴 채택
2. Phase 4에서 에이전트가 도구(예: 웹 API 호출)가 필요하면, 비동기 도구 레지스트리 추가
3. 에이전트 상태 머신 확장 (현재 "thinking" → idle/thinking/tool-calling/voting)

---

## 다음 단계

1. **개발 환경 구축**: Docker 또는 venv로 로컬 환경 설정
2. **Phase 1 시작**: 백엔드 기본 구조 작성
3. **데이터베이스 초기화**: PostgreSQL 테이블 생성
4. **첫 에이전트 구현**: Manager Agent 완성
5. **프론트엔드 기본**: ChatWindow 및 WebSocket 연결

---

**예상 전체 개발 기간**: 5-6주 (Phase 1~5)

**성공 기준**:
- 4명의 에이전트가 동시에 정보를 처리하고 투표로 의견 수렴
- 모든 대화와 결정사항이 공유 메모리에 저장됨
- 웹 UI에서 전체 프로세스가 실시간으로 표시됨
- 새 에이전트 추가 시 기존 코드 수정 최소화

---

## 설계 결정사항 (design review)

### MainDashboard 정보 계층 구조
```
PRIMARY (최우선): ChatWindow (메시지 목록, 입력필드)
SECONDARY: AgentPanel (좌측) + VotingInterface (상단)
TERTIARY: MemoryPanel (우측, 필요시 접근)
```

### 디자인 시스템 (기본)
- **색상**: Manager(#0066CC), Developer(#00AA44), Designer(#9900FF), Researcher(#FF9900)
- **타이포그래피**: Pretendard (한글), 헤더 20px Bold, 본문 16px, UI 14px
- **간격**: 8px 그리드, 컴포넌트 패딩 12px, 섹션 마진 24px

### 상호작용 상태
- **ChatWindow**: 로딩중, 에이전트 생각중(타이핑), 네트워크 오류, 빈 대화
- **VotingInterface**: 투표중, 동점(매니저 결정), 완료
- **MemoryPanel**: 검색결과없음, 로딩, 비어있음
- **ImageInput**: 업로드중, 실패, 생성중

### 반응형 사양
- **데스크톱**: 3열 레이아웃 (에이전트 240px + 채팅 + 메모리 250px)
- **태블릿**: 2열 또는 탭 (에이전트 상단, 채팅 메인, 메모리 모달)
- **모바일**: 1열 전체폭 (탭으로 전환)

### 접근성
- 키보드 네비게이션 (Tab, Arrow, Enter)
- 색상 + 아이콘으로 구분
- 터치 타겟 최소 44px
- 모든 기능에 aria-label

### 미해결 설계 결정 (8개)
- 에이전트 아바타 표현 방식
- 투표 UI 정확한 배치
- 에이전트 응답 애니메이션
- 메모리 검색 UI 패턴
- 네트워크 오류 재시도 버튼 위치
- 모바일 3-패널 폴드 전략
- 빈 대화 시작 프롬프트
- 이미지 생성 진행 상황 표시

## 계획 수정사항 (eng review 결과)

| # | 결정 | 내용 |
|---|------|------|
| 1 | 엔진 통합 | conversation/voting/discussion → 하나의 ConversationEngine |
| 2 | WebSocket | python-socketio 제거 → FastAPI 네이티브 WebSocket |
| 3 | 메시지 스키마 | sender_type 컬럼 추가, agent_id nullable |
| 4 | DB 스키마 | decisions.voting_result JSONB 제거 (votes 테이블이 단일 소스) |
| 5 | 동시성 | asyncio.gather() + asyncio.Semaphore(2) |
| 6 | 에이전트 팩토리 | if/elif → registry dict 패턴 |
| 7 | 테스트 | pytest + Playwright, 각 Phase마다 통합 |
| 8 | 컨텍스트 창 | Phase 2에 슬라이딩 윈도우 (최근 20개) 추가 |
| 9 | 투표 설계 | 동등 투표 유지 (에이전트 추론이 핵심 가치) |
| 10 | Phase 1 추가 | GLM 멀티에이전트 CLI 스파이크 |

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 1 | issues_found (PLAN) | 11 findings, 5 cross-model tensions resolved |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | issues_open (PLAN) | 9 issues, 3 critical gaps (GLM timeout/ratelimit/agent failure) |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |

**UNRESOLVED:** 3 critical gaps (GLM error handling not yet designed — add to Phase 2 implementation)

**VERDICT:** ENG REVIEW RAN — issues_open (3 critical gaps need error handling in implementation). Run `/plan-design-review` when UI components are designed.
