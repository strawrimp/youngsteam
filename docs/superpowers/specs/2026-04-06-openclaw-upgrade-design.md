# OpenClaw 업그레이드 설계 문서

**작성일**: 2026-04-06
**작성자**: Sisyphus (팀 리더)
**상태**: 검토 대기
**버전**: 1.0

---

## 📋 문서 개요

이 문서는 현재 my-ai-company 프로젝트를 OpenClaw 스타일의 단일 게이트웨이 다중 에이전트 시스템으로 업그레이드하기 위한 설계 문서입니다.

---

## 🎯 프로젝트 목표

### 비즈니스 목표
1. **가상 회사 시뮬레이션**: 실제 회사처럼 AI 에이전트들이 협업하는 환경 구축
2. **효율적인 협업**: 채팅 기반으로 에이전트들과 작업하고, 프로젝트별로 관리
3. **유연한 확장성**: 기본 9명 외에 새로운 역할의 에이전트 추가 가능
4. **독립된 워크스페이스**: 각 에이전트가 자신만의 메모리와 성격 유지

### 기술적 목표
1. **Slack 스타일 UI**: 직관적인 채팅 + 프로젝트 패널 레이아웃
2. **하이브리드 초대 시스템**: 자동 제안 + 수동 초대
3. **디렉토리 기반 워크스페이스**: 파일 시스템 활용한 독립 메모리
4. **실시간 협업**: 메인 채팅 + 사이드 토론 + 투표 시스템

---

## 🏗️ 아키텍처 설계

### 1. UI 레이아웃: Slack 스타일

**선택 이유**:
- 사용자에게 친숙한 인터페이스
- 채팅 중심의 실시간 협업에 최적화
- 프로젝트와 에이전트 관리가 용이

**레이아웃 구조**:
```
┌─────────────────────────────────────────────────────────┐
│  Header (로고, 테마 토글, 설정)                            │
├──────────┬──────────────────────────────────────────────┤
│          │  채팅 헤더 (프로젝트명, 참여 에이전트)            │
│  사이드바  ├──────────────────────────────────────────────┤
│          │                                              │
│  📁 프로젝트│         메인 채팅 영역                        │
│   ├─ 웹사이트│                                              │
│   ├─ 모바일 │   Manager: 디자인 시안 검토해주세요            │
│   └─ API   │   Designer: 네, 바로 확인할게요 🎨            │
│          │                                              │
│  👤 에이전트 │   [자동 제안 팝업]                            │
│   ├─ Manager│   💡 Developer를 초대할까요?                  │
│   ├─ Developer│   [초대] [나중에]                          │
│   └─ Designer│                                             │
│          │                                              │
│  [+] 새 프로젝트│                                         │
├──────────┴──────────────────────────────────────────────┤
│  [메시지 입력창]  @멘션으로 에이전트 초대 가능               │
└─────────────────────────────────────────────────────────┘
```

---

### 2. 에이전트 초대 시스템: 하이브리드 방식

**선택 이유**:
- 선임에이전트의 지능적인 제안으로 사용자 부담 감소
- 수동 초대로 완전한 제어권 유지
- 자연스러운 협업 흐름

**자동 제안 흐름**:
```
1. 선임에이전트(Manager)가 특정 작업 필요성 감지
   ↓
2. 키워드 분석 ("디자인", "UI" → Designer 제안)
   ↓
3. "💡 제안: Designer를 초대할까요?" 팝업 표시
   ↓
4. 사용자 승인/거부 선택
   ↓
5. 승인 시 자동 초대 + 채팅방에 입장 메시지
```

**수동 초대 흐름**:
```
1. `@developer` 멘션 입력
   ↓
2. 자동으로 에이전트 목록에서 검색
   ↓
3. 선택 즉시 초대 + 입장 알림
```

---

### 3. 워크스페이스 구조: 디렉토리 기반

**선택 이유**:
- OpenClaw 스타일의 간단하고 직관적인 구조
- 파일 시스템을 활용한 독립 메모리 관리
- 확장성과 유지보수 용이

