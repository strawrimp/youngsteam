# OpenClaw Gateway WebSocket 정식 연동 설계 문서

**작성일**: 2026-05-02
**작성자**: Codex
**상태**: 설계 승인 대기
**버전**: 2.0

---

## 문서 목적

Mac Studio의 `my-ai-company` 백엔드가 Mac Mini의 OpenClaw Gateway와 **정식 Gateway WebSocket 프로토콜**로 통신하도록 설계한다.

이 문서는 다음 문제를 해결하기 위한 구현 기준을 정의한다.

- 현재 WS 구현이 `connect.challenge` 이후 `connect` 핸드셰이크를 수행하지 않음
- 현재 WS 구현이 device auth와 paired device token 재사용을 지원하지 않음
- 현재 HTTP fallback이 OpenClaw `2026.3.28`의 알려진 `/v1/chat/completions` scope 회귀에 의존함
- 현재 요청 형식이 문서화된 WS RPC surface와 맞지 않음

---

## 배경

### 현재 확인된 사실

1. OpenClaw Gateway `2026.3.28`은 WS를 단순 소켓이 아닌 **제어 평면 프로토콜**로 사용한다.
2. WS 연결 직후 첫 클라이언트 프레임은 반드시 `connect` 요청이어야 한다.
3. `connect` 요청에는 다음 정보가 포함되어야 한다.
   - protocol version
   - operator role
   - requested scopes
   - auth token
   - challenge nonce에 묶인 device identity + signature
4. 성공 시 Gateway는 `hello-ok`와 함께 `auth.deviceToken`을 반환할 수 있으며, 이후 재연결에서 이를 재사용해야 한다.
5. OpenAI-compatible HTTP `/v1/chat/completions`는 문서상 지원되지만, `2026.3.28`에서는 `missing scope: operator.write` 회귀 이슈가 공개되어 있다.

### 따라서 내리는 설계 결론

- **실행 경로의 기준 프로토콜은 WS로 한다.**
- HTTP는 주 실행 경로가 아니라 **제한적 진단/비상 fallback**으로 취급한다.
- 구현의 핵심은 “메시지를 보내는 것”이 아니라 **paired operator client lifecycle**을 올바르게 구현하는 것이다.

---

## 목표

### 1차 목표

- Mac Studio에서 OpenClaw Gateway로 정식 WS 핸드셰이크 수행
- challenge-response 기반 device auth 구현
- paired device token 저장 및 재사용
- 문서화된 WS request/response/event framing 처리
- 자연어 지시를 OpenClaw 세션 실행으로 전달

### 비목표

- OpenClaw 내부 프로토콜 전체 구현
- Dashboard/Web UI와 동일한 전체 실시간 이벤트 동기화
- OpenClaw pairing approval UI 자체 구현
- HTTP `/v1/*` 회귀 자체 수정

---

## 아키텍처 개요

```text
my-ai-company Agent
  -> delegate_to_openclaw tool
  -> OpenClawService
  -> GatewayWsClient
  -> WS connect.challenge
  -> WS connect(req)
  -> hello-ok
  -> session/chat RPC
  -> agent completion / final response
```

### 책임 분리

- `OpenClawService`
  - 외부에 노출되는 상위 서비스 API
  - 툴 호출용 instruction/context를 실행 단위로 변환
  - WS 우선, HTTP는 제한적 fallback

- `GatewayWsClient`
  - 소켓 연결
  - handshake/auth/device token
  - request/response correlation
  - event consumption
  - reconnect policy

- `OpenClawDeviceStore`
  - device keypair / fingerprint
  - cached `deviceToken`
  - approved scopes
  - last successful gateway metadata

---

## 프로토콜 설계

### 1. 연결 수립

클라이언트는 `ws://172.30.1.18:18789/`에 연결한다.

서버가 먼저 보내는 프레임:

```json
{
  "type": "event",
  "event": "connect.challenge",
  "payload": { "nonce": "...", "ts": 1737264000000 }
}
```

클라이언트는 이 프레임을 받기 전까지 어떤 RPC도 보내면 안 된다.

### 2. connect 요청

