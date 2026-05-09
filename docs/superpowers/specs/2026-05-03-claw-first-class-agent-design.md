# 클로(Claw) 정식 팀원화 설계 문서

**작성일**: 2026-05-03
**작성자**: Codex
**상태**: 설계 승인 대기
**버전**: 1.0

---

## 문서 목적

OpenClaw Gateway 기반 실행 봇인 **클로(Claw)** 를 예외 처리되는 특수 봇이 아니라, 영스팀의 **정식 팀원**으로 승격하는 설계를 정의한다.

목표는 세 가지다.

1. 사용자가 클로를 일반 팀원처럼 직접 부를 수 있게 한다.
2. 네오, 아서, 소피아, 루나가 클로의 존재와 역할을 시스템적으로 인식하게 한다.
3. 클로 관련 처리 로직을 `main.py`의 특수 분기에서 제거하고, 일반 에이전트 파이프라인으로 통합한다.

---

## 문제 정의

현재 클로는 다음과 같은 한계를 가진다.

### 1. 시스템적으로는 정식 팀원이 아니다

- DB의 정식 `Agent` 레코드가 아니라, 일부 경로에서만 `openclaw-bot`이라는 가상 객체로 취급된다.
- 일반 에이전트와 다른 payload 스키마를 사용해 프론트/UI 버그가 발생했다.
- 초대, 멘션, working bar, archive, reply 흐름에서 일관성이 없다.

### 2. `main.py` 특수 분기에 과도하게 의존한다

- `@클로` 감지 시 별도 WebSocket 응답을 직접 보내는 구조다.
- 이 구조는 일반 에이전트 응답 흐름과 분리되어 있어 중복과 불일치를 만든다.

### 3. 다른 팀원이 “프롬프트상으로만” 클로를 안다

- 템플릿에 설명을 넣는 것만으로는 충분하지 않다.
- 실제 초대/위임/역할 인식은 엔진과 라우팅 시스템이 보장해야 한다.

---

## 설계 원칙

1. **정식 팀원 원칙**
- 클로는 가상 봇이 아니라 `Agent` 모델 안의 정식 팀원으로 표현한다.

2. **단일 응답 파이프라인 원칙**
- 클로 응답도 다른 에이전트와 동일한 `agent_response` 구조를 사용한다.

3. **실행 담당 원칙**
- 클로는 분석가가 아니라 실행 담당이다.
- “생각”보다 “실행”, “외부 시스템 조작”, “도구 연결”에 특화된 역할로 정의한다.

4. **명시적 상태 원칙**
- 클로는 단순한 응답자만이 아니라, Gateway 연결 상태와 승인 상태를 말할 수 있어야 한다.

5. **예외 최소화 원칙**
- `main.py`의 멘션 특수 분기를 줄이고, 가능한 한 `ConversationEngine`, `InviteEngine`, `Agent` 레이어로 이동한다.

---

## 목표 UX

### 사용자가 보는 경험

- 사용자는 `클로야`, `@클로`, `@openclaw`로 클로를 직접 부를 수 있다.
- 클로는 네오/아서/소피아/루나처럼 동일한 말풍선 형식으로 응답한다.
- 사이드바와 팀 카드에 클로가 다른 팀원과 함께 보인다.
- 클로가 불가능한 작업이면 “승인 필요”, “Gateway 오프라인”, “실행 권한 부족” 같은 상태를 명확히 말한다.

### 팀원이 보는 경험

- 네오는 “이건 클로가 맡는 게 맞다”고 제안할 수 있다.
- 아서는 코드 구현 중 시스템 명령/빌드/외부 명령이 필요하면 클로를 호출할 수 있다.
- 루나는 외부 수집/스크래핑/검증을 클로에게 넘길 수 있다.
- 소피아는 이미지 변환/파일 처리 같은 시스템 작업을 클로에게 요청할 수 있다.

---

## 핵심 설계 결정

### 결정 1. 클로를 정식 `Agent` 레코드로 등록한다

권장 Agent 예시:

```json
{
  "id": "openclaw-bot",
  "name": "클로",
  "role": "operator",
  "display_name": "클로 실행담당",
  "emoji": "🤖",
  "badge_text": "실행담당",
  "icon": "smart_toy",
  "color": "#E85D3A",
  "status": "active"
}
```

### 결정 2. 클로 전용 에이전트 클래스를 도입한다

신규 클래스:

- `backend/agents/openclaw_agent.py`

역할:

- 일반 LLM 기반 사고형 에이전트가 아니라 실행형 에이전트
- 내부적으로 `OpenClawService.execute_instruction()` 호출
- 결과를 일반 agent response 형식으로 반환

### 결정 3. 클로는 별도 role을 가진다

현재 프론트/백엔드는 `manager | developer | designer | researcher | bot` 수준의 사고를 하고 있다.

권장 role:

- `operator`

이유:

- `bot`은 너무 표현이 약하고 역할 의미가 없다.
- `operator`는 실행/제어 담당이라는 의미가 명확하다.
- OpenClaw Gateway의 protocol role과도 개념적으로 일치한다.

단, 점진적 전환을 위해 Phase 1에서는 `bot` 유지도 가능하다.

