# 클로드코드 보완 사항 구현 계획서

**작성일**: 2026-04-06
**작성자**: Sisyphus (팀 리더)
**상태**: 구현 대기
**버전**: 1.0

---

## 📋 개요

이 문서는 클로드코드가 보완한 4가지 수정 사항을 체계적으로 구현하기 위한 작업 계획서입니다.

---

## 🎯 수정 사항 요약

### 1. ✅ context.md — LLM 스택 DeepSeek 기준으로 교체
**상태**: 완료 ✅
**담당자**: Sisyphus

#### 수정 내용
- DeepSeek-V3(V4): 범용 응답 메인
- DeepSeek-R1: 투표·전략·추론 자동 선택
- Gemini 2.5 Flash: Fallback #1
- Gemini 3 Flash Preview: Fallback #2
- GLM: 레거시(비활성) 명시
- 모델 자동 선택 로직 설명 추가

#### 관련 파일
- ✅ `context.md` (수정 완료)
- ✅ `docs/superpowers/specs/2026-04-06-llm-failover-design.md` (신규 생성)

---

### 2. ⏳ plan.md + design.md — DB 스키마 INTEGER 방식으로 통일
**상태**: 진행 중 🔄
**담당자**: Oracle (코드 아키텍트)

#### 수정 내용
- `plan.md` + `design.md` 두 파일 모두 INTEGER PRIMARY KEY AUTOINCREMENT로 일치
- ON DELETE CASCADE 외래키 추가
- UNIQUE(discussion_id, agent_id) 중복 방지 추가

#### 작업 항목
- [ ] `plan.md` DB 스키마 수정
  - projects 테이블
  - agents 테이블
  - project_agents 테이블
  - messages 테이블
  - discussions 테이블
  - votes 테이블

- [ ] `design.md` DB 스키마 수정
  - 위와 동일한 수정 사항 적용

#### 관련 파일
- ⏳ `plan.md` (수정 필요)
- ⏳ `docs/superpowers/specs/2026-04-06-openclaw-upgrade-design.md` (수정 필요)

---

### 3. ⏳ design.md — OpenClaw 연동 아키텍처 다이어그램 추가
**상태**: 진행 중 🔄
**담당자**: Oracle (코드 아키텍트)

#### 수정 내용
- React ↔ FastAPI ↔ OpenClaw Gateway ↔ 에이전트 통신 구조
- 에이전트 등록 흐름 (agents.yaml → setup.sh → 워크스페이스 자동 생성)
- agents.yaml 전체 구조 예시

#### 작업 항목
- [ ] 아키텍처 다이어그램 작성
  ```mermaid
  graph TB
      User[사용자] --> Frontend[React Frontend]
      Frontend -->|WebSocket/REST| Backend[FastAPI Backend]
      Backend -->|YAML 로드| AgentRegistry[에이전트 레지스트리]
      AgentRegistry -->|DB 등록| Database[(PostgreSQL/SQLite)]
      Backend -->|LLM 호출| LLMProvider[DeepSeek/Gemini]
      Backend -->|파일 생성| Workspace[워크스페이스]
      Workspace -->|SOUL.md 로드| Agent[에이전트 인스턴스]
      Agent -->|메모리 관리| Memory[memory.json]
  ```

- [ ] agents.yaml 구조 예시 추가
  ```yaml
  agents:
    - name: manager
      role: lead
      display_name: "매니저"
      emoji: "👔"
      soul_template: "manager.md"
      model_default: "deepseek-v4"
      model_reasoning: "deepseek-r1"
      debate_style: "diplomatic"
      is_lead: true
      
    - name: developer
      role: technical
      display_name: "개발자"
      emoji: "💻"
      soul_template: "developer.md"
      model_default: "deepseek-v4"
      model_reasoning: "deepseek-r1"
      debate_style: "analytical"
      is_lead: false
  ```