클라이언트는 첫 요청으로 아래 구조의 `connect` 프레임을 전송한다.

```json
{
  "type": "req",
  "id": "uuid",
  "method": "connect",
  "params": {
    "minProtocol": 3,
    "maxProtocol": 3,
    "client": {
      "id": "my-ai-company",
      "version": "local-dev",
      "platform": "macos",
      "mode": "operator"
    },
    "role": "operator",
    "scopes": ["operator.read", "operator.write"],
    "caps": [],
    "commands": [],
    "permissions": {},
    "auth": {
      "token": "<gateway-token or deviceToken>"
    },
    "locale": "ko-KR",
    "userAgent": "my-ai-company/openclaw-integration",
    "device": {
      "id": "<stable-device-id>",
      "publicKey": "<public-key>",
      "signature": "<signature>",
      "signedAt": 1737264000000,
      "nonce": "<challenge nonce>"
    }
  }
}
```

### 3. connect 성공 처리

성공 응답 예시:

```json
{
  "type": "res",
  "id": "uuid",
  "ok": true,
  "payload": {
    "type": "hello-ok",
    "protocol": 3,
    "policy": {
      "tickIntervalMs": 15000
    },
    "auth": {
      "deviceToken": "...",
      "role": "operator",
      "scopes": ["operator.read", "operator.write"]
    }
  }
}
```

성공 시 해야 할 일:

1. `deviceToken` 영속화
2. 실제 승인된 scope 저장
3. `policy` 값으로 payload 한계와 keepalive 동작 조정
4. 이후부터만 application RPC 전송 허용

### 4. 재연결 정책

재연결 시 auth precedence는 다음 순서로 사용한다.

1. 명시적 shared token
2. 저장된 `deviceToken`
3. 기타 fallback 없음

설계상 권장 동작:

- 첫 연결 또는 인증 실패 복구 시: `gateway.auth.token`
- 한 번 연결 성공 후: 저장된 `deviceToken` 우선 사용
- `AUTH_TOKEN_MISMATCH` 또는 device auth 관련 에러 시: shared token으로 한 번만 재시도
- 반복 실패 시 자동 루프 중단 후 오류 surface

---

## Device Identity 설계

### 요구사항

- device identity는 **stable** 해야 한다.
- challenge nonce를 포함해 서명해야 한다.
- reconnect 시 같은 device identity를 유지해야 paired device로 인식된다.

### 로컬 저장 대상

신규 저장 파일:

```text
backend/state/openclaw_device.json
```

저장 필드:

- `device_id`
- `public_key`
- `private_key_ref` 또는 private key 저장 위치
- `device_token`
- `approved_scopes`
- `gateway_base_url`
- `last_connected_at`

### 키 관리 원칙

- 개발 단계에서는 로컬 파일 저장 허용
- 운영 전환 시 private key 저장 방식을 별도 보강 가능
- `.env`에 device token을 직접 넣지 않는다

---

## RPC 실행 모델

### 왜 기존 `chat.completions` WS 방식이 잘못되었는가

현재 구현은 JSON-RPC 스타일의 `chat.completions`를 전송하지만, 공개 문서 기준 Gateway WS는 다음 family를 중심으로 동작한다.

- `sessions.create`
- `sessions.send`
- `sessions.resolve`
- `chat.send`
- `agent.wait`
- `chat.history`

### 제안 실행 경로

#### 옵션 A: 세션 기반 실행

1. `sessions.create`
2. `sessions.send`
3. 필요 시 `agent.wait`
4. 최종 assistant 메시지 수집

장점:

- session lifecycle이 명확함
- 여러 턴 확장 가능
- 추후 대화형 OpenClaw 위임으로 확장 쉬움

단점:

- 구현량이 조금 더 많음

#### 옵션 B: chat 기반 실행

1. `chat.send`
2. streamed event 수신
3. 완료 이벤트에서 응답 조합

장점:

- 단순 instruction 위임에 적합

단점:

- 세션 재사용/추적성이 약할 수 있음

### 본 설계의 선택

**세션 기반 실행을 기본으로 채택한다.**

이유:

