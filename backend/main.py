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
from agents.manager_agent import ManagerAgent
from agents.developer_agent import DeveloperAgent
from services.memory_service import MemoryService
from services.glm_service import GLMService

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

        # Initialize conversation engine and agents
        app.state.conversation_engine = ConversationEngine()
        app.state.memory_service = MemoryService()
        app.state.glm_service = GLMService()

        # Get agents from database
        db = SessionLocal()
        agents = db.query(Agent).all()

        for agent in agents:
            if agent.role == "manager":
                agent_instance = ManagerAgent(
                    str(agent.id),
                    agent.name,
                    app.state.glm_service,
                )
            elif agent.role == "developer":
                agent_instance = DeveloperAgent(
                    str(agent.id),
                    agent.name,
                    app.state.glm_service,
                )
            else:
                logger.warning(f"Unsupported agent role: {agent.role}")
                continue

            app.state.conversation_engine.register_agent(str(agent.id), agent_instance)
            logger.info(f"Registered agent: {agent.name} ({agent.role})")

        db.close()
        logger.info("Conversation engine initialized with agents")

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.ws_host, port=settings.ws_port)
