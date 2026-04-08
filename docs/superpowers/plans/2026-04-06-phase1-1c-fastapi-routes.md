# Phase 1C: FastAPI Routes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OpenClaw 스타일 다중 에이전트 시스템의 FastAPI 라우트 구현

**Architecture:** 
- FastAPI + SQLAlchemy ORM + Pydantic
- RESTful API 설계
- 새 모델 (Project, ProjectAgent, Discussion, Vote) 활용

**Tech Stack:** 
- Backend: FastAPI, SQLAlchemy, Pydantic, pytest

---

## 📁 파일 구조

### 새로 생성할 파일

```
backend/
├── routes/
│   ├── projects.py              # 프로젝트 CRUD
│   ├── agents.py                # 에이전트 관리 및 초대
│   ├── discussions.py           # 토론 시스템
│   └── votes.py                 # 투표 시스템
├── schemas/
│   ├── project.py               # Project Pydantic 스키마
│   ├── agent.py                 # Agent Pydantic 스키마
│   ├── discussion.py            # Discussion Pydantic 스키마
│   └── vote.py                  # Vote Pydantic 스키마
└── tests/
    └── test_routes.py            # 라우트 테스트
```

### 수정할 파일

```
backend/
└── main.py                      # 새 라우트 등록
```

---

## Task 1: Pydantic 스키마 생성

**Files:**
- Create: `backend/schemas/__init__.py`
- Create: `backend/schemas/project.py`
- Create: `backend/schemas/agent.py`
- Create: `backend/schemas/discussion.py`
- Create: `backend/schemas/vote.py`

- [ ] **Step 1: schemas 디렉토리 생성 및 __init__.py**

```bash
mkdir -p /Volumes/Dock/2604/my-ai-company/backend/schemas
```

`backend/schemas/__init__.py` 생성:

```python
from schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from schemas.agent import AgentResponse, AgentInviteRequest
from schemas.discussion import DiscussionCreate, DiscussionResponse, DiscussionMessageCreate
from schemas.vote import VoteCreate, VoteResponse

__all__ = [
    "ProjectCreate",
    "ProjectResponse",
    "ProjectUpdate",
    "AgentResponse",
    "AgentInviteRequest",
    "DiscussionCreate",
    "DiscussionResponse",
    "DiscussionMessageCreate",
    "VoteCreate",
    "VoteResponse",
]
```

- [ ] **Step 2: Project 스키마**

`backend/schemas/project.py` 생성:

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 3: Agent 스키마**

