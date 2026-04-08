"""에이전트 초대 엔진 - 자동 제안 및 멘션 처리

Phase 3A: 하이브리드 초대 시스템
- 선임에이전트가 키워드 감지 시 자동 제안
- @멘션 기반 수동 초대
"""

import re
import logging
from typing import List, Optional, Dict, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """에이전트 역할"""

    MANAGER = "manager"
    DEVELOPER = "developer"
    DESIGNER = "designer"
    RESEARCHER = "researcher"


@dataclass
class InviteSuggestion:
    """초대 제안 데이터"""

    suggested_agent_id: str
    suggested_agent_name: str
    suggested_agent_role: str
    reason: str
    triggered_by: str  # 'keyword' | 'mention'
    keywords_matched: List[str]
    confidence: float  # 0.0 ~ 1.0


class InviteEngine:
    """에이전트 초대 제안 엔진"""

    # 역할별 키워드 매핑 (한국어 + 영어)
    KEYWORD_MAPPING: Dict[str, Set[str]] = {
        AgentRole.DEVELOPER: {
            # 한국어
            "코드",
            "개발",
            "프로그래밍",
            "api",
            "백엔드",
            "프론트엔드",
            "데이터베이스",
            "db",
            "서버",
            "배포",
            "버그",
            "수정",
            "구현",
            "기능",
            "알고리즘",
            "최적화",
            "리팩토링",
            # 영어
            "code",
            "develop",
            "programming",
            "backend",
            "frontend",
            "database",
            "server",
            "deploy",
            "bug",
            "fix",
            "implement",
            "feature",
            "algorithm",
            "optimize",
            "refactor",
        },
        AgentRole.DESIGNER: {
            # 한국어
            "디자인",
            "ui",
            "ux",
            "인터페이스",
            "레이아웃",
            "스타일",
            "색상",
            "폰트",
            "애니메이션",
            "아이콘",
            "로고",
            "반응형",
            "모바일",
            "웹디자인",
            "피그마",
            # 영어
            "design",
            "interface",
            "layout",
            "style",
            "color",
            "font",
            "animation",
            "icon",
            "logo",
            "responsive",
            "mobile",
            "figma",
        },
        AgentRole.RESEARCHER: {
            # 한국어
            "조사",
            "연구",
            "분석",
            "리서치",
            "데이터",
            "통계",
            "시장",
            "트렌드",
            "경쟁사",
            "사용자",
            "인터뷰",
            "설문",
            "보고서",
            "문서",
            # 영어
            "research",
            "analysis",
            "data",
            "statistics",
            "market",
            "trend",
            "competitor",
            "user",
            "interview",
            "survey",
            "report",
            "document",
        },
    }

    # 선임에이전트만 제안 권한
    LEAD_AGENT_ROLES = {AgentRole.MANAGER}

    @classmethod
    def detect_keywords(
        cls, message: str, exclude_agents: Optional[Set[str]] = None
    ) -> List[InviteSuggestion]:
        """메시지에서 키워드 감지하여 초대 제안 생성

        Args:
            message: 분석할 메시지
            exclude_agents: 이미 초대된 에이전트 ID 집합

        Returns:
            초대 제안 목록
        """
        if exclude_agents is None:
            exclude_agents = set()

        suggestions = []
        message_lower = message.lower()

        for role, keywords in cls.KEYWORD_MAPPING.items():
            # 이미 참여 중인 에이전트는 제외
            if role in exclude_agents:
                continue

            # 키워드 매칭
            matched_keywords = []
            for keyword in keywords:
                if keyword in message_lower:
                    matched_keywords.append(keyword)

            if matched_keywords:
                # 신뢰도 계산 (매칭된 키워드 수 / 최소 키워드 수)
                confidence = min(1.0, len(matched_keywords) / 2.0)

                suggestions.append(
                    InviteSuggestion(
                        suggested_agent_id=role,  # 역할명을 ID로 사용
                        suggested_agent_name=cls._get_agent_display_name(role),
                        suggested_agent_role=role,
                        reason=cls._generate_reason(role, matched_keywords),
                        triggered_by="keyword",
                        keywords_matched=matched_keywords,
                        confidence=confidence,
                    )
                )

        # 신뢰도 기준 정렬
        suggestions.sort(key=lambda x: x.confidence, reverse=True)

        return suggestions

    @classmethod
    def parse_mentions(cls, message: str) -> List[str]:
        """메시지에서 @멘션 파싱

        Args:
            message: 분석할 메시지

        Returns:
            멘션된 에이전트 ID 목록 (예: ['developer', 'designer'])
        """
        # @agent_name 패턴 매칭
        pattern = r"@([a-zA-Z_]+)"
        matches = re.findall(pattern, message)

        # 유효한 에이전트 역할만 필터링
        valid_mentions = []
        for mention in matches:
            mention_lower = mention.lower()
            if mention_lower in [role.value for role in AgentRole]:
                valid_mentions.append(mention_lower)

        return valid_mentions

    @classmethod
    def create_mention_suggestions(
        cls, mentioned_agents: List[str], exclude_agents: Optional[Set[str]] = None
    ) -> List[InviteSuggestion]:
        """@멘션 기반 초대 제안 생성

        Args:
            mentioned_agents: 멘션된 에이전트 ID 목록
            exclude_agents: 이미 참여 중인 에이전트 집합

        Returns:
            초대 제안 목록
        """
        if exclude_agents is None:
            exclude_agents = set()

        suggestions = []

        for agent_id in mentioned_agents:
            if agent_id in exclude_agents:
                continue

            suggestions.append(
                InviteSuggestion(
                    suggested_agent_id=agent_id,
                    suggested_agent_name=cls._get_agent_display_name(agent_id),
                    suggested_agent_role=agent_id,
                    reason=f"@{agent_id} 멘션으로 호출됨",
                    triggered_by="mention",
                    keywords_matched=[f"@{agent_id}"],
                    confidence=1.0,  # 멘션은 100% 확실
                )
            )

        return suggestions

    @classmethod
    def can_suggest_invite(cls, agent_role: str) -> bool:
        """에이전트가 초대 제안 권한이 있는지 확인

        Args:
            agent_role: 에이전트 역할

        Returns:
            제안 권한 여부
        """
        return agent_role in [role.value for role in cls.LEAD_AGENT_ROLES]

    @classmethod
    def _get_agent_display_name(cls, role: str) -> str:
        """에이전트 표시명 반환"""
        display_names = {
            AgentRole.MANAGER: "Manager",
            AgentRole.DEVELOPER: "Developer",
            AgentRole.DESIGNER: "Designer",
            AgentRole.RESEARCHER: "Researcher",
        }
        return display_names.get(role, role.title())

    @classmethod
    def _generate_reason(cls, role: str, keywords: List[str]) -> str:
        """초대 제안 사유 생성"""
        keyword_str = ", ".join(keywords[:3])  # 최대 3개만 표시

        reasons = {
            AgentRole.DEVELOPER: f"개발 관련 키워드 감지: {keyword_str}",
            AgentRole.DESIGNER: f"디자인 관련 키워드 감지: {keyword_str}",
            AgentRole.RESEARCHER: f"리서치 관련 키워드 감지: {keyword_str}",
        }

        return reasons.get(role, f"관련 키워드 감지: {keyword_str}")

    @classmethod
    def analyze_message_for_invites(
        cls, message: str, project_agents: Set[str], sender_role: Optional[str] = None
    ) -> List[InviteSuggestion]:
        """메시지 분석하여 초대 제안 종합 생성

        Args:
            message: 분석할 메시지
            project_agents: 현재 프로젝트에 참여 중인 에이전트 ID 집합
            sender_role: 메시지 발신자 역할 (선임에이전트 확인용)

        Returns:
            초대 제안 목록
        """
        suggestions = []

        # 1. @멘션 기반 제안 (모든 사용자 가능)
        mentions = cls.parse_mentions(message)
        if mentions:
            mention_suggestions = cls.create_mention_suggestions(
                mentions, project_agents
            )
            suggestions.extend(mention_suggestions)

        # 2. 키워드 기반 자동 제안 (선임에이전트만)
        if sender_role and cls.can_suggest_invite(sender_role):
            keyword_suggestions = cls.detect_keywords(message, project_agents)
            suggestions.extend(keyword_suggestions)

        # 중복 제거 (멘션이 키워드보다 우선)
        seen_agents = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion.suggested_agent_id not in seen_agents:
                seen_agents.add(suggestion.suggested_agent_id)
                unique_suggestions.append(suggestion)

        return unique_suggestions
