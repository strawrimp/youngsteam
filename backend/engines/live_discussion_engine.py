"""
LiveDiscussionEngine: 실시간 체인형 토론 엔진.

기존 DebateEngine(asyncio.gather 병렬)과 달리,
에이전트가 순차적으로 발언하며 이전 발언자의 의견을 보고 응답합니다.

특징:
1. 고정 순서: Manager → Developer → Designer → Researcher
2. 2라운드 진행
3. WebSocket으로 실시간 스트리밍
4. AgentTaskExecutor를 통한 Tool Use 지원
5. 토론 종료 시 Manager가 요약 생성
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from database import SessionLocal
from models import Conversation, Message as DBMessage

logger = logging.getLogger(__name__)

# 고정 발언 순서 (role 기준)
AGENT_ORDER = ["manager", "developer", "designer", "researcher"]
DEFAULT_ROUNDS = 2


@dataclass
class DiscussionMessage:
    """토론 메시지."""

    agent_id: str
    agent_name: str
    agent_role: str
    content: str
    round_num: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DiscussionInfo:
    """진행 중인 토론 정보."""

    discussion_id: str
    topic: str
    conversation_id: str
    num_rounds: int
    current_round: int = 1
    current_agent_index: int = 0
    messages: List[DiscussionMessage] = field(default_factory=list)
    status: str = "active"  # active | completed | error
    summary: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None


class LiveDiscussionEngine:
    """실시간 체인형 토론 엔진."""

    def __init__(self):
        self.agents: Dict[str, Any] = {}  # agent_id -> agent instance
        self.deepseek_service = None
        self.archive_service = None  # ★ ArchiveService 참조 (main.py에서 주입)
        self.active_discussions: Dict[str, DiscussionInfo] = {}
        self._ws_send_callback: Optional[Callable] = None
        self._background_tasks: Dict[str, asyncio.Task] = {}  # discussion_id -> task

    def register_agent(self, agent_id: str, agent: Any):
        """에이전트 등록."""
        self.agents[agent_id] = agent
        logger.info(f"LiveDiscussionEngine: Registered agent {agent_id} ({agent.name})")

    def set_deepseek_service(self, service):
        """DeepSeek 서비스 주입."""
        self.deepseek_service = service
        logger.info("LiveDiscussionEngine: DeepSeekService injected")

    def set_archive_service(self, service):
        """ArchiveService 주입 (main.py에서 호출)."""
        self.archive_service = service
        logger.info("LiveDiscussionEngine: ArchiveService injected")

    def set_ws_send_callback(self, callback: Callable):
        """WebSocket 전송 콜백 설정.

        callback signature: async callback(data: dict)
        """
        self._ws_send_callback = callback

    async def _send_ws(self, data: dict):
        """WebSocket로 이벤트 전송."""
        if not self._ws_send_callback:
            logger.warning(
                f"[LiveDiscussion] No WS callback set, cannot send: {data.get('type', 'unknown')}"
            )
            return
        try:
            logger.info(
                f"[LiveDiscussion] Sending WS event: {data.get('type', 'unknown')} (discussion: {data.get('discussion_id', 'N/A')})"
            )
            await self._ws_send_callback(data)
        except Exception as e:
            logger.error(
                f"[LiveDiscussion] WS send error for {data.get('type', 'unknown')}: {type(e).__name__}: {e}"
            )

    def _get_ordered_agents(self) -> List[tuple]:
        """AGENT_ORDER에 따라 정렬된 (agent_id, agent) 리스트 반환."""
        ordered = []
        for role in AGENT_ORDER:
            for aid, agent in self.agents.items():
                if hasattr(agent, "role") and agent.role == role:
                    ordered.append((aid, agent))
                    break
        return ordered

    async def start_discussion(
        self,
        topic: str,
        conversation_id: str,
        num_rounds: int = DEFAULT_ROUNDS,
        force_discussion: bool = False,
    ) -> DiscussionInfo:
        """토론 시작.

        Args:
            topic: 토론 주제
            conversation_id: 대화 ID
            num_rounds: 라운드 수
            force_discussion: 버튼 강제 시작 여부

        Returns:
            DiscussionInfo
        """
        discussion_id = f"disc_{uuid.uuid4().hex[:12]}"

        info = DiscussionInfo(
            discussion_id=discussion_id,
            topic=topic,
            conversation_id=conversation_id,
            num_rounds=num_rounds,
        )
        self.active_discussions[discussion_id] = info

        # 시작 이벤트 전송
        participants = [
            {
                "agent_id": aid,
                "agent_name": agent.name,
                "agent_role": agent.role,
            }
            for aid, agent in self._get_ordered_agents()
        ]
        logger.info(
            f"[LiveDiscussion] Participants: {[(p['agent_name'], p['agent_role']) for p in participants]}"
        )

        await self._send_ws(
            {
                "type": "discussion_start",
                "discussion_id": discussion_id,
                "topic": topic,
                "num_rounds": num_rounds,
                "participants": participants,
            }
        )

        logger.info(f"[LiveDiscussion] Started: {topic} (rounds={num_rounds})")

        # 체인형 토론 실행 (비동기 백그라운드)
        task = asyncio.create_task(self._run_chain_discussion(info))
        task.add_done_callback(self._on_discussion_task_done)
        self._background_tasks[discussion_id] = task

        return info

    async def _run_chain_discussion(self, info: DiscussionInfo):
        """체인형 토론 실행 — 에이전트가 순차적으로 발언."""

        ordered_agents = self._get_ordered_agents()
        if not ordered_agents:
            logger.error("[LiveDiscussion] No agents available for discussion!")
            info.status = "error"
            await self._send_ws(
                {
                    "type": "discussion_end",
                    "discussion_id": info.discussion_id,
                    "status": "error",
                    "error": "No agents available",
                }
            )
            return

        logger.info(
            f"[LiveDiscussion] Starting chain discussion with {len(ordered_agents)} agents: "
            f"{[a.name for _, a in ordered_agents]}"
        )

        try:
            for round_num in range(1, info.num_rounds + 1):
                info.current_round = round_num

                # 라운드 시작 알림
                await self._send_ws(
                    {
                        "type": "discussion_round_change",
                        "discussion_id": info.discussion_id,
                        "round": round_num,
                        "total_rounds": info.num_rounds,
                    }
                )

                for idx, (agent_id, agent) in enumerate(ordered_agents):
                    info.current_agent_index = idx

                    logger.info(
                        f"[LiveDiscussion] R{round_num} - {agent.name} ({agent.role}) speaking..."
                    )

                    # 이전 발언 컨텍스트 구성 (같은 라운드 + 이전 라운드)
                    prev_context = self._build_context(info.messages, round_num)

                    # 에이전트 응답 생성
                    response = await self._get_agent_response(
                        agent_id=agent_id,
                        agent=agent,
                        topic=info.topic,
                        round_num=round_num,
                        prev_context=prev_context,
                    )

                    logger.info(
                        f"[LiveDiscussion] R{round_num} - {agent.name} responded ({len(response)} chars)"
                    )

                    # 메시지 저장
                    msg = DiscussionMessage(
                        agent_id=agent_id,
                        agent_name=agent.name,
                        agent_role=agent.role,
                        content=response,
                        round_num=round_num,
                    )
                    info.messages.append(msg)

                    # 실시간 메시지 전송
                    await self._send_ws(
                        {
                            "type": "discussion_message",
                            "discussion_id": info.discussion_id,
                            "agent_id": agent_id,
                            "agent_name": agent.name,
                            "agent_role": agent.role,
                            "content": response,
                            "round": round_num,
                            "message_index": len(info.messages) - 1,
                        }
                    )

                    # ★ DB에 토론 메시지 저장
                    self._save_message_to_db(
                        conversation_id=info.conversation_id,
                        agent_id=agent_id,
                        content=f"[R{round_num}] {response}",
                    )

            # 요약 생성
            summary = await self._generate_summary(info.topic, info.messages)
            info.summary = summary

            # 종료 이벤트
            info.status = "completed"
            info.ended_at = datetime.now()
            await self._send_ws(
                {
                    "type": "discussion_end",
                    "discussion_id": info.discussion_id,
                    "status": "completed",
                    "summary": summary,
                    "message_count": len(info.messages),
                }
            )

            logger.info(
                f"[LiveDiscussion] Completed: {info.discussion_id} "
                f"({len(info.messages)} messages)"
            )

            # ★ 토론 종료 후 백그라운드 아카이빙 트리거
            self._trigger_archive(info.conversation_id)

        except asyncio.CancelledError:
            # ESC 더블 탭 등으로 취소된 경우
            logger.info(
                f"[LiveDiscussion] Cancelled: {info.discussion_id} "
                f"({len(info.messages)} messages so far)"
            )
            info.status = "cancelled"
            info.ended_at = datetime.now()
            await self._send_ws(
                {
                    "type": "discussion_end",
                    "discussion_id": info.discussion_id,
                    "status": "cancelled",
                    "message_count": len(info.messages),
                    "summary": self._simple_summary(info.topic, info.messages),
                }
            )

        except Exception as e:
            logger.error(f"[LiveDiscussion] Error: {e}")
            import traceback

            logger.error(traceback.format_exc())
            info.status = "error"
            await self._send_ws(
                {
                    "type": "discussion_end",
                    "discussion_id": info.discussion_id,
                    "status": "error",
                    "error": str(e),
                }
            )

    def _build_context(
        self,
        messages: List[DiscussionMessage],
        current_round: int,
    ) -> str:
        """이전 발언 컨텍스트 구성.

        현재 라운드에서 이미 발언한 에이전트의 의견 + 이전 라운드 전체.
        """
        parts = []

        # 이전 라운드 메시지
        prev_round_msgs = [m for m in messages if m.round_num < current_round]
        if prev_round_msgs:
            parts.append(f"=== 이전 라운드 의견 ===")
            for m in prev_round_msgs[-8:]:  # 최근 8개
                parts.append(f"[{m.agent_name}] {m.content[:200]}")

        # 현재 라운드에서 이미 발언한 메시지
        current_round_msgs = [m for m in messages if m.round_num == current_round]
        if current_round_msgs:
            parts.append(f"\n=== 이번 라운드 의견 ===")
            for m in current_round_msgs:
                parts.append(f"[{m.agent_name}] {m.content[:200]}")

        return "\n".join(parts)

    async def _get_agent_response(
        self,
        agent_id: str,
        agent: Any,
        topic: str,
        round_num: int,
        prev_context: str,
    ) -> str:
        """단일 에이전트 응답 생성 (AgentTaskExecutor 활용)."""

        if self.deepseek_service is None:
            logger.warning(
                f"[LiveDiscussion] DeepSeek service not available, using fallback for {agent.name}"
            )
            # Fallback: respond_to_debate 사용
            try:
                prev_dicts = [
                    {
                        "agent_id": m.agent_id,
                        "agent_name": m.agent_name,
                        "content": m.content,
                    }
                    for m in []
                ]
                return await agent.respond_to_debate(
                    topic=topic,
                    previous_messages=prev_dicts,
                    round_num=round_num,
                )
            except Exception as e:
                logger.error(f"Fallback respond error: {e}")
                return f"[Error] {e}"

        # AgentTaskExecutor 경로 (Tool Use 지원)
        try:
            from services.agent_executor import AgentTaskExecutor
        except ImportError as e:
            logger.error(f"[LiveDiscussion] Failed to import AgentTaskExecutor: {e}")
            # Fallback to respond_to_debate
            try:
                return await agent.respond_to_debate(
                    topic=topic,
                    previous_messages=[],
                    round_num=round_num,
                )
            except Exception as e2:
                return f"[Error] Import and fallback both failed: {e2}"

        soul_prompt = agent.get_soul_system_prompt(debate_style="analytical")

        # 토론용 프롬프트 구성
        prompt = f"""[토론 주제] {topic}
