import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from models.project import Project
from models.agent import Agent


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
