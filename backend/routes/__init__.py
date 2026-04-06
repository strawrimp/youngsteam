from routes.projects import router as projects_router
from routes.agents import router as agents_router
from routes.discussions import router as discussions_router
from routes.votes import router as votes_router

__all__ = [
    "projects_router",
    "agents_router",
    "discussions_router",
    "votes_router",
]
