# AI 가상 회사 (Multi-Agent System)

다양한 역할을 수행하는 AI 에이전트들이 동등하게 참여하여 투표로 의견을 수렴하는 "나만의 AI 가상 회사"입니다.

## 기능

- **4명의 에이전트**: Manager (CEO), Developer, Designer, Researcher
- **동기적 협력**: 에이전트들이 동시에 정보를 처리하고 의견 교환
- **투표 기반 의견 수렴**: 모든 에이전트의 의견이 동등하게 평가됨
- **공유 메모리 시스템**: 모든 에이전트가 같은 컨텍스트를 유지
- **실시간 WebSocket 통신**: 웹 인터페이스에서 실시간으로 진행 상황 확인

## 기술 스택

| 계층 | 기술 |
|------|------|
| **백엔드** | Python 3.11+ + FastAPI |
| **프론트엔드** | React 18+ + TypeScript |
| **데이터베이스** | PostgreSQL 14+ |
| **AI 모델** | GLM (Zhipu AI) |
| **통신** | WebSocket + REST API |

## 프로젝트 구조

```
my-ai-company/
├── backend/
│   ├── main.py              # FastAPI 진입점
│   ├── config.py            # 설정
│   ├── database.py          # DB 연결
│   ├── models/              # SQLAlchemy ORM 모델
│   ├── agents/              # 에이전트 시스템
│   ├── services/            # 비즈니스 로직
│   ├── engines/             # 핵심 엔진 (추가 예정)
│   ├── routes/              # API 라우트 (추가 예정)
│   ├── requirements.txt      # Python 의존성
│   └── scripts/
│       ├── init_agents.py   # 에이전트 초기화
│       └── glm_spike.py     # GLM 스파이크 테스트
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/      # React 컴포넌트
│   │   ├── hooks/           # React 커스텀 훅
│   │   ├── store.ts         # Zustand 상태 관리
│   │   ├── App.tsx
│   │   └── index.tsx
│   └── package.json
└── README.md
```

## 설정 및 실행

### 1. 백엔드 설정

```bash
# 가상 환경 생성
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# 의존성 설치
cd backend
pip install -r requirements.txt

# 환경 변수 설정
cp ../.env.example ../.env
# .env 파일 수정: GLM_API_KEY 등 설정

# PostgreSQL 데이터베이스 생성
createdb ai_company

# 데이터베이스 초기화
python scripts/init_agents.py

# 서버 실행
python main.py
```

### 2. 프론트엔드 설정

```bash
cd frontend
npm install
npm start
```

### 3. GLM 스파이크 테스트 (선택사항)

```bash
cd backend
python scripts/glm_spike.py
```

## 개발 로드맵

### Phase 1: 기본 인프라 (완료 예정)
- [x] FastAPI 서버 셋업
- [x] PostgreSQL 데이터베이스 및 ORM 모델
- [x] React 기본 구조 + ChatWindow 컴포넌트
- [x] WebSocket 연결 구현
- [ ] echo 테스트 검증
- [ ] GLM 멀티에이전트 스파이크 테스트

### Phase 2: 단일 에이전트 시스템
- BaseAgent + Manager/Developer 구현
- GLMService 완성
- ConversationEngine 구현
- MemoryService 구현

### Phase 3: 토론 엔진 및 투표
- Researcher, Designer 에이전트 추가
- VotingEngine 구현
- DiscussionEngine 구현
- VotingInterface 컴포넌트

### Phase 4: 이미지 처리
- ImageService 구현
- Designer Agent에 이미지 기능 추가
- ImageInput/Output 컴포넌트

### Phase 5: UI 고도화
- 스타일링 및 반응형 디자인
- 성능 최적화
- 에러 처리 및 로깅

## API 엔드포인트 (Phase 1)

### REST API
- `GET /health` - 상태 확인
- `GET /api/agents` - 에이전트 목록
- `POST /api/chat/message` - 메시지 전송
- `GET /api/memory` - 공유 메모리 조회

### WebSocket
- `ws://localhost:8000/ws` - 실시간 통신

## 문제 해결

### PostgreSQL 연결 오류
```bash
# PostgreSQL 상태 확인
brew services list  # macOS

# 데이터베이스 생성
createdb ai_company
```

### 포트 충돌
```bash
# 다른 포트에서 실행
uvicorn main:app --port 8001
```

### WebSocket 연결 실패
브라우저 콘솔 확인 후, 백엔드 서버가 실행 중인지 확인하세요.

## 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [React 18 공식 문서](https://react.dev/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Zustand 상태 관리](https://github.com/pmndrs/zustand)

## 라이선스

MIT License
