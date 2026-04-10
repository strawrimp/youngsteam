"""Main FastAPI application for AI Virtual Company backend."""

from contextlib import asynccontextmanager
from typing import Optional
import json
import logging
import asyncio

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, init_db, SessionLocal
from models import Agent, Conversation, Message, TeamSettings
from engines.conversation_engine import ConversationEngine
from engines.voting_engine import VotingEngine
from engines.debate_engine import DebateEngine
from agents.agent_message_broker import AgentMessageBroker
from services.memory_service import MemoryService
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
    try:
        init_db()
        logger.info("Database initialized")

        # Initialize engines and services
        app.state.conversation_engine = ConversationEngine()
        app.state.voting_engine = VotingEngine()
        app.state.debate_engine = DebateEngine()
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
            f"   API Key: {settings.deepseek_api_key[:10]}..."
            if settings.deepseek_api_key
            else "   API Key: NOT SET"
        )

        # Inject DeepSeekService into ConversationEngine for Tool Use
        app.state.conversation_engine.set_deepseek_service(app.state.deepseek_service)
        logger.info("✅ DeepSeekService injected into ConversationEngine")

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
        agents = db.query(Agent).all()

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
                logger.info(f"Registered agent: {agent.name} ({agent.role})")
            except Exception as e:
                logger.error(f"Failed to register agent {agent.name}: {e}")

        db.close()
        logger.info(
            f"Conversation engine initialized with {len(app.state.conversation_engine.agents)} agents"
        )

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
    allow_origins=["*"],  # Localhost during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

                    if not conversation_id:
                        await app.state.ws_manager.send_personal_message(
                            {"error": "Conversation ID required"}, websocket
                        )
                        continue

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
                    try:
                        logger.info(
                            "About to call engine.process_message with Tool Use"
                        )
                        result = await engine.process_message(
                            conversation_id,
                            user_message,
                            step_callback=lambda aid, aname, step: (
                                asyncio.ensure_future(on_agent_step(aid, aname, step))
                            ),
                        )
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
                                    "content": response,
                                    "timestamp": result["timestamp"],
                                }
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
    """List all agents."""
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.ws_host, port=settings.ws_port)
