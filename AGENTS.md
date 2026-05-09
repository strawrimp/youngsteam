# AGENTS.md

이 파일은 OpenCode AI 에이전트가 프로젝트를 이해하는 데 필요한 정보를 제공합니다.

## Project Overview

my-ai-company is a multi-agent AI system with OpenClaw Gateway integration for delegating real-world tasks to Mac Mini.

## Current Progress

### Completed
- ✅ 프로젝트 초기화
- ✅ OpenClaw Gateway 연동 (WebSocket operator-mode, device token persistence, factory pattern)
  - `backend/services/openclaw_service.py` — 서비스 레이어
  - `backend/services/openclaw_ws_client.py` — WS 게이트웨이 클라이언트
  - `backend/repositories/openclaw_device_store.py` — 디바이스 토큰 저장소
  - `backend/tools/openclaw_tool.py` — `delegate_to_openclaw` 도구
  - `backend/tests/test_openclaw_integration.py` — 10개 단위 테스트
  - `backend/config.py` / `.env.example` — 환경변수 설정
  - `backend/tools/__init__.py` — 조건부 툴 등록
  - `backend/services/agent_executor.py` — Agent system prompt 통합
  - `backend/scripts/test_openclaw_connection.py` — 연결 테스트 스크립트
- ✅ Claw(openclaw-bot) API 노출 및 DB 경로 안정화
  - DB 경로 절대화 (`config.py`): `DATABASE_URL` → 절대 경로 `sqlite:///backend/ai_company.db`
  - Seed 로직 upsert 전환 (`seed.py`): `session.add_all` → role/id 기준 upsert (멱등성 보장)
  - DB 경로 서버 로깅 (`main.py`): startup 시 실제 SQLite 파일 경로 출력
  - 검증 스크립트 (`backend/scripts/check_db_state.py`): DB 일관성 검증 도구
  - Claw(id: `openclaw-bot`, role: `bot`, status: `active`) — `/api/agents`에 5명 모두 정상 반환 확인

### Completed
- ✅ E2E 브라우저 검증 (browse skill)
  - `frontend/.env` 생성 (`VITE_BACKEND_PORT=7518`) — 프론트엔드가 WS 서버(7521) 대신 올바른 백엔드(7518)를 호출하도록 수정
  - 발견: 포트 7521에 오래된 `main.py` 인스턴스(PID 18692)가 실행 중이었고, 이전 코드/DB로 Claw만 반환 — 프론트엔드가 잘못된 포트로 API 호출 중이었음
  - 수정: 오래된 인스턴스 종료(kill 18692), port 7521 정리
  - 결과: 콘솔 `[App] Loaded agents: 5` 확인, UI에 전원 표시 (네오/아서/소피아/루나/클로)
  - WebSocket도 포트 7518에서 정상 연결 확인

### Pending
- ⏳ E2E 실환경 검증 (Mac Mini Gateway 필요)

## Build Commands

### Core Commands
- `npm install` - 의존성 설치
- `npm run dev` - 개발 서버 실행
- `npm run build` - 프로덕션 빌드

## Code Style Guidelines

### TypeScript
- Target: ES2022
- Strict mode enabled
- Functional components with React.FC

### Naming Conventions
- **Components**: PascalCase
- **Functions/Variables**: camelCase
- **Constants**: UPPER_SNAKE_CASE
- **Types/Interfaces**: PascalCase

### Styling (Tailwind CSS)
- Use utility classes
- Spacing: `p-3`, `m-2`, `gap-4`
- Colors: `text-gray-800`, `bg-emerald-500`

## Multi-Agent System (Oh My OpenCode)

### Agent Roles

| 에이전트 | 역할 | 전문분야 |
|---------|------|---------|
| **Sisyphus** | 팀 리더 | 설계, 조율, 의사결정 |
| **Oracle** | 코드 아키텍트 | 코드작성, 리팩토링, 최적화 |
| **Frontend-Engineer** | 프론트엔드 전문가 | React, TypeScript, UI/UX |
| **Librarian** | 문서 검색 | 문서검색, 정보요약 |
| **Explore** | 코드 네비게이터 | 파일탐색, 코드분석 |
| **Multimodal-Looker** | 비전 분석 | 이미지분석, 디자인변환 |

### Workflow Patterns

1. **코드 생성**: Sisyphus → Oracle
2. **프론트엔드**: Sisyphus → Frontend-Engineer
3. **문서 작업**: Sisyphus → Librarian
4. **코드 탐색**: Sisyphus → Explore
5. **디자인 변환**: Sisyphus → Multimodal-Looker

## Auto-Applied Skills

이 프로젝트에서 자동으로 적용되는 스킬:
- `vercel-react-best-practices` - React 성능 최적화
- `web-design-guidelines` - 웹 디자인 가이드라인
- `frontend-design` - 프론트엔드 디자인 패턴