- 현재 `delegate_to_openclaw`는 단발성 자연어 위임처럼 보이지만, 실제 운영에서는 “후속 상태 확인”, “실패 재시도”, “승인 요구”가 생길 가능성이 높다.
- 세션 모델이 로그, 진단, 후속 확장에 유리하다.

---

## 서비스 계층 설계

### 제안 파일 구조

```text
backend/
├── services/
│   ├── openclaw_service.py
│   └── openclaw_ws_client.py
├── repositories/
│   └── openclaw_device_store.py
├── models/
│   └── openclaw_protocol.py
└── scripts/
    └── test_openclaw_connection.py
```

### `openclaw_service.py`

주요 메서드:

- `health_check()`
- `execute_instruction(instruction, context, agent_name=None)`
- `check_gateway_capabilities()`
- `explain_last_error()`

역할:

- 비즈니스 API 제공
- instruction을 OpenClaw 세션 실행으로 매핑
- WS client 세부사항 은닉

### `openclaw_ws_client.py`

주요 메서드:

- `connect()`
- `handshake()`
- `send_request(method, params)`
- `create_session()`
- `send_session_message(session_key, content)`
- `wait_for_completion(session_key or run_id)`
- `close()`

역할:

- 프로토콜 전담
- request id correlation
- event stream consumption
- reconnect handling

### `openclaw_device_store.py`

주요 메서드:

- `load_or_create_device_identity()`
- `get_device_token()`
- `save_handshake_result()`
- `clear_invalid_token()`

---

## 오류 처리 설계

### 오류 분류

1. **Transport 오류**
   - DNS 실패
   - TCP connect 실패
   - WS close
   - timeout

2. **Handshake 오류**
   - `connect.challenge` 미수신
   - invalid first frame
   - protocol version mismatch
   - auth token mismatch
   - device nonce/signature mismatch
   - pairing required

3. **Runtime RPC 오류**
   - unknown method
   - missing scope
   - invalid params
   - run timeout

4. **Gateway 회귀/호환성 오류**
   - HTTP `/v1/*` scope 회귀
   - 특정 method family 등록 누락

### 오류 surface 원칙

- 사용자 메시지는 실행 가능해야 한다.
- 로그에는 gateway close code, request id, method, error details를 남긴다.
- `error.details.code`가 있으면 그대로 보존한다.

예시:

- `DEVICE_AUTH_NONCE_REQUIRED`
- `DEVICE_AUTH_SIGNATURE_INVALID`
- `AUTH_TOKEN_MISMATCH`
- `pairing-required`

---

## 상태 점검 설계

`health_check()`는 단순히 소켓 오픈만 보면 안 된다.

### 정상 판정 기준

최소 조건:

1. Gateway TCP/WS 연결 가능
2. `connect.challenge` 수신 가능
3. `connect` 성공 또는 명시적 pairing-required 확인 가능

### 점검 단계

1. `/health` HTTP 확인
2. WS 연결
3. challenge 수신
4. connect 시도
5. 결과를 `ready`, `auth_failed`, `pairing_required`, `unreachable` 중 하나로 분류

---

## HTTP fallback 정책

### 기본 원칙

- HTTP는 기본 실행 경로가 아니다.
- `2026.3.28`에서는 `/v1/chat/completions`와 `/v1/models`가 `missing scope` 회귀를 보일 수 있다.

### 허용 범위

- `/health` 상태 확인
- 명시적으로 사용자가 HTTP 강제 디버깅을 요청한 경우

### 금지 범위

- 정상 업무 위임 실행 경로로 `/v1/chat/completions`를 신뢰하지 않음

---

## 설정 설계

### 환경변수

```bash
OPENCLAW_ENABLED=true
OPENCLAW_BASE_URL=http://172.30.1.18:18789
OPENCLAW_API_KEY=...
OPENCLAW_TIMEOUT=180
OPENCLAW_WS_ENABLED=true
OPENCLAW_WS_ENDPOINT=ws://172.30.1.18:18789/
OPENCLAW_DEVICE_STATE_PATH=backend/state/openclaw_device.json
OPENCLAW_REQUESTED_SCOPES=operator.read,operator.write
```

### 추가 설정 설명

