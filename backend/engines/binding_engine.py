"""에이전트 바인딩 엔진 - 프로젝트-에이전트 관계 관리"""

from sqlalchemy.orm import Session
from models.project_agent import ProjectAgent
from models.agent import Agent
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BindingEngine:
    """에이전트 바인딩 관리 엔진"""
    
    @staticmethod
    def bind_agent_to_project(
        db: Session,
        project_id: str,
        agent_id: str,
        is_lead: bool = False
    ) -> ProjectAgent:
        """에이전트를 프로젝트에 바인딩
        
        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            agent_id: 에이전트 ID
            is_lead: 선임 에이전트 여부
        
        Returns:
            생성된 바인딩
        """
        # 기존 바인딩 확인
        existing = db.query(ProjectAgent).filter(
            ProjectAgent.project_id == project_id,
            ProjectAgent.agent_id == agent_id
        ).first()
        
        if existing:
            logger.warning(f"Agent {agent_id} already bound to project {project_id}")
            return existing
        
        # 새 바인딩 생성
        binding = ProjectAgent(
            project_id=project_id,
            agent_id=agent_id,
            is_lead=is_lead
        )
        db.add(binding)
        db.commit()
        db.refresh(binding)
        
        logger.info(f"Bound agent {agent_id} to project {project_id} (lead: {is_lead})")
        return binding
    
    @staticmethod
    def unbind_agent_from_project(
        db: Session,
        project_id: str,
        agent_id: str
    ) -> bool:
        """프로젝트에서 에이전트 바인딩 해제
        
        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            agent_id: 에이전트 ID
        
        Returns:
            삭제 성공 여부
        """
        binding = db.query(ProjectAgent).filter(
            ProjectAgent.project_id == project_id,
            ProjectAgent.agent_id == agent_id
        ).first()
        
        if not binding:
            logger.warning(f"No binding found for agent {agent_id} in project {project_id}")
            return False
        
        db.delete(binding)
        db.commit()
        
        logger.info(f"Unbound agent {agent_id} from project {project_id}")
        return True
    
    @staticmethod
    def get_project_agents(db: Session, project_id: str) -> List[ProjectAgent]:
        """프로젝트에 바인딩된 모든 에이전트 조회
        
        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
        
        Returns:
            바인딩 목록
        """
        bindings = db.query(ProjectAgent).filter(
            ProjectAgent.project_id == project_id
        ).all()
        
        return bindings
    
    @staticmethod
    def get_agent_projects(db: Session, agent_id: str) -> List[ProjectAgent]:
        """에이전트가 참여 중인 모든 프로젝트 조회
        
        Args:
            db: 데이터베이스 세션
            agent_id: 에이전트 ID
        
        Returns:
            바인딩 목록
        """
        bindings = db.query(ProjectAgent).filter(
            ProjectAgent.agent_id == agent_id
        ).all()
        
        return bindings
    
    @staticmethod
    def get_project_lead_agents(db: Session, project_id: str) -> List[ProjectAgent]:
        """프로젝트의 선임 에이전트들 조회
        
        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
        
        Returns:
            선임 에이전트 바인딩 목록
        """
        bindings = db.query(ProjectAgent).filter(
            ProjectAgent.project_id == project_id,
            ProjectAgent.is_lead == True
        ).all()
        
        return bindings
    
    @staticmethod
    def is_agent_bound_to_project(
        db: Session,
        project_id: str,
        agent_id: str
    ) -> bool:
        """에이전트가 프로젝트에 바인딩되어 있는지 확인
        
        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            agent_id: 에이전트 ID
        
        Returns:
            바인딩 여부
        """
        binding = db.query(ProjectAgent).filter(
            ProjectAgent.project_id == project_id,
            ProjectAgent.agent_id == agent_id
        ).first()
        
        return binding is not None
    
    @staticmethod
    def get_binding_with_agent_info(db: Session, project_id: str) -> List[Tuple[ProjectAgent, Agent]]:
        """프로젝트의 바인딩과 에이전트 정보 함께 조회
        
        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
        
        Returns:
            (바인딩, 에이전트) 튜플 목록
        """
        from sqlalchemy.orm import joinedload
        
        bindings = db.query(ProjectAgent).options(
            joinedload(ProjectAgent.agent)
        ).filter(
            ProjectAgent.project_id == project_id
        ).all()
        
        return [(binding, binding.agent) for binding in bindings]
