# 실시간 체인형 토론 + 대화 아카이브 설계

**날짜**: 2026-04-10
**상태**: 승인됨
**작성자**: Sisyphus

---

## 1. 배경

### 현재 시스템의 문제

1. **토론이 병렬 실행됨**: `DebateEngine`이 `asyncio.gather()`로 모든 에이전트를 동시에 실행 → 서로의 의견을 보지 못하고 각자 독립적으로 발언
2. **동기 REST API**: 토론 전체가 끝나야 결과가 한번에 반환됨 → 실시간감 없음
3. **오른쪽 패널 고립**: 토론이 채팅창이 아닌 VotingPanel에서 진행됨 → UX 단절
4. **아카이빙 부재**: 과거 대화를 주제별로 탐색할 방법이 없음

### 목표

- 에이전트들이 **순차적으로** 발언하며, 이전 발언을 참고하는 **실시간 체인형 토론**
- 토론이 **채팅창에 실시간**으로 표시
- 오른쪽 패널을 **대화 아카이브**로 전환
- 대화 종료 시 **Manager가 자동으로 주제 분류**

---

## 2. 토론 UX 흐름

### 2.1 토론 시작

두 가지 트리거:

**A. 자동 감지**: 사용자 메시지에서 토론 키워드 감지
- 한국어: `토론, 토의, 논의, 의견 나누, 토론해, 의견을 들어, 얘기해보자, 어떻게 생각해, 찬반`
- 영어: `discuss, debate, opinion, what do you think`
- 감지 시 자동으로 토론 모드 진입

**B. 버튼**: 채팅 입력란 옆 "토론시작" 버튼 클릭
- 버튼 클릭 시 입력된 메시지(또는 빈 메시지)를 주제로 토론 시작
- 주제가 비어있으면 Manager가 대화 맥락에서 주제를 추출

### 2.2 토론 진행 (체인형 2라운드)

```
[사용자 메시지: "새 기능의 기술 스택을 React vs Vue로 토론해줘"]

→ WebSocket: { type: "discussion_start", topic: "..." }

── 📢 1라운드 ──

🤖 비서실장: "전략적 관점에서 React를 추천합니다..."
                                    ← WebSocket 즉시 전송, 채팅창에 표시

💻 개발부장: "매니저님 의견에 부분 동의합니다만, Vue의 장점도..."
                                    ← Manager 발언을 컨텍스트로 받음

🎨 디자인팀장: "디자인 시스템 관점에서 보면..."
                                    ← Manager + Developer 발언을 컨텍스트로 받음

📊 전략분석관: "시장 데이터를 보면 React가 72% 점유율..."
                                    ← 전원 발언을 컨텍스트로 받음

── 📢 2라운드 ──

🤖 비서실장: "1라운드 의견을 종합하면..."
                                    ← 1라운드 전체 + 2라운드 이전 발언 참고

💻 개발부장: "최종적으로 React에 동의합니다..."

🎨 디자인팀장: "합의된 방향에 동의합니다..."

📊 전략분석관: "데이터 기반으로 React를 권장합니다..."

── 토론 종료 ──

📋 최종 요약: "4명 중 3명이 React를 지지했습니다..."
```

### 2.3 에이전트 순서

고정 순서: Manager → Developer → Designer → Researcher

Manager는 항상 첫 번째(전략적 관점 제시)이자 마지막(종합 정리 가능성).

### 2.4 토론 중 툴 사용

에이전트는 토론 중에도 `web_search`, `execute_python`, `youtube_transcript` 툴을 사용할 수 있음.
예: Researcher가 "시장 데이터를 확인해보겠습니다" → web_search 호출 → 결과를 반영하여 발언.

툴 사용 과정도 WebSocket으로 실시간 전송 (기존 `agent_step` 메시지 활용).

---

## 3. 대화 아카이브 (오른쪽 패널)

### 3.1 ConversationArchive 컴포넌트

기존 VotingPanel을 교체. 항상 표시되는 오른쪽 사이드바.

```
┌─ 대화 아카이브 ─────────────────┐
│ 🔍 검색...                       │
│                                   │
│ 📂 기술 스택 선정                 │
│    비서실장·개발부장·디자인팀장    │
│    2시간 전 · 12개 메시지          │
│    #기술 #React                   │
│                                   │
│ 📂 마케팅 전략 회의               │
│    비서실장·전략분석관             │
│    어제 · 8개 메시지               │
│    #마케팅 #전략                   │
│                                   │
│ 📂 UI 개선 토론                   │
│    디자인팀장·개발부장             │
│    3일 전 · 15개 메시지            │
│    #UI #디자인                     │
└──────────────────────────────────┘
```

### 3.2 아카이브 데이터 구조

```typescript
interface ConversationArchive {
  id: string;
  title: string;               // Manager가 자동 분류
  tags: string[];               // Manager가 자동 태깅
  summary: string;              // 대화 요약
  participant_agents: string[]; // 참여한 에이전트 이름 목록
  message_count: number;
  created_at: string;           // 대화 시작 시간
  archived_at: string;          // 아카이빙 시간
  has_debate: boolean;          // 토론이 포함된 대화인지
}
```

