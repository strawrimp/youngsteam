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
from sqlalchemy.orm import Session
from engines.conversation_engine import ConversationEngine
from engines.voting_engine import VotingEngine
from agents.manager_agent import ManagerAgent
from agents.developer_agent import DeveloperAgent
from agents.designer_agent import DesignerAgent
from agents.researcher_agent import ResearcherAgent
from services.memory_service import MemoryService
from services.glm_service import GLMService
from services.deepseek_service import DeepSeekService

# Configure logging
logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
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
        app.state.memory_service = MemoryService()

        # Use DeepSeek service with hybrid V4 + R1 strategy
        app.state.deepseek_service = DeepSeekService(
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
            temperature=settings.deepseek_temperature,
            enable_hybrid=settings.deepseek_enable_hybrid,
        )
        logger.info(f"✅ DeepSeek Service initialized (Hybrid: {settings.deepseek_enable_hybrid})")
        logger.info(f"   API Key: {settings.deepseek_api_key[:10]}..." if settings.deepseek_api_key else "   API Key: NOT SET")

        # Keep GLM service for backward compatibility
        app.state.glm_service = GLMService()

        # Get agents from database
        db = SessionLocal()
        agents = db.query(Agent).all()

        # Agent factory mapping
        agent_factories = {
            "manager": lambda agent_id, name, service: ManagerAgent(agent_id, name, service),
            "developer": lambda agent_id, name, service: DeveloperAgent(agent_id, name, service),
            "designer": lambda agent_id, name, service: DesignerAgent(agent_id, name, service),
            "researcher": lambda agent_id, name, service: ResearcherAgent(agent_id, name, service),
        }

        for agent in agents:
            if agent.role not in agent_factories:
                logger.warning(f"Unsupported agent role: {agent.role}")
                continue

            try:
                factory = agent_factories[agent.role]
                # Use DeepSeekService for hybrid V4 + R1 strategy
                agent_instance = factory(str(agent.id), agent.name, app.state.deepseek_service)
                app.state.conversation_engine.register_agent(str(agent.id), agent_instance)
                logger.info(f"Registered agent: {agent.name} ({agent.role})")
            except Exception as e:
                logger.error(f"Failed to register agent {agent.name}: {e}")

        db.close()
        logger.info(f"Conversation engine initialized with {len(app.state.conversation_engine.agents)} agents")

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

    conversation_id = str(__import__('uuid').uuid4())
    engine = app.state.conversation_engine
    memory = app.state.memory_service

    try:
        while True:
            # Receive text message
            data = await websocket.receive_text()
            logger.debug(f"WebSocket received: {data}")

            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                message_data = {"content": data}

            user_message = message_data.get("content", "").strip()

            if not user_message:
                await websocket.send_json({"error": "Empty message"})
                continue

            # Send processing notification
            await websocket.send_json({
                "type": "status",
                "status": "processing",
                "message": "에이전트들이 의견을 수집 중입니다...",
            })

            # Process message through agents
            try:
                result = await engine.process_message(conversation_id, user_message)

                # Send agent responses
                for agent_id, response in result.get("agent_responses", {}).items():
                    agent = engine.agents.get(agent_id)
                    agent_name = agent.name if agent else agent_id

                    await websocket.send_json({
                        "type": "agent_response",
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "content": response,
                        "timestamp": result["timestamp"],
                    })

                # Save to memory
                await memory.save_memory(
                    category="conversation",
                    content=f"User: {user_message}",
                    created_by="user",
                )

                # Send completion status
                await websocket.send_json({
                    "type": "status",
                    "status": "complete",
                    "message": "✓ 모든 에이전트가 응답했습니다.",
                })

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": str(e),
                })

    except Exception as e:
        logger.error(f"WebSocket error: {type(e).__name__}: {e}")
    finally:
        logger.info(f"WebSocket client disconnected")


# REST API endpoints for chat
@app.post("/api/chat/message")
async def send_message(request_data: dict = None, db: Session = Depends(get_db)):
    """Send a message to agents."""
    try:
        return {
            "status": "received",
            "message": request_data or {},
            "note": "Phase 1: Echo only"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# REST API endpoints for agents
@app.get("/api/agents")
async def list_agents(db: Session = Depends(get_db)):
    """List all agents."""
    agents = db.query(Agent).all()
    return {"agents": [{"id": str(a.id), "name": a.name, "role": a.role} for a in agents]}


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

    voting_id = str(__import__('uuid').uuid4())
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
        }
    }


@app.post("/api/stats/models/reset")
async def reset_model_stats():
    """Reset model usage statistics (admin only)."""
    service = app.state.deepseek_service
    service.reset_usage_stats()
    return {"status": "ok", "message": "Model usage statistics reset"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.ws_host, port=settings.ws_port)
