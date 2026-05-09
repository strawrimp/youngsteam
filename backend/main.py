"""Main FastAPI application for AI Virtual Company backend."""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
import json
import logging
import re
import asyncio
from pathlib import Path

# 클로(OpenClaw) 멘션 패턴: 한국어 조사 지원
# 매칭: @openclaw, @클로, 클로야, 클로를, 클로가, 클로한테 등
# 비매칭: 클로버, 클로딘 (다른 단어의 일부일 때)
# 참고: 한국어 조사 목록 — 주격(이/가), 목적격(을/를), 보격(이/가),
#          관형격(의), 부사격(에/에서/로/으로/와/과/랑),
#          호격(야/아), 접속(와/과/랑/이랑), 보조사(는/은/도/만/부터/까지/조차/밖에)
#          비교(보다), 서술격(이다/이가), 처럼, 한테/에게/한테서/에게서
CLAW_MENTION_PATTERN = re.compile(
    r"(?:"
    r"@openclaw\b"  # @openclaw (영문)
    r"|@클로(?![가-힣])"  # @클로 (한글 이어지지 않을 때)
    r"|(?:^|[\s,.!?\"'「『【])"  # 단어 경계 (시작/공백/구두점/인용)
    r"클로"  # 이름
    r"(?:"
    r"야|아|이|가|는|은|을|를|의|에|서|와|과|도|만|"
    r"로|으로|랑|이랑|"
    r"한테|한테서|에게|에게서|"
    r"부터|까지|조차|마저|밖에|보다|처럼|"
    r"이고|이가|"
    r"이야|이지|이라는"
    r")*?"
    r"(?=[\s,.!?\"'~」」】\)]|$)"
    r")",
    re.IGNORECASE,
)

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db, init_db, SessionLocal, engine
from models import Agent, Conversation, Message, TeamSettings
from engines.conversation_engine import ConversationEngine
from engines.voting_engine import VotingEngine
from engines.debate_engine import DebateEngine
from engines.live_discussion_engine import LiveDiscussionEngine
from agents.agent_message_broker import AgentMessageBroker
from services.memory_service import MemoryService
from services.archive_service import ArchiveService
from services.conversation_service import ConversationService
from seed import ensure_agents_seeded, ensure_team_settings
from services.deepseek_service import DeepSeekService
from services.glm_service import GLMService
from services.llm_provider_service import (
    LLMProviderService,
    DeepSeekProvider,
    OpenAIProvider,
    GeminiProvider,
    OllamaProvider,
)
from agents.manager_agent import ManagerAgent
from agents.developer_agent import DeveloperAgent
from agents.designer_agent import DesignerAgent
from agents.researcher_agent import ResearcherAgent
from agents.openclaw_agent import OpenClawAgent
from config import settings
from websocket.manager import ConnectionManager
from websocket.events import EventType, create_event
from routes import projects_router, agents_router, discussions_router, votes_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup/shutdown."""
    # Startup
    logger.info("Starting up AI Virtual Company backend")

    # ★ DB 경로 로깅 (실행 위치에 따른 분기 감지용)
    db_url = str(settings.database_url)
    db_path = db_url.replace("sqlite:///", "")
    logger.info(f"[DB] DATABASE_URL: {db_url}")
    logger.info(f"[DB] SQLite file:   {db_path}")
    logger.info(f"[DB] File exists:   {Path(db_path).exists()}")

    try:
        init_db()
        logger.info("Database initialized")

        # ★ Auto-seed default agents if table is empty (P1 fix: /api/agents 빈 배열 방지)
        ensure_agents_seeded()
        ensure_team_settings()
        logger.info("Auto-seed check complete")

        # Initialize engines and services
        app.state.conversation_engine = ConversationEngine()
        app.state.voting_engine = VotingEngine()
        app.state.debate_engine = DebateEngine()
        app.state.live_discussion_engine = LiveDiscussionEngine()
        app.state.message_broker = AgentMessageBroker()
        app.state.memory_service = MemoryService()

        # Use DeepSeek service with hybrid V4 + R1 strategy
        app.state.deepseek_service = DeepSeekService(
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
            temperature=settings.deepseek_temperature,
            enable_hybrid=settings.deepseek_enable_hybrid,
        )
        logger.info(
            f"✅ DeepSeek Service initialized (Hybrid: {settings.deepseek_enable_hybrid})"
        )
        logger.info(
            "   API Key: *** (configured)"
            if settings.deepseek_api_key
            else "   API Key: NOT SET"
        )

        # Inject DeepSeekService into ConversationEngine for Tool Use
        app.state.conversation_engine.set_deepseek_service(app.state.deepseek_service)
        logger.info("✅ DeepSeekService injected into ConversationEngine")

        # Inject LiveDiscussionEngine into ConversationEngine
        app.state.live_discussion_engine.set_deepseek_service(
            app.state.deepseek_service
        )
        app.state.conversation_engine.set_live_discussion_engine(
            app.state.live_discussion_engine
        )
        logger.info("✅ LiveDiscussionEngine initialized and linked")

        # Keep GLM service for backward compatibility
        app.state.glm_service = GLMService()

        # Initialize multi-provider LLM service
        llm_provider_service = LLMProviderService()

        # Register DeepSeek as primary provider
        deepseek_provider = DeepSeekProvider(
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
        )
        llm_provider_service.register_provider(
            "deepseek", deepseek_provider, is_primary=True
        )
        logger.info(f"✅ Registered LLM Provider: DeepSeek (Primary)")

        openclaw_service = None

        if settings.openclaw_enabled:
            from services.openclaw_service import OpenClawService

            openclaw_service = OpenClawService(
                base_url=settings.openclaw_base_url,
                api_key=settings.openclaw_api_key,
                timeout=settings.openclaw_timeout,
            )

            try:
                oc_healthy = await openclaw_service.health_check()
                if oc_healthy:
                    logger.info(f"✅ OpenClaw Gateway reachable at {settings.openclaw_base_url}")
                else:
                    logger.warning(f"⚠️ OpenClaw Gateway not reachable at {settings.openclaw_base_url}")
            except Exception as e:
                logger.warning(f"⚠️ OpenClaw health check failed: {e}")
        else:
            logger.info("   OpenClaw: DISABLED")

        # ★ Store in app.state for @openclaw mention handler
        app.state.openclaw_service = openclaw_service

        # Register Gemini as fallback #1
        if settings.gemini_api_key:
            gemini_provider = GeminiProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                temperature=settings.gemini_temperature,
            )
            llm_provider_service.register_provider("gemini", gemini_provider)
            logger.info(f"✅ Registered LLM Provider: Gemini (Fallback #1)")
        else:
            logger.info("   Gemini API Key: NOT SET (skipping)")

        # Register OpenAI if available (legacy)
        if settings.openai_api_key:
            openai_provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                model="gpt-4o",
            )
            llm_provider_service.register_provider("openai", openai_provider)
            logger.info(f"✅ Registered LLM Provider: OpenAI (Legacy)")

        # Always support Ollama for local inference (fallback #2)
        ollama_provider = OllamaProvider(
            base_url=settings.ollama_url,
            model=settings.ollama_model,
        )
        llm_provider_service.register_provider("ollama", ollama_provider)
        logger.info(f"✅ Registered LLM Provider: Ollama (Local Fallback #2)")

        app.state.ws_manager = ConnectionManager()
        logger.info("✅ WebSocket Connection Manager initialized")

        # Get agents from database
        db = SessionLocal()
        try:
            agents = db.query(Agent).all()
        finally:
            db.close()

        # Agent factory mapping
        agent_factories = {
            "manager": lambda agent_id, name, service: ManagerAgent(
                agent_id, name, service
            ),
            "developer": lambda agent_id, name, service: DeveloperAgent(
                agent_id, name, service
            ),
            "designer": lambda agent_id, name, service: DesignerAgent(
                agent_id, name, service
            ),
            "researcher": lambda agent_id, name, service: ResearcherAgent(
                agent_id, name, service
            ),
            "bot": lambda agent_id, name, _service: OpenClawAgent(
                agent_id, name, openclaw_service=lambda: getattr(
                    app.state, "openclaw_service", None
                ),
            ),
        }

        for agent in agents:
            if agent.role not in agent_factories:
                logger.warning(f"Unsupported agent role: {agent.role}")
                continue

            try:
                factory = agent_factories[agent.role]
                agent_instance = factory(
                    str(agent.id), agent.name, app.state.deepseek_service
                )
                app.state.conversation_engine.register_agent(
                    str(agent.id), agent_instance
                )
                app.state.debate_engine.register_agent(str(agent.id), agent_instance)
                app.state.live_discussion_engine.register_agent(
                    str(agent.id), agent_instance
                )
                logger.info(f"Registered agent: {agent.name} ({agent.role})")
            except Exception as e:
                logger.error(f"Failed to register agent {agent.name}: {e}")
        logger.info(
            f"Conversation engine initialized with {len(app.state.conversation_engine.agents)} agents"
        )

        # ★ ConversationService를 ConversationEngine에 주입 (과거 대화 검색용)
        conv_service_db = SessionLocal()
        conversation_service = ConversationService(conv_service_db)
        app.state.conversation_engine.set_conversation_service(conversation_service)
        logger.info("✅ ConversationService wired to ConversationEngine")

        # ArchiveService 초기화 — Manager 에이전트로 자동 분류
        app.state.archive_service = ArchiveService(
            deepseek_service=app.state.deepseek_service
        )
        # manager 역할 에이전트를 아카이브 분류기로 주입
        for aid, agent in app.state.conversation_engine.agents.items():
            if hasattr(agent, "role") and agent.role == "manager":
                app.state.archive_service.set_manager_agent(agent)
                logger.info("✅ ArchiveService initialized with Manager agent")
                break
        if not app.state.archive_service.manager_agent:
            logger.warning(
                "⚠️ ArchiveService: No manager agent found, classification disabled"
            )

        # LiveDiscussionEngine에도 archive_service 주입 (토론 종료 후 아카이빙)
        app.state.live_discussion_engine.set_archive_service(app.state.archive_service)

    except Exception as e:
        logger.error(f"Failed to initialize: {e}")

    yield
    # Shutdown
    logger.info("Shutting down")


app = FastAPI(
    title="AI Virtual Company",
    description="Multi-agent AI collaboration system",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:7518",
        "http://localhost:7520",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:7518",
        "http://127.0.0.1:7520",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


from services.agent_executor import AgentTaskExecutor, TaskStep

app.include_router(projects_router)
app.include_router(agents_router)
app.include_router(discussions_router)
app.include_router(votes_router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "environment": settings.environment}


# WebSocket endpoint for real-time chat
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
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
                        await app.state.ws_manager.subscribe_to_project(
                            websocket, project_id
                        )
                        await app.state.ws_manager.send_personal_message(
                            {"type": "subscribed", "project_id": project_id}, websocket
                        )

                elif action == "unsubscribe_project":
                    # 프로젝트 구독 해제
                    project_id = message.get("project_id")
                    if project_id:
                        await app.state.ws_manager.unsubscribe_from_project(
                            websocket, project_id
                        )
                        await app.state.ws_manager.send_personal_message(
                            {"type": "unsubscribed", "project_id": project_id},
                            websocket,
                        )

                elif action == "chat":
                    # 채팅 + Tool Use 통합 로직
                    user_message = message.get("content", "").strip()
                    conversation_id = message.get("conversation_id")
                    force_discussion = message.get("force_discussion", False)
                    target_agent_role = message.get(
                        "target_agent_role"
                    )  # 답장: 특정 에이전트만 응답
                    image_data = message.get("image_data")  # ★ base64 이미지 데이터

                    if not conversation_id:
                        await app.state.ws_manager.send_personal_message(
                            {"error": "Conversation ID required"}, websocket
                        )
                        continue

                    # ★ @openclaw / @클로 멘션 → 클로 에이전트로 라우팅 (Agent 등록됨)
                    if CLAW_MENTION_PATTERN.search(user_message):
                        logger.info(
                            f"[ClawRoute] CLAW_MENTION detected, routing to openclaw-bot. "
                            f"conversation_id={conversation_id}"
                        )
                        target_agent_role = "bot"
                        user_message = CLAW_MENTION_PATTERN.sub(" ", user_message).strip()
                        user_message = re.sub(r"\s+", " ", user_message)
                        force_discussion = False

                    # 답장 타겟: role → agent_id 변환
                    target_agent_ids = None
                    if target_agent_role:
                        engine = app.state.conversation_engine
                        for aid, agent in engine.agents.items():
                            if (
                                hasattr(agent, "role")
                                and agent.role == target_agent_role
                            ):
                                target_agent_ids = [aid]
                                logger.info(
                                    f"[Reply] Targeting agent: {agent.name} ({aid})"
                                )
                                break
                        if not target_agent_ids:
                            logger.warning(
                                f"[Reply] No agent found for role: {target_agent_role}"
                            )

                    # 실시간 Tool Use step 스트리밍 콜백
                    async def on_agent_step(agent_id: str, agent_name: str, step: dict):
                        """Stream each tool use step to the frontend in real-time."""
                        try:
                            await websocket.send_json(
                                {
                                    "type": "agent_step",
                                    "agent_id": agent_id,
                                    "agent_name": agent_name,
                                    "step": step,
                                }
                            )
                        except Exception:
                            pass  # Client disconnected

                    engine = app.state.conversation_engine

                    # ★ 미리 참여 에이전트 결정 → agents_thinking 이벤트 전송
                    if target_agent_ids:
                        resolved_agent_ids = target_agent_ids
                    else:
                        resolved_agent_ids = engine._determine_agents(user_message)

                    # 에이전트 "작업 시작" 이벤트 전송
                    thinking_agents = []
                    for aid in resolved_agent_ids:
                        agent = engine.agents.get(aid)
                        if agent:
                            thinking_agents.append(
                                {
                                    "id": aid,
                                    "name": agent.name,
                                    "role": getattr(agent, "role", aid),
                                }
                            )
                    if thinking_agents:
                        await websocket.send_json(
                            {
                                "type": "agents_thinking",
                                "agents": thinking_agents,
                            }
                        )
                        logger.info(
                            f"[WorkingBar] Sent agents_thinking: {[a['name'] for a in thinking_agents]}"
                        )

                    # Set WS callback for LiveDiscussionEngine
                    async def ws_send_callback(data: dict):
                        try:
                            logger.debug(
                                f"[WS Callback] Sending: {data.get('type', 'unknown')}"
                            )
                            await websocket.send_json(data)
                        except Exception as e:
                            logger.error(
                                f"[WS Callback] Send failed: {type(e).__name__}: {e}"
                            )

                    app.state.live_discussion_engine.set_ws_send_callback(
                        ws_send_callback
                    )

                    try:
                        logger.info(
                            "About to call engine.process_message with Tool Use"
                        )

                        # ★ DB에 대화 & 사용자 메시지 저장
                        try:
                            conv_db = SessionLocal()
                            try:
                                # 대화 레코드가 없으면 생성
                                existing_conv = (
                                    conv_db.query(Conversation)
                                    .filter(Conversation.id == conversation_id)
                                    .first()
                                )
                                if not existing_conv:
                                    # 빠른 제목: 사용자 메시지 앞 20자
                                    quick_title = user_message[:20] + (
                                        "..." if len(user_message) > 20 else ""
                                    )
                                    conv = Conversation(
                                        id=conversation_id,
                                        title=quick_title,
                                    )
                                    conv_db.add(conv)
                                    conv_db.commit()
                                    logger.info(
                                        f"[DB] Created conversation: {conversation_id} (title: {quick_title})"
                                    )

                                # 사용자 메시지 저장
                                msg_type = "image" if image_data else "text"
                                # 이미지가 있으면 content에 base64 데이터 포함
                                saved_content = user_message
                                if image_data:
                                    # base64 데이터를 content에 저장 (프론트엔드에서 직접 렌더링)
                                    saved_content = f"{user_message}\n[IMAGE_DATA]{image_data}" if user_message else f"[IMAGE_DATA]{image_data}"
                                user_msg = Message(
                                    conversation_id=conversation_id,
                                    sender_type="user",
                                    content=saved_content,
                                    message_type=msg_type,
                                )
                                conv_db.add(user_msg)
                                conv_db.commit()
                            finally:
                                conv_db.close()
                        except Exception as db_err:
                            logger.warning(
                                f"[DB] Failed to save user message: {db_err}"
                            )

                        result = await engine.process_message(
                            conversation_id,
                            user_message,
                            agent_ids=resolved_agent_ids,  # 미리 결정한 에이전트 목록
                            step_callback=lambda aid, aname, step: (
                                asyncio.ensure_future(on_agent_step(aid, aname, step))
                            ),
                            force_discussion=force_discussion,
                            image_context=f"[사용자가 이미지를 첨부했습니다. 이미지 내용을 바탕으로 답변해주세요.]" if image_data else None,
                        )

                        # Check if discussion mode was triggered
                        if result.get("discussion_mode"):
                            # Discussion events are sent via ws_send_callback
                            # Just send the initial confirmation
                            await websocket.send_json(
                                {
                                    "type": "discussion_mode",
                                    "discussion_id": result["discussion_id"],
                                    "topic": result["topic"],
                                }
                            )
                            continue

                        # Normal response flow
                        logger.info(
                            f"Engine returned with {len(result.get('agent_responses', {}))} responses"
                        )

                        # Send agent responses
                        for agent_id, response in result.get(
                            "agent_responses", {}
                        ).items():
                            agent = engine.agents.get(agent_id)
                            if agent:
                                agent_name = agent.name
                            else:
                                agent_name = agent_id
                                logger.warning(f"Agent {agent_id} not found")

                            await websocket.send_json(
                                {
                                    "type": "agent_response",
                                    "agent_id": agent_id,
                                    "agent_name": agent_name,
                                    "agent_role": getattr(agent, "role", agent_id)
                                    if agent
                                    else agent_id,
                                    "content": response,
                                    "timestamp": result["timestamp"],
                                }
                            )

                            # ★ DB에 에이전트 응답 저장
                            try:
                                conv_db = SessionLocal()
                                try:
                                    agent_msg = Message(
                                        conversation_id=conversation_id,
                                        agent_id=agent_id,
                                        sender_type="agent",
                                        content=response,
                                    )
                                    conv_db.add(agent_msg)
                                    conv_db.commit()
                                finally:
                                    conv_db.close()
                            except Exception as db_err:
                                logger.warning(
                                    f"[DB] Failed to save agent response: {db_err}"
                                )

                            # ★ 에이전트 "작업 완료" 이벤트 전송
                            await websocket.send_json(
                                {
                                    "type": "agent_done",
                                    "agent_id": agent_id,
                                    "agent_name": agent_name,
                                }
                            )

                        # ★ 비동기 백그라운드 아카이빙 (LLM 분류)
                        try:
                            # 메시지가 3개 이상이면 LLM으로 자동 분류
                            _conv_db_check = SessionLocal()
                            try:
                                _msg_count = (
                                    _conv_db_check.query(Message)
                                    .filter(Message.conversation_id == conversation_id)
                                    .count()
                                )
                            finally:
                                _conv_db_check.close()

                            if _msg_count >= 3 and hasattr(
                                app.state, "archive_service"
                            ):

                                async def _do_archive():
                                    try:
                                        result = await app.state.archive_service.archive_conversation(
                                            conversation_id
                                        )
                                        if result:
                                            logger.info(
                                                f"[Archive] Auto-archived: {result.get('title', 'N/A')}"
                                            )
                                            # 프론트엔드에 아카이브 갱신 알림
                                            await websocket.send_json(
                                                {
                                                    "type": "archive_updated",
                                                    "conversation_id": conversation_id,
                                                    "title": result.get("title", ""),
                                                    "category": result.get(
                                                        "category", ""
                                                    ),
                                                    "tags": result.get("tags", []),
                                                }
                                            )
                                    except Exception as arch_err:
                                        logger.warning(
                                            f"[Archive] Background archive failed: {arch_err}"
                                        )

                                asyncio.create_task(_do_archive())
                        except Exception as count_err:
                            logger.warning(
                                f"[Archive] Message count check failed: {count_err}"
                            )

                        # Save to memory
                        try:
                            await app.state.memory_service.save_memory(
                                category="conversation",
                                content=f"User: {user_message}",
                                created_by="user",
                            )
                        except Exception as mem_err:
                            logger.warning(f"Failed to save to memory: {mem_err}")

                        # Send completion status
                        await websocket.send_json(
                            {
                                "type": "status",
                                "status": "complete",
                                "message": "✅ 모든 에이전트가 응답했습니다.",
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error processing chat message: {e}")
                        await websocket.send_json(
                            {
                                "error": str(e),
                            }
                        )

                elif action == "new_conversation":
                    # 새 대화 시작 — 기존 대화 종료 + 아카이빙
                    old_conversation_id = message.get("conversation_id")
                    logger.info(
                        f"[NewConversation] Request received. Old conv: {old_conversation_id}"
                    )

                    if old_conversation_id:
                        # 1) 기존 대화 종료
                        try:
                            conv_db = SessionLocal()
                            try:
                                conv = (
                                    conv_db.query(Conversation)
                                    .filter(Conversation.id == old_conversation_id)
                                    .first()
                                )
                                if conv and conv.ended_at is None:
                                    conv.ended_at = datetime.utcnow()
                                    conv_db.commit()
                                    logger.info(
                                        f"[NewConversation] Ended conv: {old_conversation_id}"
                                    )
                            finally:
                                conv_db.close()
                        except Exception as db_err:
                            logger.warning(
                                f"[NewConversation] DB error ending conv: {db_err}"
                            )

                        # 2) 비동기 아카이빙 (LLM 분류)
                        if hasattr(app.state, "archive_service"):

                            async def _archive_old():
                                try:
                                    result = await app.state.archive_service.archive_conversation(
                                        old_conversation_id
                                    )
                                    if result:
                                        logger.info(
                                            f"[NewConversation] Archived: {result.get('title', 'N/A')}"
                                        )
                                        await websocket.send_json(
                                            {
                                                "type": "archive_updated",
                                                "conversation_id": old_conversation_id,
                                                "title": result.get("title", ""),
                                                "category": result.get("category", ""),
                                                "tags": result.get("tags", []),
                                            }
                                        )
                                except Exception as arch_err:
                                    logger.warning(
                                        f"[NewConversation] Archive failed: {arch_err}"
                                    )

                            asyncio.create_task(_archive_old())

                    # 3) 프론트엔드에 새 대화 준비 완료 알림
                    await websocket.send_json(
                        {
                            "type": "conversation_closed",
                            "old_conversation_id": old_conversation_id,
                        }
                    )

                elif action == "execute_task":
                    # 에이전트 업무 실행 (Tool Use)
                    task = message.get("task", "").strip()
                    agent_id = message.get("agent_id", "")
                    agent_name = message.get("agent_name", "에이전트")
                    agent_role = message.get("agent_role", "developer")
                    soul_prompt = message.get("soul_prompt", "")

                    if not task:
                        await websocket.send_json({"error": "task is required"})
                        continue

                    # Send start event
                    await websocket.send_json(
                        {
                            "type": "task_start",
                            "agent_id": agent_id,
                            "agent_name": agent_name,
                            "task": task,
                        }
                    )

                    # Create executor with real-time step streaming
                    async def send_step(step: TaskStep):
                        try:
                            await websocket.send_json(
                                {
                                    "type": "task_step",
                                    "agent_id": agent_id,
                                    "agent_name": agent_name,
                                    "step": {
                                        "type": step.type,
                                        "content": step.content,
                                        "tool_name": step.tool_name,
                                        "tool_args": step.tool_args,
                                        "success": step.success,
                                    },
                                }
                            )
                        except Exception:
                            pass  # Client disconnected

                    executor = AgentTaskExecutor(
                        deepseek_service=app.state.deepseek_service,
                        on_step=lambda step: asyncio.ensure_future(send_step(step)),
                    )

                    try:
                        result = await executor.execute_task(
                            task=task,
                            agent_name=agent_name,
                            agent_role=agent_role,
                            soul_prompt=soul_prompt,
                        )

                        await websocket.send_json(
                            {
                                "type": "task_complete",
                                "agent_id": agent_id,
                                "agent_name": agent_name,
                                "task": task,
                                "final_response": result.final_response,
                                "result": result.to_dict(),
                            }
                        )
                    except Exception as e:
                        logger.error(f"Task execution error: {e}")
                        await websocket.send_json(
                            {
                                "type": "task_error",
                                "agent_id": agent_id,
                                "error": str(e),
                            }
                        )

                elif action == "start_debate":
                    # 체인형 토론 시작 (버튼 클릭)
                    topic = message.get("topic", "").strip()
                    conversation_id = message.get("conversation_id")

                    if not conversation_id:
                        await websocket.send_json({"error": "Conversation ID required"})
                        continue

                    if not topic:
                        # 주제가 없으면 최근 사용자 메시지를 주제로 사용
                        topic = "이 주제에 대해 토론해봅시다"

                    # Set WS callback for LiveDiscussionEngine
                    async def debate_ws_callback(data: dict):
                        try:
                            logger.debug(
                                f"[WS Callback] Sending: {data.get('type', 'unknown')}"
                            )
                            await websocket.send_json(data)
                        except Exception as e:
                            logger.error(
                                f"[WS Callback] Send failed: {type(e).__name__}: {e}"
                            )

                    app.state.live_discussion_engine.set_ws_send_callback(
                        debate_ws_callback
                    )

                    discussion_info = (
                        await app.state.live_discussion_engine.start_discussion(
                            topic=topic,
                            conversation_id=conversation_id,
                            num_rounds=2,
                            force_discussion=True,
                        )
                    )

                    await websocket.send_json(
                        {
                            "type": "discussion_mode",
                            "discussion_id": discussion_info.discussion_id,
                            "topic": topic,
                        }
                    )

                    logger.info(
                        f"[Debate] Started: {topic} (id: {discussion_info.discussion_id})"
                    )

                elif action == "stop_debate":
                    # 토론 즉시 중단 (ESC 더블 탭)
                    conversation_id = message.get("conversation_id")

                    if not conversation_id:
                        await websocket.send_json({"error": "Conversation ID required"})
                        continue

                    stopped = await app.state.live_discussion_engine.stop_discussion(
                        conversation_id
                    )

                    if stopped:
                        await websocket.send_json(
                            {
                                "type": "discussion_stopped",
                                "conversation_id": conversation_id,
                            }
                        )
                        logger.info(
                            f"[Debate] Stopped discussion for conv: {conversation_id}"
                        )
                    else:
                        await websocket.send_json(
                            {
                                "type": "discussion_stopped",
                                "conversation_id": conversation_id,
                                "note": "No active discussion to stop",
                            }
                        )

                else:
                    await websocket.send_json({"error": f"Unknown action: {action}"})

            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json(
                    {
                        "error": str(e),
                    }
                )

    except WebSocketDisconnect:
        app.state.ws_manager.disconnect(websocket)
        logger.info(f"WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {type(e).__name__}: {e}")
        app.state.ws_manager.disconnect(websocket)
        logger.info(f"WebSocket client disconnected due to error")


# REST API: Execute task with tools
@app.post("/api/tasks/execute")
async def execute_task_rest(request_data: dict, db: Session = Depends(get_db)):
    """Execute a task for a specific agent using Tool Use.

    Body: { task, agent_id, agent_name, agent_role, soul_prompt? }
    Returns: { success, final_response, steps, agent_name }
    """
    task = request_data.get("task", "").strip()
    agent_id = request_data.get("agent_id", "")
    agent_name = request_data.get("agent_name", "에이전트")
    agent_role = request_data.get("agent_role", "developer")
    soul_prompt = request_data.get("soul_prompt", "")

    if not task:
        raise HTTPException(status_code=400, detail="task is required")

    executor = AgentTaskExecutor(
        deepseek_service=app.state.deepseek_service,
    )

    try:
        result = await executor.execute_task(
            task=task,
            agent_name=agent_name,
            agent_role=agent_role,
            soul_prompt=soul_prompt,
        )
        return result.to_dict()
    except Exception as e:
        logger.error(f"Task execution REST error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# REST API endpoints for chat
@app.post("/api/chat/message")
async def send_message(request_data: dict = None, db: Session = Depends(get_db)):
    """Send a message to agents."""
    try:
        content = request_data.get("content", "") if request_data else ""

        engine = app.state.conversation_engine
        logger.info(f"Testing with {len(engine.agents)} agents")

        agent_ids = list(engine.agents.keys())
        if agent_ids:
            agent_id = agent_ids[0]
            agent = engine.agents[agent_id]
            logger.info(f"Calling agent {agent.name} directly")

            response = await agent.respond(content)
            logger.info(f"Agent responded: {response[:100]}...")

            return {"status": "ok", "agent": agent.name, "response": response}

        return {"status": "error", "message": "No agents registered"}
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}


# REST API endpoints for agents
@app.get("/api/agents")
async def list_agents(db: Session = Depends(get_db)):
    """List all agents (openclaw-bot included via DB init_agents.py)."""
    agents = db.query(Agent).all()
    return {
        "agents": [
            {
                "id": str(a.id),
                "name": a.name,
                "role": a.role,
                "display_name": a.display_name,
                "emoji": a.emoji,
                "badge_text": a.badge_text,
                "icon": a.icon,
                "color": a.color,
                "status": a.status,
            }
            for a in agents
        ]
    }


# REST API endpoints for memory
@app.get("/api/memory")
async def get_memory(category: str = None, db: Session = Depends(get_db)):
    """Get shared memory by category."""
    return {"status": "ok", "category": category}


# REST API endpoints for voting
@app.post("/api/voting/start")
async def start_voting(request_data: dict, db: Session = Depends(get_db)):
    """Start a voting session."""
    topic = request_data.get("topic")
    candidates = request_data.get("candidates", [])
    conversation_id = request_data.get("conversation_id")

    if not topic or not candidates:
        return {"error": "Missing topic or candidates"}, 400

    voting_id = str(__import__("uuid").uuid4())
    engine = app.state.conversation_engine

    result = await engine.start_voting(conversation_id, topic, candidates)
    result["voting_id"] = voting_id

    return result


@app.get("/api/voting/{voting_id}/result")
async def get_voting_result(voting_id: str, db: Session = Depends(get_db)):
    """Get voting results (voting results are returned from start_voting)."""
    return {"voting_id": voting_id, "status": "ok"}


# REST API endpoints for model usage stats
@app.get("/api/stats/models")
async def get_model_usage_stats():
    """Get DeepSeek V4 vs R1 usage statistics."""
    service = app.state.deepseek_service
    stats = service.get_model_usage_stats()
    return {
        "status": "ok",
        "model_strategy": "hybrid (V4 + R1)",
        "stats": stats,
        "description": {
            "v4": "DeepSeek V4 - Fast, cost-effective for standard tasks",
            "r1": "DeepSeek R1 - Advanced reasoning for complex tasks (voting, strategy, analysis)",
            "hybrid_selection": "Automatic based on task type and complexity",
        },
    }


@app.post("/api/stats/models/reset")
async def reset_model_stats():
    """Reset model usage statistics (admin only)."""
    service = app.state.deepseek_service
    service.reset_usage_stats()
    return {"status": "ok", "message": "Model usage statistics reset"}


# REST API endpoints for debate
@app.post("/api/debate/start")
async def start_debate(request_data: dict):
    """Start a multi-round debate."""
    topic = request_data.get("topic")
    agent_ids = request_data.get("agent_ids", [])
    num_rounds = request_data.get("num_rounds", 2)
    mode = request_data.get("mode", "debate")

    if not topic:
        return {"error": "Missing topic"}, 400

    debate_engine = app.state.debate_engine

    if not agent_ids:
        agent_ids = list(debate_engine.agents.keys())

    result = await debate_engine.start_debate(
        topic=topic,
        agent_ids=agent_ids,
        num_rounds=num_rounds,
        mode=mode,
    )

    return {
        "status": "ok",
        "debate_id": result.debate_id,
        "topic": result.topic,
        "mode": result.mode,
        "rounds": result.rounds,
        "message_count": len(result.messages),
        "final_summary": result.final_summary,
        "messages": [
            {
                "round": m.round_num,
                "agent": m.agent_name,
                "content": m.content,
            }
            for m in result.messages
        ],
    }


@app.get("/api/debate/{debate_id}")
async def get_debate(debate_id: str):
    """Get debate details."""
    return {"status": "ok", "debate_id": debate_id}


# REST API endpoints for LLM providers
@app.get("/api/llm/providers")
async def get_llm_providers():
    """Get available LLM providers."""
    service = app.state.llm_provider_service
    providers = list(service.providers.keys())
    stats = service.get_stats()

    return {
        "status": "ok",
        "providers": providers,
        "primary": service.fallback_order[0] if service.fallback_order else None,
        "stats": stats,
    }


@app.get("/api/llm/stats")
async def get_llm_stats():
    """Get LLM provider statistics."""
    service = app.state.llm_provider_service
    stats = service.get_stats()

    return {
        "status": "ok",
        "stats": stats,
        "description": {
            "calls": "Total API calls made",
            "errors": "Total errors encountered",
            "success_rate": "Success rate (0.0 - 1.0)",
            "avg_latency_ms": "Average latency in milliseconds",
        },
    }


# ==================== Archive API ====================


@app.get("/api/archive/conversations")
async def list_archived_conversations(
    limit: int = 50, offset: int = 0, db: Session = Depends(get_db)
):
    """List archived conversations with pagination."""
    total = db.query(Conversation).count()
    conversations = (
        db.query(Conversation)
        .order_by(Conversation.started_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
        "status": "ok",
        "conversations": [
            {
                "id": str(c.id),
                "title": c.title or "제목 없는 대화",
                "started_at": c.started_at.isoformat() if c.started_at else None,
                "ended_at": c.ended_at.isoformat() if c.ended_at else None,
                "message_count": db.query(Message)
                .filter(Message.conversation_id == c.id)
                .count(),
                "tags": json.loads(c.tags) if c.tags else [],
                "category": c.category or None,
                "summary": c.summary or None,
                "reference_code": c.reference_code or None,
            }
            for c in conversations
        ],
        "total": total,
    }


@app.get("/api/archive/conversations/{conversation_id}")
async def get_conversation_detail(conversation_id: str, db: Session = Depends(get_db)):
    """Get detailed conversation with messages."""
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )

    messages_data = []
    for msg in messages:
        agent = (
            db.query(Agent).filter(Agent.id == msg.agent_id).first()
            if msg.agent_id
            else None
        )
        messages_data.append(
            {
                "id": str(msg.id),
                "agent_id": str(msg.agent_id) if msg.agent_id else None,
                "agent_name": agent.display_name if agent else None,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "sender_type": msg.sender_type,
                "type": msg.message_type,
            }
        )

    return {
        "status": "ok",
        "conversation": {
            "id": str(conversation.id),
            "title": conversation.title or "제목 없는 대화",
            "started_at": conversation.started_at.isoformat()
            if conversation.started_at
            else None,
            "ended_at": conversation.ended_at.isoformat()
            if conversation.ended_at
            else None,
            "tags": json.loads(conversation.tags) if conversation.tags else [],
            "category": conversation.category or None,
            "summary": conversation.summary or None,
            "reference_code": conversation.reference_code or None,
            "messages": messages_data,
        },
    }


@app.get("/api/archive/search")
async def search_conversations(q: str, limit: int = 20, db: Session = Depends(get_db)):
    """Search conversations by content."""
    if len(q) < 2:
        return {"status": "ok", "query": q, "conversations": [], "count": 0}

    search_term = f"%{q}%"
    messages = (
        db.query(Message)
        .filter(Message.content.ilike(search_term))
        .limit(limit * 5)
        .all()
    )

    conv_ids = list(set([m.conversation_id for m in messages]))
    conversations = []
    for conv_id in conv_ids[:limit]:
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        if conv:
            conversations.append(
                {
                    "id": str(conv.id),
                    "title": conv.title or "제목 없는 대화",
                    "started_at": conv.started_at.isoformat()
                    if conv.started_at
                    else None,
                    "ended_at": conv.ended_at.isoformat() if conv.ended_at else None,
                    "message_count": db.query(Message)
                    .filter(Message.conversation_id == conv.id)
                    .count(),
                    "tags": json.loads(conv.tags) if conv.tags else [],
                    "category": conv.category or None,
                    "summary": conv.summary or None,
                    "reference_code": conv.reference_code or None,
                }
            )

    return {
        "status": "ok",
        "query": q,
        "conversations": conversations,
        "count": len(conversations),
    }


@app.delete("/api/archive/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Delete a conversation and its messages."""
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 메시지 먼저 삭제 (FK 제약조건)
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.delete(conversation)
    db.commit()

    return {"status": "ok", "message": f"Conversation {conversation_id} deleted"}


