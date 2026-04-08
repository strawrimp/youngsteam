# Phase 1A: Backend DB Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OpenClaw 스타일 다중 에이전트 시스템의 백엔드 DB 스키마 구축 (Project, ProjectAgent, Discussion 모델 추가)

**Architecture:** 
- SQLite + SQLAlchemy ORM (UUID 기본키 유지, 기존 코드와 일관성)
- 기존 Agent 모델에 is_lead 필드 추가
- 기존 Message 모델에 project_id 필드 추가
- Vote 모델을 decision_id → discussion_id로 변경

**Tech Stack:** 
- Backend: FastAPI, SQLAlchemy, SQLite, Pydantic, pytest

---

## 📁 파일 구조

### 새로 생성할 파일

```
backend/
├── models/
│   ├── project.py              # Project 모델
│   └── project_agent.py        # 프로젝트-에이전트 바인딩
│   └── discussion.py            # Discussion + DiscussionMessage
└── tests/
    └── test_models.py            # 모델 테스트
```

### 수정할 파일

```
backend/
├── models/
│   ├── agent.py                 # is_lead 필드 추가
│   ├── message.py               # project_id 필드 추가
│   ├── vote.py                  # decision_id → discussion_id
│   └── __init__.py              # 새 모델 export
```

---

## Task 1: Project 모델 생성

**Files:**
- Create: `backend/models/project.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Project 모델 테스트 작성**

`backend/tests/test_models.py` 생성:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from models.project import Project

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_project_creation(db_session):
    """Project 모델이 정상적으로 생성되는지 테스트"""
    project = Project(
        name="테스트 프로젝트",
        description="테스트용 프로젝트입니다"
    )
    db_session.add(project)
    db_session.commit()
    
    assert project.id is not None
    assert project.name == "테스트 프로젝트"
    assert project.created_at is not None

def test_project_required_fields(db_session):
    """필수 필드 누락 시 예외 발생 테스트"""
    project = Project(description="이름 없는 프로젝트")
    db_session.add(project)
    
    with pytest.raises(Exception):
        db_session.commit()
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_project_creation -v
```

Expected: FAIL - `ModuleNotFoundError: No module named 'models.project'`

- [ ] **Step 3: Project 모델 구현**

`backend/models/project.py` 생성:

```python
from sqlalchemy import Column, String, DateTime, Text, func
import uuid
from database import Base


class Project(Base):
    """프로젝트 엔티티 - 에이전트들이 협업하는 작업 공간"""

    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name})>"
```

- [ ] **Step 4: 테스트 실행 (성공 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_project_creation -v
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/models/project.py backend/tests/test_models.py && git commit -m "feat(models): add Project model with tests"
```

---

## Task 2: Agent 모델에 is_lead 필드 추가

**Files:**
- Modify: `backend/models/agent.py`
- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: is_lead 필드 테스트 작성**

`backend/tests/test_models.py`에 추가:

```python
from models.agent import Agent

def test_agent_is_lead_field(db_session):
    """Agent 모델에 is_lead 필드가 존재하는지 테스트"""
    agent = Agent(
        name="manager",
        role="manager",
        system_prompt="당신은 매니저입니다.",
        is_lead=True
    )
    db_session.add(agent)
    db_session.commit()
    
    assert agent.is_lead is True

def test_agent_default_is_lead_false(db_session):
    """is_lead 기본값이 False인지 테스트"""
    agent = Agent(
        name="developer",
        role="developer",
        system_prompt="당신은 개발자입니다."
    )
    db_session.add(agent)
    db_session.commit()
    
    assert agent.is_lead is False
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_agent_is_lead_field -v
```

Expected: FAIL - `TypeError: 'is_lead' is an invalid keyword argument`

- [ ] **Step 3: Agent 모델에 is_lead 필드 추가**

`backend/models/agent.py` 수정 (Line 17 이후에 추가):

```python
from sqlalchemy import Column, String, DateTime, Boolean, func
import uuid
from database import Base


class Agent(Base):
    """Agent entity representing a role in the company."""

    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)  # manager, developer, designer, researcher
    status = Column(String(20), default="active")
    system_prompt = Column(String, nullable=False)
    is_lead = Column(Boolean, default=False)  # 선임에이전트 여부 (초대 제안 권한)

    # New display columns
    display_name = Column(String(50), nullable=True)  # 비서실장, 개발부장, etc.
    emoji = Column(String(10), nullable=True)  # 👔, 💻, 🎨, 📚
    badge_text = Column(String(20), nullable=True)  # 책임, 기술, 디자인, 연구
    icon = Column(String(50), nullable=True)  # Material Symbols name
    color = Column(String(20), nullable=True)  # Hex color code

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Agent(id={self.id}, name={self.name}, role={self.role}, is_lead={self.is_lead})>"
```

- [ ] **Step 4: 테스트 실행 (성공 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_agent_is_lead_field tests/test_models.py::test_agent_default_is_lead_false -v
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/models/agent.py backend/tests/test_models.py && git commit -m "feat(models): add is_lead field to Agent model"
```