[라운드] {round_num}

"""
        if prev_context:
            prompt += f"""[다른 팀원들의 의견]
{prev_context}

"""

        prompt += """위 의견을 참고하여 본인의 전문 분야 관점에서 의견을 제시해주세요.
- 다른 팀원의 의견에 동의하거나 반론을 제시할 수 있습니다.
- 구체적인 근거와 함께 설명해주세요.
- 2~4문장으로 간결하게 작성해주세요."""

        # AgentTaskExecutor로 실행
        executor = AgentTaskExecutor(
            deepseek_service=self.deepseek_service,
        )

        try:
            result = await executor.execute_task(
                task=prompt,
                agent_name=agent.name,
                agent_role=agent.role,
                soul_prompt=soul_prompt,
                conversation_history=agent.get_history(limit=5),
            )
            # 에이전트 히스토리에 저장
            agent.add_to_history("user", prompt)
            agent.add_to_history("assistant", result.final_response)

            return result.final_response
        except Exception as e:
            logger.error(f"AgentTaskExecutor error for {agent.name}: {e}")
            # Fallback
            try:
                return await agent.respond_to_debate(
                    topic=topic,
                    previous_messages=[],
                    round_num=round_num,
                )
            except Exception as e2:
                return f"[Error] {e2}"

    async def _generate_summary(
        self,
        topic: str,
        messages: List[DiscussionMessage],
    ) -> str:
        """Manager 에이전트로 토론 요약 생성.

        AgentTaskExecutor 대신 deepseek_service 직접 호출을 사용합니다.
        이유: AgentTaskExecutor는 soul_prompt를 system_prompt로 사용하는데,
        이게 task 프롬프트(요약 지시)를 집어삼켜서 자기소개를 반환하는 문제가 있습니다.
        """
        if not self.deepseek_service:
            return self._simple_summary(topic, messages)

        # 메시지 정리
        msgs_text = "\n".join(
            [f"[{m.agent_name} R{m.round_num}] {m.content[:200]}" for m in messages]
        )

        # 요약 전용 system prompt — role personality 배제, 오직 요약에 집중
        system_prompt = """당신은 토론 요약 전문가입니다.