# Team Settings API
@app.get("/api/settings/team")
async def get_team_settings(db: Session = Depends(get_db)):
    """Get team settings."""
    settings = db.query(TeamSettings).first()
    if not settings:
        # Return default settings
        return {
            "team_name": "Young's Team",
            "team_subtitle": "AI Agents Online",
            "team_icon": "terminal",
        }
    return {
        "team_name": settings.team_name,
        "team_subtitle": settings.team_subtitle,
        "team_icon": settings.team_icon,
    }


@app.put("/api/settings/team")
async def update_team_settings(data: dict, db: Session = Depends(get_db)):
    """Update team settings."""
    settings = db.query(TeamSettings).first()
    if not settings:
        # Create new settings
        settings = TeamSettings(**data)
        db.add(settings)
    else:
        # Update existing settings
        for key, value in data.items():
            setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return {
        "team_name": settings.team_name,
        "team_subtitle": settings.team_subtitle,
        "team_icon": settings.team_icon,
    }


# ==================== Frontend Static File Serving ====================

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "build"
if FRONTEND_DIR.exists():
    logger.info(f"🌐 Serving frontend from: {FRONTEND_DIR}")

    # Mount compiled JS/CSS assets
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="frontend_assets",
        )

    # SPA catch-all: 모든 non-API 요청을 index.html로 fallback
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # API/WS 경로는 건드리지 않음 (404를 던져서 기존 핸들러가 처리하게 함)
        if full_path.startswith(("api/", "ws", "openapi.json", "docs", "redoc")):
            raise HTTPException(status_code=404)
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    logger.warning(
        f"⚠️ Frontend build not found at {FRONTEND_DIR}. "
        f"Run 'cd frontend && npm run build' to build the UI."
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.ws_host, port=settings.ws_port)