`backend/schemas/agent.py` 생성:

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class AgentBase(BaseModel):
    name: str
    role: str
    system_prompt: str
    is_lead: bool = False
    display_name: Optional[str] = None
    emoji: Optional[str] = None
    badge_text: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class AgentResponse(AgentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    status: str
    created_at: datetime
    updated_at: datetime


class AgentInviteRequest(BaseModel):
    project_id: str
    agent_id: str
    is_lead: bool = False
```

- [ ] **Step 4: Discussion 스키마**

`backend/schemas/discussion.py` 생성:

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class DiscussionBase(BaseModel):
    project_id: str
    topic: str


class DiscussionCreate(DiscussionBase):
    pass


class DiscussionResponse(DiscussionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None


class DiscussionMessageBase(BaseModel):
    discussion_id: str
    agent_id: Optional[str] = None
    content: str


class DiscussionMessageCreate(DiscussionMessageBase):
    pass


class DiscussionMessageResponse(DiscussionMessageBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    created_at: datetime
```

- [ ] **Step 5: Vote 스키마**

`backend/schemas/vote.py` 생성:

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class VoteBase(BaseModel):
    discussion_id: str
    agent_id: str
    choice: str
    reasoning: Optional[str] = None


class VoteCreate(VoteBase):
    pass


class VoteResponse(VoteBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    created_at: datetime
```

- [ ] **Step 6: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/schemas/ && git commit -m "feat(schemas): add Pydantic schemas for Project, Agent, Discussion, Vote"
```

---

## Task 2: Projects 라우트 생성

**Files:**
- Create: `backend/routes/projects.py`
- Create: `backend/tests/test_routes.py`

- [ ] **Step 1: Projects 라우트 테스트 작성**

`backend/tests/test_routes.py` 생성:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from main import app
from database import get_db, Base, engine
from models.project import Project


@pytest.fixture
def client():
    """Create a test client."""
    Base.metadata.create_all(bind=engine)
    
    def override_get_db():
        try:
            db = SessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    Base.metadata.drop_all(bind=engine)


def test_create_project(client):
    """POST /api/projects - 프로젝트 생성 테스트"""
    response = client.post(
        "/api/projects",
        json={"name": "테스트 프로젝트", "description": "테스트용"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "테스트 프로젝트"
    assert data["description"] == "테스트용"
    assert "id" in data


def test_list_projects(client):
    """GET /api/projects - 프로젝트 목록 조회 테스트"""
    # 프로젝트 2개 생성
    client.post("/api/projects", json={"name": "프로젝트 1"})
    client.post("/api/projects", json={"name": "프로젝트 2"})
    
    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_project(client):
    """GET /api/projects/{id} - 특정 프로젝트 조회 테스트"""
    create_response = client.post(
        "/api/projects",
        json={"name": "조회 테스트"}
    )
    project_id = create_response.json()["id"]
    
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "조회 테스트"
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python3 -m pytest tests/test_routes.py::test_create_project -v
```

Expected: FAIL - `404 Not Found`

- [ ] **Step 3: Projects 라우트 구현**

`backend/routes/projects.py` 생성:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.project import Project
from schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """새 프로젝트 생성"""
    db_project = Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.get("/", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """프로젝트 목록 조회"""
    projects = db.query(Project).all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """특정 프로젝트 조회"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str, 
    project_update: ProjectUpdate, 
    db: Session = Depends(get_db)
):
    """프로젝트 수정"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """프로젝트 삭제"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}
```

- [ ] **Step 4: main.py에 라우트 등록**

`backend/main.py` 수정 (라우트 import 및 등록):

```python
# 라우트 import (기존 import 섹션에 추가)
from routes.projects import router as projects_router

# app.include_router() 호출 (기존 라이프사이클 후에 추가)
app.include_router(projects_router)
```

- [ ] **Step 5: 테스트 실행 (성공 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python3 -m pytest tests/test_routes.py -v
```

Expected: PASS

- [ ] **Step 6: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/routes/projects.py backend/tests/test_routes.py backend/main.py && git commit -m "feat(routes): add projects CRUD routes"
```

---

## Task 3: Agents 라우트 생성

**Files:**
- Create: `backend/routes/agents.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Agents 라우트 테스트 추가**

`backend/tests/test_routes.py`에 추가:

```python
from models.agent import Agent


def test_list_agents(client):
    """GET /api/agents - 에이전트 목록 조회 테스트"""
    response = client.get("/api/agents")
    assert response.status_code == 200


def test_invite_agent(client):
    """POST /api/agents/invite - 에이전트 초대 테스트"""
    # 프로젝트와 에이전트 생성
    project_resp = client.post("/api/projects", json={"name": "테스트"})
    project_id = project_resp.json()["id"]
    
    # 에이전트 생성 (직접 DB에)
    from database import SessionLocal
    db = SessionLocal()
    agent = Agent(
        name="developer",
        role="developer",
        system_prompt="당신은 개발자입니다."
    )
    db.add(agent)
    db.commit()
    agent_id = agent.id
    db.close()
    
    # 초대 요청
    response = client.post(
        "/api/agents/invite",
        json={"project_id": project_id, "agent_id": agent_id, "is_lead": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == agent_id
    assert data["project_id"] == project_id
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python3 -m pytest tests/test_routes.py::test_list_agents -v
```

Expected: FAIL - `404 Not Found`

- [ ] **Step 3: Agents 라우트 구현**

`backend/routes/agents.py` 생성:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.agent import Agent
from models.project_agent import ProjectAgent
from schemas.agent import AgentResponse, AgentInviteRequest

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    """에이전트 목록 조회"""
    agents = db.query(Agent).all()
    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """특정 에이전트 조회"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/invite")
def invite_agent(invite: AgentInviteRequest, db: Session = Depends(get_db)):
    """에이전트를 프로젝트에 초대"""
    # 에이전트 존재 확인
    agent = db.query(Agent).filter(Agent.id == invite.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 중복 바인딩 확인
    existing = db.query(ProjectAgent).filter(
        ProjectAgent.project_id == invite.project_id,
        ProjectAgent.agent_id == invite.agent_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Agent already invited to this project")
    
    # 바인딩 생성
    binding = ProjectAgent(
        project_id=invite.project_id,
        agent_id=invite.agent_id,
        is_lead=invite.is_lead
    )
    db.add(binding)
    db.commit()
    db.refresh(binding)
    
    return {
        "id": binding.id,
        "project_id": binding.project_id,
        "agent_id": binding.agent_id,
        "is_lead": binding.is_lead,
        "message": f"Agent {agent.name} invited to project"
    }


@router.delete("/{agent_id}/projects/{project_id}")
def remove_agent_from_project(
    agent_id: str, 
    project_id: str, 
    db: Session = Depends(get_db)
):
    """프로젝트에서 에이전트 제거"""
    binding = db.query(ProjectAgent).filter(
        ProjectAgent.agent_id == agent_id,
        ProjectAgent.project_id == project_id
    ).first()
    
    if not binding:
        raise HTTPException(status_code=404, detail="Binding not found")
    
    db.delete(binding)
    db.commit()
    
    return {"message": "Agent removed from project"}
```

- [ ] **Step 4: main.py에 라우트 등록**

`backend/main.py` 수정:

```python
from routes.agents import router as agents_router

app.include_router(agents_router)
```

- [ ] **Step 5: 테스트 실행 (성공 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python3 -m pytest tests/test_routes.py -v
```

Expected: PASS

- [ ] **Step 6: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/routes/agents.py backend/tests/test_routes.py backend/main.py && git commit -m "feat(routes): add agents management and invite routes"
```

---

## Task 4: Discussions 라우트 생성

**Files:**
- Create: `backend/routes/discussions.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Discussions 라우트 테스트 추가**

`backend/tests/test_routes.py`에 추가:

```python
from models.discussion import Discussion


def test_create_discussion(client):
    """POST /api/discussions - 토론 생성 테스트"""
    # 프로젝트 생성
    project_resp = client.post("/api/projects", json={"name": "토론 테스트"})
    project_id = project_resp.json()["id"]
    
    # 토론 생성
    response = client.post(
        "/api/discussions",
        json={"project_id": project_id, "topic": "UI 프레임워크 선정"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "UI 프레임워크 선정"
    assert data["status"] == "active"


def test_list_discussions(client):
    """GET /api/discussions/{project_id} - 토론 목록 조회 테스트"""
    # 프로젝트 생성
    project_resp = client.post("/api/projects", json={"name": "목록 테스트"})
    project_id = project_resp.json()["id"]
    
    # 토론 2개 생성
    client.post("/api/discussions", json={"project_id": project_id, "topic": "토론 1"})
    client.post("/api/discussions", json={"project_id": project_id, "topic": "토론 2"})
    
    response = client.get(f"/api/discussions/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python3 -m pytest tests/test_routes.py::test_create_discussion -v
```

Expected: FAIL - `404 Not Found`

- [ ] **Step 3: Discussions 라우트 구현**

`backend/routes/discussions.py` 생성:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from database import get_db
from models.discussion import Discussion, DiscussionMessage
from models.project import Project
from schemas.discussion import (
    DiscussionCreate, 
    DiscussionResponse, 
    DiscussionMessageCreate,
    DiscussionMessageResponse
)

router = APIRouter(prefix="/api/discussions", tags=["discussions"])


@router.post("/", response_model=DiscussionResponse)
def create_discussion(discussion: DiscussionCreate, db: Session = Depends(get_db)):
    """새 토론 생성"""
    # 프로젝트 존재 확인
    project = db.query(Project).filter(Project.id == discussion.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db_discussion = Discussion(**discussion.model_dump())
    db.add(db_discussion)
    db.commit()
    db.refresh(db_discussion)
    return db_discussion


@router.get("/{project_id}", response_model=List[DiscussionResponse])
def list_discussions(project_id: str, db: Session = Depends(get_db)):
    """프로젝트의 토론 목록 조회"""
    discussions = db.query(Discussion).filter(
        Discussion.project_id == project_id
    ).all()
    return discussions


@router.get("/detail/{discussion_id}", response_model=DiscussionResponse)
def get_discussion(discussion_id: str, db: Session = Depends(get_db)):
    """특정 토론 조회"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    return discussion


@router.post("/{discussion_id}/close")
def close_discussion(discussion_id: str, db: Session = Depends(get_db)):
    """토론 종료"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    
    discussion.status = "closed"
    discussion.closed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Discussion closed", "discussion_id": discussion_id}


@router.post("/{discussion_id}/messages", response_model=DiscussionMessageResponse)
def send_discussion_message(
    discussion_id: str,
    message: DiscussionMessageCreate,
    db: Session = Depends(get_db)
):
    """토론에 메시지 전송"""
    # 토론 존재 및 활성 상태 확인
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    if discussion.status != "active":
        raise HTTPException(status_code=400, detail="Discussion is closed")
    
    db_message = DiscussionMessage(
        discussion_id=discussion_id,
        agent_id=message.agent_id,
        content=message.content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    return db_message


@router.get("/{discussion_id}/messages", response_model=List[DiscussionMessageResponse])
def get_discussion_messages(discussion_id: str, db: Session = Depends(get_db)):
    """토론의 메시지 목록 조회"""
    messages = db.query(DiscussionMessage).filter(
        DiscussionMessage.discussion_id == discussion_id
    ).order_by(DiscussionMessage.created_at).all()
    return messages
```

- [ ] **Step 4: main.py에 라우트 등록**

`backend/main.py` 수정:

```python
from routes.discussions import router as discussions_router

app.include_router(discussions_router)
```

- [ ] **Step 5: 테스트 실행 (성공 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python3 -m pytest tests/test_routes.py -v
```

Expected: PASS

- [ ] **Step 6: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/routes/discussions.py backend/tests/test_routes.py backend/main.py && git commit -m "feat(routes): add discussions routes with message support"
```

---

## Task 5: Votes 라우트 생성

**Files:**
- Create: `backend/routes/votes.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Votes 라우트 테스트 추가**

`backend/tests/test_routes.py`에 추가:

```python
from models.agent import Agent
from models.discussion import Discussion


def test_create_vote(client):
    """POST /api/votes - 투표 생성 테스트"""
    # 프로젝트, 에이전트, 토론 생성
    from database import SessionLocal
    db = SessionLocal()
    
    project = Project(name="투표 테스트")
    agent = Agent(name="manager", role="manager", system_prompt="테스트")
    db.add_all([project, agent])
    db.commit()
    
    discussion = Discussion(project_id=project.id, topic="투표 대상")
    db.add(discussion)
    db.commit()
    
    project_id = project.id
    agent_id = agent.id
    discussion_id = discussion.id
    db.close()
    
    # 투표 생성
    response = client.post(
        "/api/votes",
        json={
            "discussion_id": discussion_id,
            "agent_id": agent_id,
            "choice": "React",
            "reasoning": "성숙한 생태계"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["choice"] == "React"


def test_get_votes_by_discussion(client):
    """GET /api/votes/{discussion_id} - 토론별 투표 조회 테스트"""
    # 프로젝트, 에이전트, 토론 생성
    from database import SessionLocal
    db = SessionLocal()
    
    project = Project(name="조회 테스트")
    agent1 = Agent(name="agent1", role="developer", system_prompt="테스트")
    agent2 = Agent(name="agent2", role="designer", system_prompt="테스트")
    db.add_all([project, agent1, agent2])
    db.commit()
    
    discussion = Discussion(project_id=project.id, topic="조회 대상")
    db.add(discussion)
    db.commit()
    
    discussion_id = discussion.id
    agent1_id = agent1.id
    agent2_id = agent2.id
    db.close()
    
    # 투표 2개 생성
    client.post("/api/votes", json={
        "discussion_id": discussion_id,
        "agent_id": agent1_id,
        "choice": "React"
    })
    client.post("/api/votes", json={
        "discussion_id": discussion_id,
        "agent_id": agent2_id,
        "choice": "Vue"
    })
    
    # 조회
    response = client.get(f"/api/votes/{discussion_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python3 -m pytest tests/test_routes.py::test_create_vote -v
```

Expected: FAIL - `404 Not Found`

- [ ] **Step 3: Votes 라우트 구현**

`backend/routes/votes.py` 생성:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.vote import Vote
from models.discussion import Discussion
from models.agent import Agent
from schemas.vote import VoteCreate, VoteResponse

router = APIRouter(prefix="/api/votes", tags=["votes"])


@router.post("/", response_model=VoteResponse)
def create_vote(vote: VoteCreate, db: Session = Depends(get_db)):
    """새 투표 생성"""
    # 토론 존재 및 활성 상태 확인
    discussion = db.query(Discussion).filter(Discussion.id == vote.discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    if discussion.status != "active":
        raise HTTPException(status_code=400, detail="Discussion is closed")
    
    # 에이전트 존재 확인
    agent = db.query(Agent).filter(Agent.id == vote.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 중복 투표 확인
    existing_vote = db.query(Vote).filter(
        Vote.discussion_id == vote.discussion_id,
        Vote.agent_id == vote.agent_id
    ).first()
    if existing_vote:
        raise HTTPException(status_code=400, detail="Agent has already voted")
    
    db_vote = Vote(**vote.model_dump())
    db.add(db_vote)
    db.commit()
    db.refresh(db_vote)
    
    return db_vote


@router.get("/{discussion_id}", response_model=List[VoteResponse])
def get_votes_by_discussion(discussion_id: str, db: Session = Depends(get_db)):
    """토론별 투표 결과 조회"""
    votes = db.query(Vote).filter(Vote.discussion_id == discussion_id).all()
    return votes


@router.get("/{discussion_id}/results")
def get_vote_results(discussion_id: str, db: Session = Depends(get_db)):
    """투표 결과 집계"""
    votes = db.query(Vote).filter(Vote.discussion_id == discussion_id).all()
    
    if not votes:
        return {"discussion_id": discussion_id, "total_votes": 0, "results": {}}
    
    # 선택별 집계
    results = {}
    for vote in votes:
        if vote.choice not in results:
            results[vote.choice] = {"count": 0, "reasoning": []}
        results[vote.choice]["count"] += 1
        if vote.reasoning:
            results[vote.choice]["reasoning"].append(vote.reasoning)
    
    return {
        "discussion_id": discussion_id,
        "total_votes": len(votes),
        "results": results
    }
```

- [ ] **Step 4: main.py에 라우트 등록**

`backend/main.py` 수정:

```python
from routes.votes import router as votes_router

app.include_router(votes_router)
```

- [ ] **Step 5: 테스트 실행 (성공 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python3 -m pytest tests/test_routes.py -v
```

Expected: PASS

- [ ] **Step 6: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/routes/votes.py backend/tests/test_routes.py backend/main.py && git commit -m "feat(routes): add votes routes with result aggregation"
```

---

## Task 6: 전체 통합 테스트

- [ ] **Step 1: 전체 라우트 테스트 실행**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python3 -m pytest tests/test_routes.py -v --tb=short
```

Expected: 모든 테스트 PASS

- [ ] **Step 2: API 문서 확인**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python3 -c "from main import app; print('Routes:', [r.path for r in app.routes])"
```

Expected: 새 라우트들이 등록되어 있어야 함

- [ ] **Step 3: 최종 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add -A && git commit -m "feat(routes): complete Phase 1C - all FastAPI routes implemented"
```

---

## Self-Review 체크리스트

- [ ] **Spec coverage:** checklist.md의 모든 라우트가 구현되었는가?
  - projects.py ✅
  - agents.py ✅
  - discussions.py ✅
  - votes.py ✅
  - main.py 등록 ✅

- [ ] **Placeholder scan:** TBD, TODO 등의 플레이스홀더가 없는가?
  - 스캔 완료 ✅

- [ ] **Error handling:** 적절한 HTTP 예외 처리가 되어 있는가?
  - 404 Not Found ✅
  - 400 Bad Request ✅

- [ ] **Test coverage:** 주요 기능에 대한 테스트가 작성되었는가?
  - CRUD 테스트 ✅
  - 에러 케이스 테스트 ✅

---

**작업 담당자: @Sisyphus 👑**