### 3.3 자동 분류 흐름

```
대화 종료 감지
    │
    ├── 트리거:
    │   1. 사용자가 완전히 새로운 주제로 전환 (키워드 기반 감지)
    │   2. 사용자가 명시적 종료 ("고마워", "끝", "그만", "done" 등)
    │   3. 새 대화가 시작되면서 이전 대화가 자동 아카이빙
    │
    └── Manager 에이전트 분류 요청
        │
        ├── 입력: 대화의 모든 메시지 (최대 최근 20개)
        │
        └── 출력: {
        │     title: "기술 스택 선정",
        │     tags: ["#기술", "#React"],
        │     summary: "React vs Vue 기술 스택 선정에 대한 토론..."
        │   }
        │
        └── 백엔드에 저장 → 프론트엔드 아카이브 리스트 갱신
```

### 3.4 아카이브 클릭 동작

아카이브 항목을 클릭하면:
- 해당 대화의 메시지를 채팅창에 로드 (읽기 전용 표시)
- 채팅창 상단에 "과거 대화 보기 중" 배너 표시
- 뒤로가기 버튼으로 현재 대화로 복귀

---

## 4. 백엔드 아키텍처

### 4.1 신규: LiveDiscussionEngine

파일: `backend/engines/live_discussion_engine.py`

```python
class LiveDiscussionEngine:
    """체인형 실시간 토론 엔진.
    
    에이전트가 한 명씩 순차적으로 발언하며,
    각 발언이 WebSocket으로 즉시 전송됨.
    """

    async def start_discussion(
        self,
        topic: str,
        agents: list,           # 참여 에이전트 객체 리스트
        ws_callback: callable,  # WebSocket 전송 콜백
        conversation_id: str,
        num_rounds: int = 2,
    ) -> dict:
        """전체 토론을 실행하고 결과 반환."""
        
    async def _run_chain_round(
        self,
        topic: str,
        agents: list,
        round_num: int,
        previous_messages: list,  # 이전 라운드 메시지 누적
        ws_callback: callable,
    ) -> list:
        """단일 라운드: 에이전트를 순차적으로 호출."""
        # for agent in agents:
        #     1. 이전 발언 컨텍스트 구성
        #     2. AgentTaskExecutor로 에이전트 호출 (툴 사용 지원)
        #     3. WebSocket으로 즉시 전송
        #     4. 발언을 previous_messages에 추가
        
    async def _generate_summary(
        self,
        topic: str,
        all_messages: list,
    ) -> str:
        """Manager 에이전트가 최종 요약 생성."""
```

### 4.2 수정: ConversationEngine

파일: `backend/engines/conversation_engine.py`

변경점:
- `_detect_discussion_intent(message)` 메서드 추가 — 토론 키워드 감지
- `process_message()`에서 토론 감지 시 `LiveDiscussionEngine`으로 라우팅
- 기존 일반 응답 로직은 그대로 유지
- `_detect_conversation_end(message)` 메서드 추가 — 대화 종료 감지

### 4.3 수정: ManagerAgent

파일: `backend/agents/manager_agent.py`

변경점:
- `classify_conversation(messages)` 메서드 추가 — 대화 주제 자동 분류
- LLM에 메시지 목록을 전달하여 title, tags, summary 생성

### 4.4 신규: ArchiveService

파일: `backend/services/archive_service.py`

```python
class ArchiveService:
    """대화 아카이빙 서비스."""
    
    async def archive_conversation(
        self, 
        conversation_id: str,
        messages: list,
    ) -> ConversationArchive:
        """대화를 아카이빙. Manager가 자동 분류."""
        
    async def search_archives(
        self, 
        query: str, 
        limit: int = 20,
    ) -> list[ConversationArchive]:
        """아카이브 검색."""
        
    async def get_recent_archives(
        self, 
        limit: int = 20,
    ) -> list[ConversationArchive]:
        """최근 아카이브 목록."""
        
    async def get_archive_messages(
        self, 
        archive_id: str,
    ) -> list[dict]:
        """아카이브의 메시지 조회."""
```

### 4.5 수정: main.py

신규 WebSocket 이벤트:
- `discussion_start` — 토론 시작 알림
- `discussion_message` — 에이전트 발언 (실시간)
- `discussion_round_change` — 라운드 전환
- `discussion_summary` — 최종 요약
- `discussion_end` — 토론 종료
- `conversation_archived` — 대화 아카이빙 완료

신규 REST API:
- `GET /api/archives` — 아카이브 목록
- `GET /api/archives/{id}` — 아카이브 상세 + 메시지
- `GET /api/archives/search?q=...` — 아카이브 검색

신규 WebSocket action:
- `{ "action": "start_debate", "topic": "..." }` — 채팅에서 토론 시작

---

## 5. 프론트엔드 아키텍처

### 5.1 신규: ConversationArchive

파일: `frontend/src/components/ConversationArchive.tsx`

오른쪽 패널 교체. VotingPanel 대신 App.tsx에 마운트.

