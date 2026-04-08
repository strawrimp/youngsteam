# Phase 1D: WebSocket Events Extension Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OpenClaw 스타일 다중 에이전트 시스템의 WebSocket 이벤트 확장

**Architecture:** 
- FastAPI WebSocket + Connection Manager
- 이벤트 기반 실시간 업데이트
- 브로드캐스팅 및 유니캐스트 지원

**Tech Stack:** 
- Backend: FastAPI WebSocket, asyncio, pydantic

---

## 📁 파일 구조

### 새로 생성할 파일

```
backend/
├── websocket/
│   ├── __init__.py
│   ├── manager.py              # WebSocket 연결 관리자
│   └── events.py               # 이벤트 타입 정의
```

### 수정할 파일

```
backend/
├── main.py                     # WebSocket 핸들러 수정
├── routes/
│   ├── projects.py             # 프로젝트 이벤트 발행
│   ├── agents.py               # 에이전트 초대 이벤트 발행
│   ├── discussions.py          # 토론 이벤트 발행
│   └── votes.py                # 투표 이벤트 발행
```

---

## Task 1: WebSocket 이벤트 타입 정의

**Files:**
- Create: `backend/websocket/__init__.py`
- Create: `backend/websocket/events.py`

- [ ] **Step 1: websocket 디렉토리 생성**

```bash
mkdir -p /Volumes/Dock/2604/my-ai-company/backend/websocket
```

- [ ] **Step 2: 이벤트 타입 정의**

`backend/websocket/events.py` 생성:

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any, Dict


class EventType(str, Enum):
    """WebSocket 이벤트 타입"""
    # Project events
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    
    # Agent events
    AGENT_INVITED = "agent_invited"
    AGENT_REMOVED = "agent_removed"
    
    # Discussion events
    DISCUSSION_STARTED = "discussion_started"
    DISCUSSION_MESSAGE = "discussion_message"
    DISCUSSION_CLOSED = "discussion_closed"
    
    # Vote events
    VOTE_CAST = "vote_cast"
    VOTE_COMPLETED = "vote_completed"
    
    # Chat events (existing)
    CHAT_MESSAGE = "chat_message"
    AGENT_RESPONSE = "agent_response"
    TYPING_INDICATOR = "typing_indicator"


class WebSocketEvent(BaseModel):
    """WebSocket 이벤트 스키마"""
    type: EventType
    data: Dict[str, Any]
    timestamp: Optional[str] = None
    
    class Config:
        use_enum_values = True