#### 관련 파일
- ⏳ `docs/superpowers/specs/2026-04-06-openclaw-upgrade-design.md` (수정 필요)

---

### 4. ✅ checklist.md — Phase 2에 2A-0 작업 그룹 추가
**상태**: 완료 ✅
**담당자**: Oracle (코드 아키텍트)

#### 추가 내용
- backend/agents/config.yaml 생성 (에이전트 YAML 정의)
- agent_registry.py 생성 (동적 팩토리, upsert 등록)
- setup.sh / init_agents.py 수정 (워크스페이스 자동 생성)
- main.py 하드코딩 제거

#### 작업 항목 (이미 추가됨)
- [x] `backend/agents/config.yaml` 생성
- [x] `backend/agents/agent_registry.py` 생성
- [x] `backend/scripts/setup.sh` 수정
- [x] `backend/scripts/init_agents.py` 수정
- [x] `backend/main.py` 하드코딩 제거

#### 관련 파일
- ✅ `checklist.md` (수정 완료)

---

## 📊 작업 진행 상황

| 항목 | 상태 | 담당자 | 우선순위 | 예상 시간 |
|------|------|--------|---------|----------|
| **1. context.md LLM 스택 교체** | ✅ 완료 | Sisyphus | 높음 | 완료 |
| **2. plan.md DB 스키마 수정** | ⏳ 진행 중 | Oracle | 높음 | 30분 |
| **3. design.md DB 스키마 수정** | ⏳ 진행 중 | Oracle | 높음 | 30분 |
| **4. design.md 아키텍처 다이어그램 추가** | ⏳ 진행 중 | Oracle | 높음 | 1시간 |
| **5. checklist.md 2A-0 작업 그룹 추가** | ✅ 완료 | Oracle | 높음 | 완료 |

---

## 🚀 구현 단계별 상세 계획

### Step 1: DB 스키마 수정 (plan.md + design.md)

#### 1.1 plan.md 수정
**작업자**: Oracle
**예상 시간**: 30분

**수정 내용**:
```sql
-- projects 테이블
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- agents 테이블
CREATE TABLE agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL,
    soul_template VARCHAR(100),
    workspace_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- project_agents 테이블
CREATE TABLE project_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
    is_lead BOOLEAN DEFAULT FALSE,
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, agent_id)
);

-- messages 테이블
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL,
    sender_id INTEGER,
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'chat',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- discussions 테이블
CREATE TABLE discussions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    topic VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);

-- votes 테이블
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

#### 1.2 design.md 수정
**작업자**: Oracle
**예상 시간**: 30분

**수정 내용**: 위와 동일

---

### Step 2: OpenClaw 연동 아키텍처 다이어그램 추가 (design.md)

#### 2.1 아키텍처 다이어그램 작성
**작업자**: Oracle
**예상 시간**: 1시간

**다이어그램 내용**:
```
┌─────────────────────────────────────────────────────────┐
│                    사용자 인터페이스                      │
│  ┌──────────────────────────────────────────────────┐  │
│  │         React Frontend (Vite + TypeScript)        │  │
│  │  - 프로젝트 관리                                   │  │
│  │  - 채팅 인터페이스                                 │  │
│  │  - 에이전트 초대                                   │  │
│  │  - 투표 패널                                       │  │
│  └──────────────┬───────────────────────────────────┘  │
└─────────────────┼───────────────────────────────────────┘
                  │
                  │ WebSocket + REST API
                  ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                      │