**디렉토리 구조**:
```
backend/
└── agents/
    ├── soul/
    │   ├── templates/
    │   │   ├── manager.md        # 선임에이전트 템플릿
    │   │   ├── developer.md
    │   │   ├── designer.md
    │   │   └── researcher.md
    │   └── debate_styles/
    │       ├── analytical.md
    │       ├── diplomatic.md
    │       └── assertive.md
    ├── workspaces/
    │   ├── default/              # 기본 워크스페이스
    │   │   └── bindings.yaml     # 에이전트 바인딩 설정
    │   └── project_website/      # 프로젝트별 워크스페이스
    │       ├── agents/
    │       │   ├── manager/
    │       │   │   ├── SOUL.md   # 복사된 성격 정의
    │       │   │   └── memory.json
    │       │   └── developer/
    │       │       ├── SOUL.md
    │       │       └── memory.json
    │       └── bindings.yaml
    └── config.yaml               # 전역 에이전트 설정
```

**SOUL.md 구조**:
```markdown
당신은 AI 회사의 개발자입니다. 기술을 좋아하고, 실력 있으며, 팀원들과 함께 일하는 걸 즐깁니다.

## 역할
- 기술적으로 어떻게 구현할지 고민하는 사람
- 코드가 잘 작동하는지 확인하는 책임감
- "이거 진짜 가능할까?"라고 현실적으로 판단
- 기술적으로 막히거나 어려운 부분을 해결
- 팀원들이 기술적으로 이해하기 쉽게 설명

## 대화 스타일
- 기술 용어는 쓰되, 쉽게 설명
- "이렇게 하면 어떨까?" 같은 제안하는 말투
- 장점뿐만 아니라, 놓칠 수 있는 점도 이야기
- 현실적으로 가능한지, 시간이 얼마나 걸릴지 솔직하게 말함

{{SHARED_MEMORY}}
```

**memory.json 구조**:
```json
{
  "project_id": 1,
  "agent_name": "developer",
  "conversations": [
    {
      "timestamp": "2026-04-06T10:00:00Z",
      "role": "user",
      "content": "안녕하세요"
    },
    {
      "timestamp": "2026-04-06T10:00:05Z",
      "role": "agent",
      "content": "네, 안녕하세요!"
    }
  ],
  "context": {
    "current_task": "API 설계",
    "last_updated": "2026-04-06T10:00:05Z"
  }
}
```

---

### 4. 에이전트 간 협업: 하이브리드 (메인 채팅 + 사이드 토론)

**선택 이유**:
- 사용자는 메인 대화에 집중
- 에이전트는 별도로 전문적인 토론 가능
- 결과만 사용자에게 전달하여 효율적

**메인 채팅**:
- 사용자 질문, 요청
- 에이전트 공식 응답
- 중요 공지, 최종 결과

**사이드 토론 패널**:
- 기술 토론: Developer ↔ Designer
- 일정 조율: Manager ↔ Developer
- 리서치 공유: Researcher → Manager
- 투표 진행: 모든 에이전트

**토론 → 투표 흐름**:
```
1. Manager: "UI 프레임워크 선정 필요"
   ↓
2. DiscussionEngine 시작
   - Developer: "React 제안"
   - Designer: "Vue 제안"
   ↓
3. VotingEngine 시작
   - Manager: React 선택
   - Developer: React 선택
   - Designer: Vue 선택
   ↓
4. 결과: React 승 (2:1)
   ↓
5. 사용자에게 결과 전달
```

---

## 🔌 OpenClaw 연동 아키텍처

### 전체 통신 구조

