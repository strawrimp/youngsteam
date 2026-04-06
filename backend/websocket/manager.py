from fastapi import WebSocket
from typing import List, Dict, Set
import logging
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 연결 관리자"""

    def __init__(self):
        # 활성 연결 목록
        self.active_connections: List[WebSocket] = []
        # 프로젝트별 구독자 관리 {project_id: set(websocket)}
        self.project_subscribers: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """새 WebSocket 연결 수락"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """WebSocket 연결 해제"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # 모든 프로젝트 구독에서 제거
        for project_id, subscribers in self.project_subscribers.items():
            if websocket in subscribers:
                subscribers.remove(websocket)
                logger.info(f"WebSocket unsubscribed from project {project_id}")

        logger.info(
            f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """특정 클라이언트에게 메시지 전송"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: dict):
        """모든 연결된 클라이언트에게 브로드캐스트"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)

        # 연결이 끊긴 클라이언트 정리
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_project(self, project_id: str, message: dict):
        """특정 프로젝트를 구독한 클라이언트에게 브로드캐스트"""
        if project_id not in self.project_subscribers:
            return

        subscribers = self.project_subscribers[project_id].copy()
        disconnected = []

        for connection in subscribers:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to project {project_id}: {e}")
                disconnected.append(connection)

        # 연결이 끊긴 클라이언트 정리
        for conn in disconnected:
            self.disconnect(conn)

    async def subscribe_to_project(self, websocket: WebSocket, project_id: str):
        """프로젝트 구독"""
        if project_id not in self.project_subscribers:
            self.project_subscribers[project_id] = set()

        self.project_subscribers[project_id].add(websocket)
        logger.info(f"WebSocket subscribed to project {project_id}")

    async def unsubscribe_from_project(self, websocket: WebSocket, project_id: str):
        """프로젝트 구독 해제"""
        if project_id in self.project_subscribers:
            if websocket in self.project_subscribers[project_id]:
                self.project_subscribers[project_id].remove(websocket)
                logger.info(f"WebSocket unsubscribed from project {project_id}")