- `OPENCLAW_WS_ENDPOINT`
  - 기본은 `/`
  - 문서상 Gateway WS는 same port multiplex이므로 별도 `/v1/ws` 추측 탐색은 제거 가능

- `OPENCLAW_DEVICE_STATE_PATH`
  - paired operator state 저장 위치

- `OPENCLAW_REQUESTED_SCOPES`
  - 초기에 `operator.read,operator.write`
  - admin scope는 기본 요청값으로 넣지 않음

---

## 보안 설계

### 원칙

1. Gateway token은 소유자 권한에 가까운 credential로 취급한다.
2. device token은 paired scope 내에서만 재사용한다.
3. destructive instruction은 상위 agent/tool 계층에서 별도 확인 정책을 둘 수 있다.

### 구현 원칙

- Authorization 헤더 기반 WS 인증에 의존하지 않는다.
- 문서 기준대로 `connect.params.auth.*`를 사용한다.
- private key와 device token은 로그에 남기지 않는다.
- raw frame 전체를 디버그 로그로 남기지 않는다.

---

## 테스트 전략

### 단위 테스트

`backend/tests/test_openclaw_integration.py` 확장:

- challenge 수신 후 connect frame 생성 검증
- invalid first frame 방지 검증
- `hello-ok.auth.deviceToken` 저장 검증
- reconnect 시 device token 사용 검증
- handshake error mapping 검증
- 403 HTTP 오류 메시지 보존 검증

### 통합 테스트

신규 또는 확장:

- 로컬 mock gateway로 protocol happy path 검증
- pairing-required 응답 검증
- bad nonce / bad signature 검증
- session create/send/wait 흐름 검증

### 수동 검증

1. Mac Mini Gateway 실행
2. 첫 연결 시 pairing 필요 여부 확인
3. pairing 승인 후 재연결
4. 단순 instruction 위임
5. Mac Studio 프로세스 재시작 후 device token 재사용 확인

---

## 단계별 구현 계획

### Phase 1: 프로토콜 기반 정리

1. 기존 WS probe 로직 단순화
2. `GatewayWsClient` 골격 추가
3. challenge -> connect -> hello-ok handshake 구현
4. device state 저장소 추가

### Phase 2: 세션 실행 경로 구현

5. `sessions.create` / `sessions.send` / `agent.wait` 연결
6. 최종 assistant 출력 추출
7. tool-facing `execute_instruction()` 완성

### Phase 3: 오류/복구 강화

8. pairing-required surface 개선
9. token mismatch 복구
10. timeout / reconnect / cancellation 처리

### Phase 4: 테스트 및 운영화

11. mock gateway 통합 테스트
12. 실 Gateway 수동 검증
13. HTTP fallback 범위 축소 및 문서화

---

## 기존 구현 대비 변경점

### 제거

- WS endpoint 추측 탐색 중심 설계
- 첫 프레임으로 JSON-RPC 전송하는 방식
- `chat.completions` WS method 가정
- HTTP `/v1/chat/completions`를 정상 fallback으로 보는 가정

### 추가

- `connect.challenge` 처리
- signed device auth
- paired `deviceToken` 저장 및 재사용
- session 기반 WS 실행 모델
- handshake-aware health check

---

## 오픈 이슈

1. OpenClaw의 device signature payload v3를 Python에서 어떻게 canonicalize할지
2. 최초 pairing-required 상태를 사용자에게 어떤 UX로 안내할지
3. `sessions.send`와 `chat.send` 중 실제 Gateway 응답 품질이 더 안정적인 쪽이 무엇인지
4. device state 저장 경로를 repo 내부에 둘지, 사용자 홈 디렉터리로 뺄지

---

## 권장 후속 작업

1. 이 설계를 기준으로 구현 계획 문서도 WS 기준으로 수정
2. `openclaw_service.py`를 `service`와 `ws_client`로 분리
3. mock gateway fixture를 먼저 만들고 그 위에서 handshake부터 고정

---

## 참고 기준

- OpenClaw Gateway Protocol 문서
- OpenClaw OpenAI Chat Completions 문서
- OpenClaw `2026.3.28` HTTP scope regression 이슈