│  ┌──────────────────────────────────────────────────┐  │
│  │              AgentRegistry (YAML 기반)             │  │
│  │  - config.yaml 로드                               │  │
│  │  - 에이전트 동적 등록 (upsert)                     │  │
│  │  - 워크스페이스 자동 생성                          │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                        │
│  ┌──────────────┴───────────────────────────────────┐  │
│  │          LLMProviderService (Failover)            │  │
│  │  - DeepSeek V4 (메인)                             │  │
│  │  - DeepSeek R1 (추론)                             │  │
│  │  - Gemini 2.5 Flash (폴백#1)                      │  │
│  │  - Gemini 3 Flash Preview (폴백#2)                │  │
│  └──────────────┬───────────────────────────────────┘  │
└─────────────────┼───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│                 OpenClaw Gateway                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │         에이전트 워크스페이스 관리                  │  │
│  │  - workspaces/manager/                            │  │
│  │  - workspaces/developer/                          │  │
│  │  - workspaces/designer/                           │  │
│  │  - workspaces/researcher/                         │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                        │
│  ┌──────────────┴───────────────────────────────────┐  │
│  │              에이전트 인스턴스                     │  │
│  │  - SOUL.md 로드                                   │  │
│  │  - memory.json 관리                               │  │
│  │  - AGENTS.md 생성                                 │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

#### 2.2 agents.yaml 구조 예시 추가
**작업자**: Oracle
**예상 시간**: 30분

**YAML 구조**:
```yaml
# backend/agents/config.yaml
version: "1.0"
description: "OpenClaw 에이전트 설정"

agents:
  # 선임에이전트
  - name: manager
    role: lead
    display_name: "매니저"
    emoji: "👔"
    soul_template: "manager.md"
    model_default: "deepseek-v4"
    model_reasoning: "deepseek-r1"
    debate_style: "diplomatic"
    is_lead: true
    capabilities:
      - project_management
      - team_coordination
      - decision_making
      - agent_invitation
    
  # 기술 에이전트
  - name: developer
    role: technical
    display_name: "개발자"
    emoji: "💻"
    soul_template: "developer.md"
    model_default: "deepseek-v4"
    model_reasoning: "deepseek-r1"
    debate_style: "analytical"
    is_lead: false
    capabilities:
      - code_review
      - api_design
      - debugging
      - architecture
    
  # 디자인 에이전트
  - name: designer
    role: creative
    display_name: "디자이너"
    emoji: "🎨"
    soul_template: "designer.md"
    model_default: "deepseek-v4"
    model_reasoning: "deepseek-r1"
    debate_style: "diplomatic"
    is_lead: false
    capabilities:
      - ui_design
      - ux_optimization
      - visual_review
      - prototyping
    
  # 리서치 에이전트
  - name: researcher
    role: analytical
    display_name: "리서처"
    emoji: "🔍"
    soul_template: "researcher.md"
    model_default: "deepseek-v4"
    model_reasoning: "deepseek-r1"
    debate_style: "analytical"
    is_lead: false
    capabilities:
      - market_research
      - data_analysis
      - trend_analysis
      - report_writing

# 확장 설정
extensions:
  max_agents_per_project: 10
  auto_invite_keywords:
    developer: ["코드", "API", "개발", "프로그래밍", "버그"]
    designer: ["디자인", "UI", "UX", "화면", "레이아웃"]
    researcher: ["조사", "분석", "데이터", "트렌드", "리서치"]
```

---

### Step 3: LLM Failover 체계 구현

#### 3.1 LLMProviderService 구현
**작업자**: Oracle
**예상 시간**: 2시간

**구현 내용**:
- `backend/services/llm_provider_service.py` 생성
- DeepSeek V4/R1 Provider 구현
- Gemini 2.5 Flash Provider 구현
- Gemini 3 Flash Preview Provider 구현
- Failover 로직 구현
- 통계 추적 구현

#### 3.2 API 엔드포인트 구현
**작업자**: Oracle
**예상 시간**: 1시간

**구현 내용**:
- `GET /api/llm/stats` - LLM Provider별 통계 조회
- `GET /api/llm/health` - LLM Provider 상태 확인

---

## 📋 작업 할당

### Oracle (코드 아키텍트)
**담당 작업**:
1. ⏳ plan.md DB 스키마 수정 (30분)
2. ⏳ design.md DB 스키마 수정 (30분)
3. ⏳ design.md 아키텍처 다이어그램 추가 (1시간)
4. ⏳ LLMProviderService 구현 (2시간)
5. ⏳ API 엔드포인트 구현 (1시간)

**총 예상 시간**: 5시간

### Frontend-Engineer
**담당 작업**:
- 없음 (이번 작업은 백엔드 중심)

### Sisyphus (팀 리더)
**담당 작업**:
1. ✅ context.md LLM 스택 교체 (완료)
2. ✅ LLM Failover 설계도 작성 (완료)
3. ⏳ 작업 진행 상황 모니터링
4. ⏳ 최종 검수 및 문서화

**총 예상 시간**: 2시간

---

## ⚠️ 리스크 및 대응 방안

### 리스크 1: API 키 발급 지연
**확률**: 중간
**영향**: 높음
**대응 방안**:
- DeepSeek API 키 먼저 발급
- Gemini API 키는 Google AI Studio에서 무료 발급 가능

### 리스크 2: DB 마이그레이션 실패
**확률**: 낮음
**영향**: 높음
**대응 방안**:
- 기존 DB 백업 후 진행
- SQLite → PostgreSQL 마이그레이션 스크립트 작성

### 리스크 3: LLM API 호출 제한 초과
**확률**: 중간
**영향**: 중간
**대응 방안**:
- 캐싱 전략 수립
- Rate limiting 구현
- Gemini 폴백 자동 전환

---

## ✅ 완료 기준

### 기술적 완료 기준
- [ ] 모든 DB 스키마가 INTEGER PRIMARY KEY AUTOINCREMENT로 통일
- [ ] ON DELETE CASCADE가 모든 외래키에 적용됨
- [ ] UNIQUE 제약조건이 올바르게 적용됨
- [ ] OpenClaw 연동 아키텍처 다이어그램이 명확하게 작성됨
- [ ] agents.yaml 구조가 확장 가능하게 설계됨
- [ ] LLMProviderService가 Failover 로직을 포함하여 구현됨
- [ ] API 엔드포인트가 구현되고 테스트됨

### 문서적 완료 기준
- [ ] 모든 수정 사항이 문서에 반영됨
- [ ] 작업 계획서가 최신 상태로 유지됨
- [ ] API 문서가 작성됨
- [ ] 배포 가이드가 작성됨

---

## 📚 관련 문서

- **LLM Failover 설계도**: `docs/superpowers/specs/2026-04-06-llm-failover-design.md`
- **OpenClaw 업그레이드 설계**: `docs/superpowers/specs/2026-04-06-openclaw-upgrade-design.md`
- **구현 계획서**: `plan.md`
- **기술 스택**: `context.md`
- **작업 체크리스트**: `checklist.md`

---

## 📅 마일스톤

### Milestone 1: DB 스키마 수정 완료
**예상 완료일**: 2026-04-06
**담당자**: Oracle
**산출물**:
- plan.md 수정 완료
- design.md 수정 완료

### Milestone 2: 아키텍처 다이어그램 완료
**예상 완료일**: 2026-04-06
**담당자**: Oracle
**산출물**:
- design.md에 다이어그램 추가
- agents.yaml 구조 예시 추가

### Milestone 3: LLM Failover 구현 완료
**예상 완료일**: 2026-04-07
**담당자**: Oracle
**산출물**:
- LLMProviderService 구현
- API 엔드포인트 구현
- 단위 테스트 완료

### Milestone 4: 최종 검수 완료
**예상 완료일**: 2026-04-07
**담당자**: Sisyphus
**산출물**:
- 전체 문서 검수
- 작업 계획서 최종 업데이트
- 배포 준비 완료

---

**작성자**: Sisyphus (팀 리더)
**작성일**: 2026-04-06
**상태**: 구현 대기
**다음 검토일**: 2026-04-07