---

## Task 3: ProjectAgent 바인딩 모델 생성

**Files:**
- Create: `backend/models/project_agent.py`
- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: ProjectAgent 바인딩 테스트 작성**

`backend/tests/test_models.py`에 추가:

```python
from models.project_agent import ProjectAgent

def test_project_agent_binding(db_session):
    """프로젝트-에이전트 바인딩 생성 테스트"""
    # 에이전트 생성
    agent = Agent(
        name="manager",
        role="manager",
        system_prompt="당신은 매니저입니다.",
        is_lead=True
    )
    db_session.add(agent)
    
    # 프로젝트 생성
    project = Project(name="테스트 프로젝트")
    db_session.add(project)
    db_session.commit()
    
    # 바인딩 생성
    binding = ProjectAgent(
        project_id=project.id,
        agent_id=agent.id,
        is_lead=True
    )
    db_session.add(binding)
    db_session.commit()
    
    assert binding.id is not None
    assert binding.is_lead is True
    assert binding.project_id == project.id
    assert binding.agent_id == agent.id

def test_unique_project_agent_constraint(db_session):
    """동일한 프로젝트에 동일한 에이전트 중복 바인딩 방지 테스트"""
    agent = Agent(
        name="developer",
        role="developer",
        system_prompt="당신은 개발자입니다."
    )
    project = Project(name="중복 테스트")
    db_session.add_all([agent, project])
    db_session.commit()
    
    binding1 = ProjectAgent(project_id=project.id, agent_id=agent.id)
    db_session.add(binding1)
    db_session.commit()
    
    # 동일한 바인딩 재시도
    binding2 = ProjectAgent(project_id=project.id, agent_id=agent.id)
    db_session.add(binding2)
    
    with pytest.raises(Exception):  # UNIQUE 제약 위반
        db_session.commit()
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_project_agent_binding -v
```

Expected: FAIL - `ModuleNotFoundError: No module named 'models.project_agent'`

- [ ] **Step 3: ProjectAgent 모델 구현**

`backend/models/project_agent.py` 생성:

```python
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, func, UniqueConstraint
import uuid
from database import Base


class ProjectAgent(Base):
    """프로젝트-에이전트 바인딩 (중간 테이블)"""

    __tablename__ = "project_agents"
    __table_args__ = (
        UniqueConstraint("project_id", "agent_id", name="uq_project_agent"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    is_lead = Column(Boolean, default=False)  # 이 프로젝트에서 선임 역할 여부
    invited_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ProjectAgent(project_id={self.project_id}, agent_id={self.agent_id}, is_lead={self.is_lead})>"
```

