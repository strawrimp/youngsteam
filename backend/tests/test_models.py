import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from models.project import Project
from models.agent import Agent
from models.project_agent import ProjectAgent
from models.message import Message
from models.conversation import Conversation
from models.discussion import Discussion, DiscussionMessage


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_project_creation(db_session):
    """Project 모델이 정상적으로 생성되는지 테스트"""
    project = Project(name="테스트 프로젝트", description="테스트용 프로젝트입니다")
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


def test_agent_is_lead_field(db_session):
    """Agent 모델에 is_lead 필드가 존재하는지 테스트"""
    agent = Agent(
        name="manager",
        role="manager",
        system_prompt="당신은 매니저입니다.",
        is_lead=True,
    )
    db_session.add(agent)
    db_session.commit()

    assert agent.is_lead is True


def test_agent_default_is_lead_false(db_session):
    """is_lead 기본값이 False인지 테스트"""
    agent = Agent(
        name="developer", role="developer", system_prompt="당신은 개발자입니다."
    )
    db_session.add(agent)
    db_session.commit()

    assert agent.is_lead is False


def test_project_agent_binding(db_session):
    """프로젝트-에이전트 바인딩 생성 테스트"""
    # 에이전트 생성
    agent = Agent(
        name="manager",
        role="manager",
        system_prompt="당신은 매니저입니다.",
        is_lead=True,
    )
    db_session.add(agent)

    # 프로젝트 생성
    project = Project(name="테스트 프로젝트")
    db_session.add(project)
    db_session.commit()

    # 바인딩 생성
    binding = ProjectAgent(project_id=project.id, agent_id=agent.id, is_lead=True)
    db_session.add(binding)
    db_session.commit()

    assert binding.id is not None
    assert binding.is_lead is True
    assert binding.project_id == project.id
    assert binding.agent_id == agent.id


def test_unique_project_agent_constraint(db_session):
    """동일한 프로젝트에 동일한 에이전트 중복 바인딩 방지 테스트"""
    agent = Agent(
        name="developer", role="developer", system_prompt="당신은 개발자입니다."
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
        project_id=project.id,
    )
    db_session.add(message)
    db_session.commit()

    assert message.project_id == project.id


def test_discussion_creation(db_session):
    """Discussion 모델이 정상적으로 생성되는지 테스트"""
    project = Project(name="토론 테스트")
    db_session.add(project)
    db_session.commit()

    discussion = Discussion(project_id=project.id, topic="UI 프레임워크 선정")
    db_session.add(discussion)
    db_session.commit()

    assert discussion.id is not None
    assert discussion.status == "active"
    assert discussion.topic == "UI 프레임워크 선정"


def test_discussion_message(db_session):
    """DiscussionMessage가 정상적으로 생성되는지 테스트"""
    project = Project(name="토론 메시지 테스트")
    agent = Agent(
        name="developer", role="developer", system_prompt="당신은 개발자입니다."
    )
    db_session.add_all([project, agent])
    db_session.commit()

    discussion = Discussion(project_id=project.id, topic="테스트 토론")
    db_session.add(discussion)
    db_session.commit()

    message = DiscussionMessage(
        discussion_id=discussion.id, agent_id=agent.id, content="React를 제안합니다."
    )
    db_session.add(message)
    db_session.commit()

    assert message.id is not None
    assert message.discussion_id == discussion.id