권장 방향:

- 단기: `bot` 호환 유지
- 중기: `operator`를 정식 role로 추가

### 결정 4. 멘션 처리도 일반 invite/routing 시스템으로 통합한다

현재:

- `main.py`에서 `CLAW_MENTION_PATTERN`을 직접 감지하고 별도 처리

목표:

- `InviteEngine.parse_mentions()`가 `@클로`, `@openclaw`를 인식
- `ConversationEngine._determine_agents()`가 `클로`, `클로야`, `클로를` 등 자연어 호출을 인식
- 클로도 일반 agent selection 결과에 포함

---

## 아키텍처 개요

```text
User Message
  -> Mention / routing analysis
  -> ConversationEngine selects agents
  -> OpenClawAgent selected when appropriate
  -> OpenClawAgent delegates to OpenClawService
  -> Standard agent_response event
  -> Frontend renders like any other team member
```

---

## 데이터 모델 설계

### Agent role 확장

현재 프론트 타입:

- `manager | developer | designer | researcher | bot`

권장 확장:

- `manager | developer | designer | researcher | operator`

또는 하위 호환 전환안:

- 백엔드 DB role은 `operator`
- 프론트는 `operator | bot` 둘 다 허용

### Agent 메타데이터

클로는 다음 메타데이터를 가져야 한다.

- `display_name`: 클로 실행담당
- `badge_text`: 실행담당 / Gateway
- `emoji`: 🤖
- `description`: Mac Mini Gateway를 통해 실제 작업을 수행하는 실행 담당

### 상태 모델

권장 상태:

- `active`
- `offline`
- `auth_required`
- `pairing_required`
- `degraded`

단기에는 `status` 문자열만 재사용하고, UI에 해석 레이어를 둔다.

---

## 백엔드 설계

### 1. 신규 `OpenClawAgent` 추가

파일:

- `backend/agents/openclaw_agent.py`

역할:

- `BaseAgent`를 상속
- `respond()` 또는 엔진에서 기대하는 인터페이스를 구현
- 입력 메시지를 OpenClaw instruction으로 변환
- OpenClawService 실행 결과를 텍스트 응답으로 반환

책임:

- 실행 요청 전달
- 실패 사유를 사용자 친화적으로 번역
- 필요 시 상태 메시지 제공

예:

- “Gateway 연결이 끊겨 있어 지금은 실행할 수 없습니다.”
- “Pairing 승인이 필요합니다. Mac Mini에서 승인 후 다시 시도해 주세요.”

### 2. `main.py` 특수 분기 제거

현재:

- `CLAW_MENTION_PATTERN` 발견 시 `main.py`에서 직접 WebSocket 이벤트 발행

목표:

- 이 로직을 단계적으로 제거
- 멘션 감지만 남기거나 아예 `ConversationEngine`로 이동
- 응답 전송은 일반 `engine.process_message()` 결과로만 처리

전환 단계:

#### Phase A

- 기존 분기는 유지하되, 내부적으로 `OpenClawAgent`를 호출하도록 얇게 만든다.

#### Phase B

- `main.py` 특수 분기 제거
- `resolved_agent_ids`에 클로가 포함되도록 일반 라우팅만 사용

### 3. `ConversationEngine` 라우팅 확장

파일:

- `backend/engines/conversation_engine.py`

추가할 것:

- `operator` role 키워드 맵
- 자연어 호출 패턴:
  - `클로`
  - `@클로`
  - `@openclaw`
  - `클로야`
  - `클로를`
  - `클로한테`
  - `클로에게`

도메인 키워드도 추가 가능:

- `실행`
- `명령`
- `터미널`
- `파일 처리`
- `브라우저 조작`
- `게이트웨이`

### 4. `InviteEngine` / mention 처리 확장

현재 mention 시스템은 role 기반으로 동작한다.

필요 변경:

- `@클로`, `@openclaw`를 operator agent로 해석
- 클로도 invite suggestion 대상이 되게 함

예:

- 네오가 “이건 클로가 처리하는 게 맞다”고 말하면 invite suggestion 생성
- 사용자가 승인하면 클로가 프로젝트 바인딩

### 5. 상태 조회 API 추가

신규 권장 API:

- `GET /api/openclaw/status`

반환 예시:

```json
{
  "enabled": true,
  "reachable": true,
  "authenticated": false,
  "state": "pairing_required",
  "message": "Mac Mini에서 pairing 승인 필요"
}
```

이 상태를 Agent status와 연결해 UI에 반영한다.

---

## 프론트엔드 설계

### 1. 클로를 에이전트 목록에 정식 포함

파일:

- `frontend/src/agentConfig.ts`
- `frontend/src/types.ts`
- `frontend/src/components/Sidebar.tsx`

변경 사항:

- `operator` role 지원
- `getFallbackAgents()`에 클로 포함 가능하게 검토
- 사이드바에 클로를 다른 팀원과 동일하게 표시

### 2. role 스타일 확장

현재 `bot` 색상 규칙이 존재한다.

선택지:

- 단기: `operator`가 없으면 `bot` 스타일 재사용
- 중기: `operator` 색상/뱃지 별도 정의

