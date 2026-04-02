"""FastAPI application for AI Virtual Company."""

from fastapi import FastAPI, WebSocket, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
from contextlib import asynccontextmanager

from config import settings
from database import init_db, get_db
from models.agent import Agent
from models.conversation import Conversation
from models.message import Message
from sqlalchemy.orm import Session

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
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
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
    """WebSocket endpoint for real-time communication."""
    await websocket.accept()
    logger.info(f"WebSocket client connected: {websocket.client}")

    try:
        while True:
            # Receive text message
            data = await websocket.receive_text()
            logger.debug(f"WebSocket received: {data}")

            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                message_data = {"content": data}

            # Echo test for Phase 1
            response = {
                "type": "echo",
                "content": f"Echo: {message_data.get('content', 'no content')}",
                "timestamp": str(__import__('datetime').datetime.now()),
            }

            await websocket.send_json(response)
            logger.debug(f"WebSocket sent: {response}")

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