기능:
- 아카이브 리스트 표시 (최근 순)
- 검색 입력 (디바운스 300ms)
- 아카이브 클릭 → 채팅창에 과거 대화 로드
- `conversation_archived` WebSocket 이벤트 수신 시 리스트 갱신

### 5.2 수정: ChatWindow

파일: `frontend/src/components/ChatWindow.tsx`

변경점:
- 채팅 입력란 옆 "토론시작" 버튼 추가
- `discussion_start`, `discussion_message`, `discussion_round_change`, `discussion_summary`, `discussion_end` 이벤트 처리
- 라운드 구분선 UI (── 1라운드 ──)
- 최종 요약은 강조 스타일 (배경색 + 아이콘)

### 5.3 수정: MessageBubble

파일: `frontend/src/components/MessageBubble.tsx`

변경점:
- `isDebate` prop 추가 — 토론 메시지 시각적 구분
- 라운드 구분선 컴포넌트
- 요약 메시지 특별 스타일

### 5.4 수정: Zustand Store

파일: `frontend/src/store.ts`

신규 상태:
```typescript
// 아카이브
archives: ConversationArchive[];
isLoadingArchives: boolean;

// 활성 토론
isDebating: boolean;
currentDiscussionId: string | null;
discussionRound: number;
```

신규 액션:
```typescript
addArchive(archive: ConversationArchive): void;
setArchives(archives: ConversationArchive[]): void;
setDebating(isDebating: boolean): void;
```

### 5.5 제거: VotingPanel

파일: `frontend/src/components/VotingPanel.tsx`

App.tsx에서 import 및 렌더링을 제거. 파일 자체는 보존 (향후 투표 기능 복원 시 참고).

---

## 6. 데이터베이스

기존 SQLite에 신규 테이블 추가:

```sql
CREATE TABLE conversation_archives (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    title TEXT NOT NULL,
    tags TEXT,                           -- JSON array string
    summary TEXT,
    participant_agents TEXT,             -- JSON array string
    message_count INTEGER DEFAULT 0,
    has_debate BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_archives_conversation ON conversation_archives(conversation_id);
CREATE INDEX idx_archives_created ON conversation_archives(created_at DESC);
```

아카이브 메시지는 기존 `messages` 테이블에서 `conversation_id`로 조회.

---

## 7. 에이전트 토론 프롬프트

각 에이전트의 `respond_to_debate()` 메서드에 전달되는 프롬프트 형식:

```
[주제]: {topic}

[이전 발언]:
- 비서실장 (1라운드): "전략적 관점에서..."
- 개발부장 (1라운드): "매니저님 의견에 동의하지만..."
- ...

당신은 {agent_role}입니다. 위 주제에 대해 이전 발언을 참고하여:
1. 동의하는 점과 반론할 점을 명확히 구분하여 의견을 제시하세요
2. 본인의 전문 분야 관점에서 보완하세요
3. 가능하면 구체적인 근거를 제시하세요

{mode_instruction}
```

2라운드 모드 명령:
```
"1라운드에서 나온 의견들을 종합하여, 최종 입장을 정리하세요. 
필요하면 타협안을 제시하거나 추가 근거를 보완하세요."
```

---

## 8. 파일 변경 요약

### 신규 파일
| 파일 | 설명 |
|------|------|
| `backend/engines/live_discussion_engine.py` | 체인형 실시간 토론 엔진 |
| `backend/services/archive_service.py` | 대화 아카이빙 서비스 |
| `frontend/src/components/ConversationArchive.tsx` | 오른쪽 패널 아카이브 UI |

### 수정 파일
| 파일 | 변경 내용 |
|------|-----------|
| `backend/engines/conversation_engine.py` | 토론 감지 로직, LiveDiscussionEngine 라우팅 |
| `backend/agents/manager_agent.py` | `classify_conversation()` 메서드 추가 |
| `backend/main.py` | discussion WebSocket 이벤트, 아카이브 REST API |
| `frontend/src/components/ChatWindow.tsx` | 토론 메시지 표시, 토론 버튼 |
| `frontend/src/components/MessageBubble.tsx` | 토론 구분선, 요약 스타일 |
| `frontend/src/store.ts` | 아카이브 상태, 토론 상태 |
| `frontend/src/App.tsx` | VotingPanel → ConversationArchive 교체 |

### 제거 (렌더링만)
| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/components/VotingPanel.tsx` | App.tsx에서 import 제거 (파일 보존) |

---

## 9. 제약사항 및 주의점

1. **API 호출량**: 토론 2라운드 × 4에이전트 = 최소 8회 LLM 호출. Manager 분류 요청까지 포함하면 9회. 툴 사용 시 더 늘어날 수 있음.
2. **순차 실행 지연**: 병렬이 아닌 순차이므로 총 소요시간은 길어짐. 단, 사용자는 실시간으로 하나씩 보기 때문에 체감 대기시간은 짧음.
3. **기존 DebateEngine/VotingEngine**: 삭제하지 않음. REST API는 그대로 유지. 향후 필요시 복원 가능.
4. **아카이빙 타이밍**: 대화 종료 정확한 감지가 어려울 수 있음. 새 대화 시작 시 이전 대화를 자동 아카이빙하는 방식이 가장 안전.