권장 스타일:

- 색상: 주황/레드 계열 유지
- icon: `smart_toy` 또는 `memory`
- badge: `실행담당`

### 3. 상태 배지 추가

예시 상태 표시:

- `연결됨`
- `승인 필요`
- `오프라인`
- `권한 부족`

위치는:

- 사이드바 agent status dot
- Agent card subtitle
- Header 또는 AdminSettings

### 4. 메시지 렌더링 통일

클로도 반드시 일반 에이전트와 동일한 payload 스키마를 사용한다.

표준:

```json
{
  "type": "agent_response",
  "agent_id": "openclaw-bot",
  "agent_name": "클로",
  "agent_role": "operator",
  "content": "..."
}
```

---

## 프롬프트/협업 설계

### 팀원 설명

모든 팀원 템플릿에 아래 내용을 포함한다.

- 클로는 Mac Mini Gateway를 통해 실제 실행을 담당한다.
- 외부 시스템 변경, 시스템 명령, 브라우저 조작, 파일 처리 같은 작업은 클로에게 적합하다.
- 클로는 분석용 에이전트가 아니라 실행용 에이전트다.

### 호출 기준

네오/아서/소피아/루나가 클로를 언제 불러야 하는지 명확히 적는다.

예:

- 네오: “실행이 필요하면 클로를 부른다”
- 아서: “빌드/스크립트/시스템 명령이 필요하면 클로를 부른다”
- 루나: “외부 수집과 검증이 필요하면 클로를 부른다”
- 소피아: “파일 변환/에셋 처리/도구 실행이 필요하면 클로를 부른다”

### 핸드오프 문장 패턴

권장 예시:

- “이건 클로가 처리하는 게 맞습니다. 클로를 호출하겠습니다.”
- “실행 작업이 필요하니 클로에게 넘기겠습니다.”
- “외부 명령이 필요한 작업이라 클로 담당입니다.”

---

## 운영 상태 설계

클로는 단순 응답자보다 “실행 인프라 상태를 대표하는 팀원”이어야 한다.

### 상태 분류

- `online`: Gateway 연결 + 인증 성공
- `pairing_required`: WS 연결은 되나 승인 필요
- `auth_failed`: 토큰/권한 문제
- `offline`: Gateway 연결 실패
- `degraded`: 일부 기능만 가능

### UI 반영

- online: 녹색
- pairing_required: 노란색
- auth_failed: 주황색
- offline: 회색/빨간색

---

## 전환 전략

### Phase 1: 정식 메타데이터화

- DB에 클로 추가
- 프론트 role/스타일 지원
- 에이전트 목록에 표시
- 일반 payload 스키마 통일

### Phase 2: 실행 에이전트화

- `OpenClawAgent` 추가
- `main.py` 특수 분기를 얇게 축소
- 일반 agent response 파이프라인 연결

### Phase 3: 라우팅 통합

- `ConversationEngine`와 `InviteEngine`에서 클로를 정식 agent로 선택
- 다른 팀원이 클로를 호출/초대 가능하게 함

### Phase 4: 상태/운영 완성

- Gateway 상태 API 추가
- 상태 배지/UI 반영
- pairing/auth failure UX 개선

---

## 테스트 전략

### 단위 테스트

- `@클로`, `클로야`, `클로를`, `클로한테` 라우팅 검증
- `OpenClawAgent`가 일반 응답 스키마를 반환하는지 검증
- 클로 상태별 메시지 검증

### 통합 테스트

- 클로가 에이전트 목록에 나타나는지
- `@클로 안녕` 시 클로만 응답하는지
- `네오야, 클로를 불러줘` 시 의도한 정책대로 동작하는지
- OpenClaw 비활성 상태에서도 클로 이름으로 에러가 표시되는지

### UX 테스트

- 클로가 다른 팀원과 같은 말풍선 스타일로 보이는지
- working bar, archive, reply, mention dropdown에서 일관되게 보이는지

---

## 정책 결정이 필요한 항목

1. 클로 role을 `bot`으로 유지할지 `operator`로 승격할지
2. 사용자가 `네오야, 클로를 불러줘`처럼 복합 멘션했을 때
   - 네오만 응답할지
   - 클로만 응답할지
   - 네오와 클로가 순차 참여할지
3. 클로를 기본 팀원으로 항상 프로젝트에 포함할지
   - 항상 포함
   - 필요 시 초대
4. 클로의 실패 메시지를 일반 팀원 톤으로 바꿀지, 시스템 메시지처럼 유지할지

---

## 권장 결론

가장 좋은 방향은 다음이다.

1. 클로를 `Agent` 테이블의 정식 팀원으로 등록
2. 전용 `OpenClawAgent` 도입
3. role은 `operator`로 승격
4. `main.py` 특수 분기를 제거하고 일반 ConversationEngine 라우팅으로 통합
5. 상태를 팀 UI에서 명시적으로 보여줌

이 방향으로 가면 클로는 “봇 하나 덧붙인 기능”이 아니라, 영스팀의 **실행 담당 팀원**으로 자리 잡을 수 있다.