주어진 토론 내용을 분석하여 핵심을 간결하게 요약하세요.
개인적인 인사나 소개는 하지 마세요. 오직 토론 내용 요약만 작성하세요."""

        user_prompt = f"""다음 토론을 요약해주세요.

주제: {topic}

토론 내용:
{msgs_text}

요약 형식:
1. 핵심 쟁점 (2-3개)
2. 각 에이전트의 주요 의견
3. 최종 결론 또는 다음 단계 제안

한국어로 간결하게 작성해주세요."""

        try:
            response = await self.deepseek_service.call_model(
                system_prompt=system_prompt,
                user_message=user_prompt,
                conversation_history=[],
                task_type="summary",
            )
            if response and response.strip():
                return response.strip()
            else:
                logger.warning(
                    "[LiveDiscussion] Empty summary response, using fallback"
                )
                return self._simple_summary(topic, messages)
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return self._simple_summary(topic, messages)

    def _simple_summary(self, topic: str, messages: List[DiscussionMessage]) -> str:
        """간단한 기본 요약 (LLM 실패 시 사용)."""
        parts = [f"📋 토론 주제: {topic}\n"]
        for m in messages:
            parts.append(f"- {m.agent_name} (R{m.round_num}): {m.content[:80]}...")
        return "\n".join(parts)

    def _save_message_to_db(
        self, conversation_id: str, agent_id: str, content: str
    ) -> None:
        """토론 메시지를 DB에 저장.

        Args:
            conversation_id: 대화 ID
            agent_id: 에이전트 ID
            content: 메시지 내용
        """
        try:
            db = SessionLocal()
            try:
                # 대화 레코드가 존재하는지 확인
                conv = (
                    db.query(Conversation)
                    .filter(Conversation.id == conversation_id)
                    .first()
                )
                if not conv:
                    logger.warning(
                        f"[DB] Conversation {conversation_id} not found, skipping message save"
                    )
                    return

                msg = DBMessage(
                    conversation_id=conversation_id,
                    agent_id=agent_id,
                    sender_type="agent",
                    content=content,
                    message_type="discussion",
                )
                db.add(msg)
                db.commit()
                logger.info(
                    f"[DB] Saved discussion message: conv={conversation_id}, agent={agent_id}"
                )
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[DB] Failed to save discussion message: {e}")

    def _trigger_archive(self, conversation_id: str):
        """토론 종료 후 비동기 아카이빙 트리거.

        LiveDiscussionEngine 자체는 ArchiveService를 직접 참조하지 않고,
        WS 콜백을 통해 archive_updated 이벤트를 전송합니다.
        실제 분류는 main.py의 WS 핸들러에서 이벤트를 수신하여 처리합니다.
        """
        asyncio.create_task(self._do_archive(conversation_id))

    async def _do_archive(self, conversation_id: str):
        """비동기 아카이빙 — WS로 이벤트를 보내 main.py가 처리하도록 요청."""
        try:
            # 프론트엔드에 아카이빙 요청 알림 (main.py의 WS 루프가 아닌
            # 별도 콜백 체인에서 archive_service를 호출할 수 없으므로
            # 간접적으로 처리: conversation_id만 알림)
            await self._send_ws(
                {
                    "type": "discussion_archive_request",
                    "conversation_id": conversation_id,
                }
            )
            logger.info(
                f"[LiveDiscussion] Archive requested for conv: {conversation_id}"
            )
        except Exception as e:
            logger.warning(f"[LiveDiscussion] Archive trigger failed: {e}")

    def _on_discussion_task_done(self, task: asyncio.Task):
        """Background task 완료 콜백 — 미처리 예외 로깅 + cleanup + 아카이빙."""
        # Find and remove the task reference
        disc_id = None
        conv_id = None
        for did, t in list(self._background_tasks.items()):
            if t is task:
                disc_id = did
                break
        if disc_id:
            info = self.active_discussions.get(disc_id)
            if info:
                conv_id = info.conversation_id
            del self._background_tasks[disc_id]

        try:
            exc = task.exception()
            if exc:
                logger.error(
                    f"[LiveDiscussion] Background task failed with unhandled exception: "
                    f"{type(exc).__name__}: {exc}"
                )
        except asyncio.CancelledError:
            logger.info(
                f"[LiveDiscussion] Background task was cancelled (discussion: {disc_id})"
            )
        except Exception as e:
            logger.error(f"[LiveDiscussion] Error in task done callback: {e}")

        # ★ 토론 완료 후 아카이빙 트리거 (completed 상태인 경우만)
        if disc_id and conv_id and self.archive_service:
            info = self.active_discussions.get(disc_id)
            if info and info.status == "completed":
                asyncio.create_task(self._archive_discussion(conv_id, disc_id))

    def get_discussion_info(self, discussion_id: str) -> Optional[DiscussionInfo]:
        """토론 정보 조회."""
        return self.active_discussions.get(discussion_id)

    def is_discussing(self, conversation_id: str) -> bool:
        """해당 대화에서 토론 중인지 확인."""
        for info in self.active_discussions.values():
            if info.conversation_id == conversation_id and info.status == "active":
                return True
        return False

    async def stop_discussion(self, conversation_id: str) -> bool:
        """토론 즉시 중단.

        Args:
            conversation_id: 대화 ID

        Returns:
            True if a discussion was stopped, False otherwise
        """
        # Find active discussion for this conversation
        disc_id = None
        for did, info in self.active_discussions.items():
            if info.conversation_id == conversation_id and info.status == "active":
                disc_id = did
                break

        if not disc_id:
            logger.warning(
                f"[LiveDiscussion] No active discussion to stop for conv: {conversation_id}"
            )
            return False

        logger.info(f"[LiveDiscussion] Stopping discussion: {disc_id}")

        # Cancel the background task
        task = self._background_tasks.get(disc_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"[LiveDiscussion] Task cancelled: {disc_id}")

        return True

    async def _archive_discussion(self, conversation_id: str, discussion_id: str):
        """토론 완료 후 아카이빙 (비동기 백그라운드)."""
        try:
            result = await self.archive_service.archive_conversation(conversation_id)
            if result:
                logger.info(
                    f"[LiveDiscussion] Archived discussion: disc={discussion_id} "
                    f"title='{result.get('title', 'N/A')}'"
                )
                # 프론트엔드에 아카이브 갱신 알림
                await self._send_ws(
                    {
                        "type": "archive_updated",
                        "conversation_id": conversation_id,
                        "title": result.get("title", ""),
                        "category": result.get("category", ""),
                        "tags": result.get("tags", []),
                    }
                )
        except Exception as e:
            logger.warning(f"[LiveDiscussion] Post-discussion archive failed: {e}")