- [ ] **Step 4: 테스트 실행 (성공 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_project_agent_binding tests/test_models.py::test_unique_project_agent_constraint -v
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/models/project_agent.py backend/tests/test_models.py && git commit -m "feat(models): add ProjectAgent binding model"
```

---

## Task 4: Message 모델에 project_id 추가

**Files:**
- Modify: `backend/models/message.py`
- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: Message project_id 테스트 작성**

`backend/tests/test_models.py`에 추가:

```python
from models.message import Message
from models.conversation import Conversation

def test_message_with_project_id(db_session):
    """Message에 project_id 필드가 존재하는지 테스트"""
    # 프로젝트와 대화 생성
    project = Project(name="메시지 테스트")
    conversation = Conversation(title="테스트 대화")
    db_session.add_all([project, conversation])
    db_session.commit()
    
    # 메시지 생성 (project_id 포함)
    message = Message(
        conversation_id=conversation.id,
        sender_type="user",
        content="안녕하세요",
        project_id=project.id
    )
    db_session.add(message)
    db_session.commit()
    
    assert message.project_id == project.id
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_message_with_project_id -v
```

Expected: FAIL - `TypeError: 'project_id' is an invalid keyword argument`

- [ ] **Step 3: Message 모델에 project_id 추가**

`backend/models/message.py` 수정:

```python
from sqlalchemy import Column, String, DateTime, ForeignKey, func
import uuid
from database import Base


class Message(Base):
    """Message in a conversation."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)  # NEW
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    sender_type = Column(String(20), nullable=False)  # "user" or "agent"
    content = Column(String, nullable=False)
    message_type = Column(String(20), default="text")  # text, image, decision, invite
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, sender_type={self.sender_type})>"
```

- [ ] **Step 4: 테스트 실행 (성공 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_message_with_project_id -v
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/models/message.py backend/tests/test_models.py && git commit -m "feat(models): add project_id to Message model"
```

---

## Task 5: Discussion 모델 생성

**Files:**
- Create: `backend/models/discussion.py`
- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: Discussion 모델 테스트 작성**

`backend/tests/test_models.py`에 추가:

```python
from models.discussion import Discussion, DiscussionMessage

def test_discussion_creation(db_session):
    """Discussion 모델이 정상적으로 생성되는지 테스트"""
    project = Project(name="토론 테스트")
    db_session.add(project)
    db_session.commit()
    
    discussion = Discussion(
        project_id=project.id,
        topic="UI 프레임워크 선정"
    )
    db_session.add(discussion)
    db_session.commit()
    
    assert discussion.id is not None
    assert discussion.status == "active"
    assert discussion.topic == "UI 프레임워크 선정"

def test_discussion_message(db_session):
    """DiscussionMessage가 정상적으로 생성되는지 테스트"""
    project = Project(name="토론 메시지 테스트")
    agent = Agent(
        name="developer",
        role="developer",
        system_prompt="당신은 개발자입니다."
    )
    db_session.add_all([project, agent])
    db_session.commit()
    
    discussion = Discussion(project_id=project.id, topic="테스트 토론")
    db_session.add(discussion)
    db_session.commit()
    
    message = DiscussionMessage(
        discussion_id=discussion.id,
        agent_id=agent.id,
        content="React를 제안합니다."
    )
    db_session.add(message)
    db_session.commit()
    
    assert message.id is not None
    assert message.discussion_id == discussion.id
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_discussion_creation -v
```

Expected: FAIL - `ModuleNotFoundError: No module named 'models.discussion'`

- [ ] **Step 3: Discussion 모델 구현**

`backend/models/discussion.py` 생성:

```python
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, func
import uuid
from database import Base


class Discussion(Base):
    """에이전트 간 토론 세션"""

    __tablename__ = "discussions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    topic = Column(String(200), nullable=False)
    status = Column(String(20), default="active")  # active, closed
    created_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Discussion(id={self.id}, topic={self.topic}, status={self.status})>"


class DiscussionMessage(Base):
    """토론 내 메시지"""

    __tablename__ = "discussion_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    discussion_id = Column(String(36), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<DiscussionMessage(discussion_id={self.discussion_id}, agent_id={self.agent_id})>"
```

- [ ] **Step 4: 테스트 실행 (성공 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_discussion_creation tests/test_models.py::test_discussion_message -v
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/models/discussion.py backend/tests/test_models.py && git commit -m "feat(models): add Discussion and DiscussionMessage models"
```

---

## Task 6: Vote 모델 수정 (decision_id → discussion_id)

**Files:**
- Modify: `backend/models/vote.py`
- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: Vote 모델 수정 테스트 작성**

`backend/tests/test_models.py`에 추가:

```python
from models.vote import Vote

def test_vote_with_discussion(db_session):
    """Vote가 discussion_id를 참조하는지 테스트"""
    project = Project(name="투표 테스트")
    agent = Agent(
        name="manager",
        role="manager",
        system_prompt="당신은 매니저입니다.",
        is_lead=True
    )
    db_session.add_all([project, agent])
    db_session.commit()
    
    discussion = Discussion(project_id=project.id, topic="투표 대상")
    db_session.add(discussion)
    db_session.commit()
    
    vote = Vote(
        discussion_id=discussion.id,
        agent_id=agent.id,
        choice="React",
        reasoning="성숙한 생태계와 풍부한 라이브러리"
    )
    db_session.add(vote)
    db_session.commit()
    
    assert vote.id is not None
    assert vote.discussion_id == discussion.id
    assert vote.choice == "React"
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_vote_with_discussion -v
```

Expected: FAIL - `TypeError: 'discussion_id' is an invalid keyword argument`

- [ ] **Step 3: Vote 모델 수정**

`backend/models/vote.py` 수정:

```python
from sqlalchemy import Column, String, DateTime, ForeignKey, func, Text
import uuid
from database import Base


class Vote(Base):
    """Vote cast by an agent in a discussion."""

    __tablename__ = "votes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    discussion_id = Column(String(36), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    choice = Column(String, nullable=False)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Vote(id={self.id}, agent_id={self.agent_id}, choice={self.choice})>"
```

- [ ] **Step 4: 테스트 실행 (성공 확인)**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py::test_vote_with_discussion -v
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/models/vote.py backend/tests/test_models.py && git commit -m "refactor(models): change Vote to reference discussion_id instead of decision_id"
```

---

## Task 7: 모델 __init__.py 업데이트

**Files:**
- Modify: `backend/models/__init__.py`

- [ ] **Step 1: __init__.py 내보내기 추가**

`backend/models/__init__.py` 수정:

```python
from models.agent import Agent
from models.conversation import Conversation
from models.decision import Decision
from models.image import Image
from models.message import Message
from models.shared_memory import SharedMemory
from models.team_settings import TeamSettings
from models.vote import Vote

# 새로 추가
from models.project import Project
from models.project_agent import ProjectAgent
from models.discussion import Discussion, DiscussionMessage

__all__ = [
    "Agent",
    "Conversation",
    "Decision",
    "Image",
    "Message",
    "SharedMemory",
    "TeamSettings",
    "Vote",
    "Project",
    "ProjectAgent",
    "Discussion",
    "DiscussionMessage",
]
```

- [ ] **Step 2: 전체 모델 테스트 실행**

```bash
cd /Volumes/Dock/2604/my-ai-company/backend && python -m pytest tests/test_models.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 3: 커밋**

```bash
cd /Volumes/Dock/2604/my-ai-company && git add backend/models/__init__.py && git commit -m "chore(models): export new models in __init__.py"
```

---

## Self-Review 체크리스트

- [ ] **Spec coverage:** plan.md의 모든 모델이 구현되었는가?
  - Project ✅
  - ProjectAgent ✅
  - Agent.is_lead ✅
  - Message.project_id ✅
  - Discussion ✅
  - Vote.discussion_id ✅

- [ ] **Placeholder scan:** TBD, TODO 등의 플레이스홀더가 없는가?
  - 스캔 완료 ✅

- [ ] **Type consistency:** 모델 간의 외래키 참조가 일관성 있는가?
  - Project.id → ProjectAgent.project_id ✅
  - Agent.id → ProjectAgent.agent_id ✅
  - Project.id → Message.project_id ✅
  - Project.id → Discussion.project_id ✅
  - Discussion.id → DiscussionMessage.discussion_id ✅
  - Discussion.id → Vote.discussion_id ✅

---

**작업 담당자: @Sisyphus 👑**