# 편의 함수들
def create_event(event_type: EventType, data: Dict[str, Any]) -> Dict[str, Any]:
    """이벤트 생성 헬퍼 함수"""
    from datetime import datetime
    return {
        "type": event_type.value,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
```

- [ ] **Step 3: __init__.py 생성**

`backend/websocket/__init__.py` 생성:

```python
from websocket.events import EventType, WebSocketEvent, create_event
from websocket.manager import ConnectionManager

__all__ = [
    "EventType",
    "WebSocketEvent",
    "create_event",
    "ConnectionManager",
]
```

- [ ] **Step 4: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/websocket/ && git commit -m "feat(websocket): add event types definition"
```

---

## Task 2: WebSocket 연결 관리자 구현

**Files:**
- Create: `backend/websocket/manager.py`

- [ ] **Step 1: ConnectionManager 구현**

`backend/websocket/manager.py` 생성:

```python
from fastapi import WebSocket
from typing import List, Dict, Set
import logging
import json

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        # 모든 활성 연결
        self.active_connections: List[WebSocket] = []
        # 프로젝트별 연결 (project_id -> set of WebSocket)
        self.project_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        """새 WebSocket 연결 수락"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """WebSocket 연결 해제"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # 프로젝트 연결에서도 제거
        for project_id in list(self.project_connections.keys()):
            if websocket in self.project_connections[project_id]:
                self.project_connections[project_id].remove(websocket)
                if not self.project_connections[project_id]:
                    del self.project_connections[project_id]
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def subscribe_to_project(self, websocket: WebSocket, project_id: str):
        """프로젝트 구독"""
        if project_id not in self.project_connections:
            self.project_connections[project_id] = set()
        self.project_connections[project_id].add(websocket)
        logger.info(f"WebSocket subscribed to project {project_id}")
    
    async def unsubscribe_from_project(self, websocket: WebSocket, project_id: str):
        """프로젝트 구독 해제"""
        if project_id in self.project_connections:
            self.project_connections[project_id].discard(websocket)
            if not self.project_connections[project_id]:
                del self.project_connections[project_id]
        logger.info(f"WebSocket unsubscribed from project {project_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """특정 연결에 메시지 전송"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(self, message: dict):
        """모든 연결에 브로드캐스트"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
    
    async def broadcast_to_project(self, project_id: str, message: dict):
        """특정 프로젝트 구독자들에게 브로드캐스트"""
        if project_id not in self.project_connections:
            return
        
        for connection in list(self.project_connections[project_id]):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to project {project_id}: {e}")
    
    def get_project_subscribers_count(self, project_id: str) -> int:
        """프로젝트 구독자 수 조회"""
        return len(self.project_connections.get(project_id, set()))
```

- [ ] **Step 2: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/websocket/manager.py && git commit -m "feat(websocket): add ConnectionManager for WebSocket management"
```

---

## Task 3: 라우트에 WebSocket 이벤트 발행 추가

**Files:**
- Modify: `backend/routes/projects.py`
- Modify: `backend/routes/agents.py`
- Modify: `backend/routes/discussions.py`
- Modify: `backend/routes/votes.py`

- [ ] **Step 1: projects.py에 이벤트 발행 추가**

`backend/routes/projects.py` 수정:

```python
# 파일 상단에 import 추가
from websocket.events import EventType, create_event

# 전역 변수로 manager 받기 (main.py에서 주입)
ws_manager = None

def set_ws_manager(manager):
    """WebSocket manager 주입"""
    global ws_manager
    ws_manager = manager

# create_project 함수 수정
@router.post("/", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """새 프로젝트 생성"""
    db_project = Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # WebSocket 이벤트 발행
    if ws_manager:
        import asyncio
        event = create_event(EventType.PROJECT_CREATED, {
            "id": db_project.id,
            "name": db_project.name,
            "description": db_project.description
        })
        asyncio.create_task(ws_manager.broadcast(event))
    
    return db_project
```

- [ ] **Step 2: agents.py에 이벤트 발행 추가**

`backend/routes/agents.py` 수정:

```python
# 파일 상단에 import 추가
from websocket.events import EventType, create_event

ws_manager = None

def set_ws_manager(manager):
    global ws_manager
    ws_manager = manager

# invite_agent 함수 수정
@router.post("/invite")
def invite_agent(invite: AgentInviteRequest, db: Session = Depends(get_db)):
    """에이전트를 프로젝트에 초대"""
    # ... 기존 코드 ...
    
    # WebSocket 이벤트 발행
    if ws_manager:
        import asyncio
        event = create_event(EventType.AGENT_INVITED, {
            "project_id": binding.project_id,
            "agent_id": binding.agent_id,
            "is_lead": binding.is_lead,
            "agent_name": agent.name
        })
        asyncio.create_task(ws_manager.broadcast_to_project(invite.project_id, event))
    
    return {...}
```

- [ ] **Step 3: discussions.py에 이벤트 발행 추가**

`backend/routes/discussions.py` 수정:

```python
# 파일 상단에 import 추가
from websocket.events import EventType, create_event

ws_manager = None

def set_ws_manager(manager):
    global ws_manager
    ws_manager = manager

# create_discussion 함수 수정
@router.post("/", response_model=DiscussionResponse)
def create_discussion(discussion: DiscussionCreate, db: Session = Depends(get_db)):
    """새 토론 생성"""
    # ... 기존 코드 ...
    
    # WebSocket 이벤트 발행
    if ws_manager:
        import asyncio
        event = create_event(EventType.DISCUSSION_STARTED, {
            "id": db_discussion.id,
            "project_id": db_discussion.project_id,
            "topic": db_discussion.topic
        })
        asyncio.create_task(ws_manager.broadcast_to_project(discussion.project_id, event))
    
    return db_discussion

# create_discussion_message 함수 수정
@router.post("/{discussion_id}/messages", response_model=DiscussionMessageResponse)
def create_discussion_message(...):
    """토론에 메시지 전송"""
    # ... 기존 코드 ...
    
    # WebSocket 이벤트 발행
    if ws_manager:
        import asyncio
        event = create_event(EventType.DISCUSSION_MESSAGE, {
            "discussion_id": discussion_id,
            "agent_id": message.agent_id,
            "content": message.content
        })
        # 토론이 속한 프로젝트의 구독자들에게 전송
        asyncio.create_task(ws_manager.broadcast_to_project(
            discussion.project_id, event
        ))
    
    return db_message
```

- [ ] **Step 4: votes.py에 이벤트 발행 추가**

`backend/routes/votes.py` 수정:

```python
# 파일 상단에 import 추가
from websocket.events import EventType, create_event

ws_manager = None

def set_ws_manager(manager):
    global ws_manager
    ws_manager = manager

# create_vote 함수 수정
@router.post("/", response_model=VoteResponse)
def create_vote(vote: VoteCreate, db: Session = Depends(get_db)):
    """새 투표 생성"""
    # ... 기존 코드 ...
    
    # WebSocket 이벤트 발행
    if ws_manager:
        import asyncio
        event = create_event(EventType.VOTE_CAST, {
            "discussion_id": vote.discussion_id,
            "agent_id": vote.agent_id,
            "choice": vote.choice
        })
        # 토론이 속한 프로젝트의 구독자들에게 전송
        asyncio.create_task(ws_manager.broadcast_to_project(
            discussion.project_id, event
        ))
    
    return db_vote
```

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/routes/ && git commit -m "feat(routes): add WebSocket event broadcasting to all routes"
```

---

## Task 4: main.py WebSocket 핸들러 수정

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: ConnectionManager 초기화**

`backend/main.py` 수정:

```python
# 파일 상단에 import 추가
from websocket import ConnectionManager

# lifespan 함수 내에 manager 초기화 추가
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... 기존 코드 ...
    
    # WebSocket manager 초기화
    app.state.ws_manager = ConnectionManager()
    logger.info("✅ WebSocket Connection Manager initialized")
    
    # 라우트에 manager 주입
    from routes.projects import set_ws_manager
    from routes.agents import set_ws_manager
    from routes.discussions import set_ws_manager
    from routes.votes import set_ws_manager
    
    set_ws_manager(app.state.ws_manager)
    # 다른 라우트도 동일하게 호출
    
    yield
    
    # Cleanup
    logger.info("Shutting down...")
```

- [ ] **Step 2: WebSocket 핸들러 수정**

`backend/main.py`의 websocket_endpoint 수정:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication and agent interaction."""
    await app.state.ws_manager.connect(websocket)
    logger.info(f"WebSocket client connected: {websocket.client}")
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            logger.info(f"WebSocket received: {data}")
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                # Handle different actions
                if action == "subscribe_project":
                    # 프로젝트 구독
                    project_id = message.get("project_id")
                    if project_id:
                        await app.state.ws_manager.subscribe_to_project(websocket, project_id)
                        await app.state.ws_manager.send_personal_message({
                            "type": "subscribed",
                            "project_id": project_id
                        }, websocket)
                
                elif action == "unsubscribe_project":
                    # 프로젝트 구독 해제
                    project_id = message.get("project_id")
                    if project_id:
                        await app.state.ws_manager.unsubscribe_from_project(websocket, project_id)
                        await app.state.ws_manager.send_personal_message({
                            "type": "unsubscribed",
                            "project_id": project_id
                        }, websocket)
                
                elif action == "chat":
                    # 기존 채팅 로직 유지
                    # ... (기존 코드)
                    pass
                
                else:
                    await app.state.ws_manager.send_personal_message({
                        "error": f"Unknown action: {action}"
                    }, websocket)
            
            except json.JSONDecodeError:
                await app.state.ws_manager.send_personal_message({
                    "error": "Invalid JSON"
                }, websocket)
    
    except WebSocketDisconnect:
        app.state.ws_manager.disconnect(websocket)
        logger.info(f"WebSocket client disconnected")
    
    except Exception as e:
        logger.error(f"WebSocket error: {type(e).__name__}: {e}")
        app.state.ws_manager.disconnect(websocket)
```

- [ ] **Step 3: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/main.py && git commit -m "feat(websocket): integrate ConnectionManager with main.py and update handler"
```

---

## Task 5: 테스트 및 검증

- [ ] **Step 1: WebSocket 연결 테스트**

```bash
# 서버 시작
cd /Volumes/Dock/2604/my-ai-company/backend && python3 main.py

# 다른 터미널에서 WebSocket 클라이언트 테스트
# (wscat 또는 websocat 사용)
wscat -c ws://localhost:8000/ws
```

- [ ] **Step 2: 이벤트 브로드캐스트 테스트**

```json
// 프로젝트 구독
{"action": "subscribe_project", "project_id": "PROJECT_ID"}

// 프로젝트 생성 (다른 클라이언트에서 POST /api/projects 호출)
// → project_created 이벤트 수신 확인

// 에이전트 초대 (POST /api/agents/invite 호출)
// → agent_invited 이벤트 수신 확인
```

- [ ] **Step 3: 최종 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add -A && git commit -m "feat(websocket): complete Phase 1D - real-time event system implemented"
```

---

## Self-Review 체크리스트

- [ ] **Spec coverage:** checklist.md의 모든 이벤트 타입이 구현되었는가?
  - project_created ✅
  - agent_invited ✅
  - discussion_started ✅
  - discussion_message ✅
  - vote_cast ✅

- [ ] **Connection management:** 연결 관리가 안전하게 구현되었는가?
  - connect/disconnect ✅
  - subscribe/unsubscribe ✅
  - error handling ✅

- [ ] **Event broadcasting:** 이벤트가 올바르게 브로드캐스트되는가?
  - broadcast to all ✅
  - broadcast to project ✅
  - personal message ✅

- [ ] **Integration:** 라우트와 WebSocket이 올바르게 통합되었는가?
  - projects.py ✅
  - agents.py ✅
  - discussions.py ✅
  - votes.py ✅

---

**작업 담당자: @Sisyphus 👑**