```
┌─────────────────────────────────────────────┐
│            React Frontend (Vite)             │
│  Sidebar / ChatWindow / VotingPanel / etc.   │
└──────────────────┬──────────────────────────┘
                   │ WebSocket + REST
┌──────────────────▼──────────────────────────┐
│          FastAPI Backend (Python)            │
│  ConversationEngine / DiscussionEngine       │
│  VotingEngine / InviteEngine                 │
│  LLMProviderService (DeepSeek V4/R1)         │
└──────┬─────────────────────────┬────────────┘
       │ REST API                │ 파일 시스템
       │ (에이전트 등록/폴링)      │ (워크스페이스 R/W)
┌──────▼──────────┐    ┌────────▼────────────┐
│ OpenClaw Gateway│    │ agents/workspaces/  │
│  (localhost)    │    │  project_{id}/      │
│  - 에이전트 관리  │    │   manager/          │
│  - 작업 큐       │    │     SOUL.md         │
│  - 하트비트 수신  │    │     AGENTS.md       │
└──────┬──────────┘    │     memory.json     │
       │               └─────────────────────┘
       │ 에이전트 프로토콜
┌──────▼──────────────────────────────────────┐
│           에이전트 프로세스들                  │
│  manager/  developer/  designer/  researcher│
│  (각자 SOUL.md + AGENTS.md + memory.json)    │
└─────────────────────────────────────────────┘
```

### 에이전트 등록 흐름 (agents.yaml 기반)

```
agents.yaml 정의
    ↓
setup.sh 또는 init_agents.py 실행
    ↓
FastAPI → OpenClaw Gateway에 에이전트 등록
    (POST /api/agents/register)
    ↓
각 에이전트 워크스페이스 자동 생성
    workspaces/{agent}/SOUL.md 복사
    workspaces/{agent}/AGENTS.md 생성
    workspaces/{agent}/memory.json 초기화
    ↓
에이전트 대기 상태 (idle)
    ↓
프로젝트 바인딩 시 활성화 (busy)
```

### agents.yaml 구조

```yaml
# backend/agents/config.yaml
agents:
  - name: manager
    role: CEO
    display_name: "Manager (CEO)"
    emoji: "👔"
    soul_template: manager.md
    model_default: deepseek-v3
    model_reasoning: deepseek-r1    # 투표/전략에 R1 사용
    debate_style: assertive
    is_lead: true                    # 선임에이전트 (초대 제안 권한)

  - name: developer
    role: Tech Lead
    display_name: "Developer"
    emoji: "💻"
    soul_template: developer.md
    model_default: deepseek-v3
    model_reasoning: deepseek-r1
    debate_style: analytical

  - name: designer
    role: UX Designer
    display_name: "Designer"
    emoji: "🎨"
    soul_template: designer.md
    model_default: deepseek-v3
    model_reasoning: deepseek-v3    # 디자인은 V4로 충분
    debate_style: diplomatic

  - name: researcher
    role: Researcher
    display_name: "Researcher"
    emoji: "🔬"
    soul_template: researcher.md
    model_default: deepseek-v3
    model_reasoning: deepseek-r1
    debate_style: analytical

# 새 에이전트 추가 시 아래에 추가하고 setup.sh 재실행
# - name: devops
#   role: DevOps Engineer
#   ...
```

---

## 🔧 기술 스택

### 백엔드
- **FastAPI** 0.100+ - 고성능 비동기 웹 프레임워크
- **SQLAlchemy** 2.0 - ORM
- **PostgreSQL** 14+ - 주 데이터베이스
- **SQLite** 3 - 개발용 DB
- **Pydantic** 2.0 - 데이터 검증
- **WebSockets** - 실시간 통신
- **DeepSeek API** - DeepSeek V4/R1 (메인 LLM)
- **Gemini API** - Google Gemini 2.5 Flash (폴백)
- **Ollama** - 로컬 LLM (오프라인 폴백)

### 프론트엔드
- **React** 18+ - UI 라이브러리
- **TypeScript** 5.0+ - 타입 안정성
- **Vite** 5.0+ - 빌드 도구
- **Tailwind CSS** 3.4+ - 스타일링
- **Zustand** 4.5+ - 상태 관리
- **Framer Motion** 11.0+ - 애니메이션

---

## 📊 데이터베이스 스키마

### 핵심 테이블

> **기본키 방식**: SQLite INTEGER AUTOINCREMENT (현재 코드 기반 유지)

