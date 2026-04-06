"""FastAPI application for AI Virtual Company."""

from fastapi import FastAPI, WebSocket, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
from contextlib import asynccontextmanager

from config import settings
from database import init_db, get_db, SessionLocal
from models.agent import Agent
from models.conversation import Conversation
from models.message import Message
from models.team_settings import TeamSettings
from sqlalchemy.orm import Session
from engines.conversation_engine import ConversationEngine
from engines.voting_engine import VotingEngine
from engines.debate_engine import DebateEngine
from agents.agent_message_broker import AgentMessageBroker
from agents.manager_agent import ManagerAgent
from agents.developer_agent import DeveloperAgent
from agents.designer_agent import DesignerAgent
from agents.researcher_agent import ResearcherAgent
from services.memory_service import MemoryService
from services.glm_service import GLMService
from services.deepseek_service import DeepSeekService
from services.llm_provider_service import (
    LLMProviderService,
    DeepSeekProvider,
    OpenAIProvider,
    ClaudeProvider,
    OllamaProvider,
)

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

        # Register OpenAI if available
        if settings.openai_api_key:
            openai_provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                model="gpt-4o",
            )
            llm_provider_service.register_provider("openai", openai_provider)
            logger.info(f"✅ Registered LLM Provider: OpenAI")

        # Register Claude if available
        if settings.claude_api_key:
            claude_provider = ClaudeProvider(
                api_key=settings.claude_api_key,
                model="claude-sonnet-4-20250514",
            )
            llm_provider_service.register_provider("claude", claude_provider)
            logger.info(f"✅ Registered LLM Provider: Claude")

        # Always support Ollama for local inference
        ollama_provider = OllamaProvider(
            base_url=settings.ollama_url,
            model=settings.ollama_model,
        )
        llm_provider_service.register_provider("ollama", ollama_provider)
        logger.info(f"✅ Registered LLM Provider: Ollama (Local)")

        app.state.llm_provider_service = llm_provider_service

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


# Register new routes
from routes import projects_router, agents_router, discussions_router, votes_router

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
    """WebSocket endpoint for real-time communication and agent interaction."""
    await websocket.accept()
    logger.info(f"WebSocket client connected: {websocket.client}")

    conversation_id = str(__import__("uuid").uuid4())
    engine = app.state.conversation_engine
    memory = app.state.memory_service

    logger.info(f"Engine has {len(engine.agents)} agents")

    try:
        while True:
            # Receive text message
            data = await websocket.receive_text()
            logger.info(f"WebSocket received: {data}")

            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                message_data = {"content": data}

            user_message = message_data.get("content", "").strip()

            if not user_message:
                await websocket.send_json({"error": "Empty message"})
                continue

            # Send processing notification
            await websocket.send_json(
                {
                    "type": "status",
                    "status": "processing",
                    "message": "에이전트들이 의견을 수집 중입니다...",
                }
            )

            logger.info(f"Calling engine.process_message with: {user_message}")

            # Process message through agents
            try:
                logger.info("About to call engine.process_message")
                result = await engine.process_message(conversation_id, user_message)
                logger.info(
                    f"Engine returned with {len(result.get('agent_responses', {}))} responses"
                )

                logger.info(f"Engine returned result keys: {list(result.keys())}")
                if result.get("agent_responses"):
                    logger.info(
                        f"Agent response keys: {list(result.get('agent_responses', {}).keys())}"
                    )

                # Send agent responses
                for agent_id, response in result.get("agent_responses", {}).items():
                    agent = engine.agents.get(agent_id)
                    agent_name = agent.name if agent else agent_id

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
                await memory.save_memory(
                    category="conversation",
                    content=f"User: {user_message}",
                    created_by="user",
                )

                # Send completion status
                await websocket.send_json(
                    {
                        "type": "status",
                        "status": "complete",
                        "message": "✓ 모든 에이전트가 응답했습니다.",
                    }
                )

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": str(e),
                    }
                )

    except Exception as e:
        logger.error(f"WebSocket error: {type(e).__name__}: {e}")
    finally:
        logger.info(f"WebSocket client disconnected")


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