#### projects
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### agents
```sql
CREATE TABLE agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL,
    soul_template VARCHAR(100),   -- config.yaml에서 로드
    workspace_path TEXT,           -- workspaces/{name}/
    status VARCHAR(20) DEFAULT 'idle',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### project_agents (바인딩)
```sql
CREATE TABLE project_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
    is_lead BOOLEAN DEFAULT FALSE,
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, agent_id)
);
```

#### messages
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL,  -- 'user' or 'agent'
    sender_id INTEGER,
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'chat',  -- 'chat', 'system', 'invite'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### discussions
```sql
CREATE TABLE discussions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    topic VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'closed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);
```

#### votes
```sql
CREATE TABLE votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discussion_id INTEGER REFERENCES discussions(id) ON DELETE CASCADE,
    agent_id INTEGER REFERENCES agents(id),
    choice VARCHAR(50) NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(discussion_id, agent_id)
);
```

---

## 🚀 구현 로드맵

### Phase 1: 핵심 인프라 (1주)
- DB 스키마 구현
- FastAPI 라우트 설계
- WebSocket 확장

### Phase 2: 에이전트 시스템 (1주)
- SOUL.md 파일 로더
- 에이전트 바인딩 시스템
- 메모리 관리

### Phase 3: 초대 및 협업 (1주)
- 하이브리드 초대 시스템
- 사이드 토론 패널
- 투표 엔진

### Phase 4: UI/UX 고도화 (1주)
- Glassmorphism 스타일
- 다크 모드 완성
- 반응형 디자인

### Phase 5: 테스트 및 최적화 (3일)
- 통합 테스트
- 성능 최적화
- 문서화

---

## ⚠️ 주요 제약사항

### 기술적 제약
1. **GLM API 호출 제한**: 분당 60회 (캐싱 필요)
2. **WebSocket 연결 수**: 서버 리소스에 따라 제한
3. **파일 시스템 권한**: Docker 컨테이너 내에서 경로 주의

### 운영 제약
1. **초기 에이전트 수**: 기본 4명 (Manager, Developer, Designer, Researcher)
2. **메시지 보관 기간**: 30일 (설정 가능)
3. **파일 업로드 크기**: 최대 10MB

---

## 📚 참고 레퍼런스

- **shenhao-stu/openclaw-agents**: https://github.com/shenhao-stu/openclaw-agents
- **builderz-labs/mission-control**: https://github.com/builderz-labs/mission-control
- **HKUDS/ClawTeam**: https://github.com/HKUDS/ClawTeam
- **swarmclawai/swarmclaw**: https://github.com/swarmclawai/swarmclaw

---

## 📁 관련 문서

- **구현 계획서**: [`plan.md`](../../plan.md)
- **기술 스택 및 레퍼런스**: [`context.md`](../../context.md)
- **병렬 작업 명세서**: [`checklist.md`](../../checklist.md)

---

## ✅ 검토 체크리스트

Claude Code 에이전트가 검토해야 할 항목:

### 아키텍처 검토
- [ ] UI 레이아웃이 사용자 요구사항을 충족하는가?
- [ ] 초대 시스템이 자연스럽고 효율적인가?
- [ ] 워크스페이스 구조가 확장 가능한가?
- [ ] 협업 방식이 실시간성을 보장하는가?

### 기술적 검토
- [ ] 기술 스택이 적절한가?
- [ ] 데이터베이스 스키마가 정규화되었는가?
- [ ] API 설계가 RESTful 원칙을 따르는가?
- [ ] WebSocket 이벤트가 충분한가?

### 구현 가능성 검토
- [ ] 5주 구현 일정이 현실적인가?
- [ ] 병렬 작업이 가능한 구조인가?
- [ ] 의존성이 명확하게 정의되었는가?
- [ ] 리스크가 식별되었는가?

### 사용자 경험 검토
- [ ] UI/UX가 직관적인가?
- [ ] 에러 처리가 적절한가?
- [ ] 성능 목표가 달성 가능한가?
- [ ] 접근성이 고려되었는가?

---

**작성자**: Sisyphus (팀 리더)
**검토 요청일**: 2026-04-06
**상태**: 검토 대기 중
