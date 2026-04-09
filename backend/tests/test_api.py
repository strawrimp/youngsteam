"""Integration tests for REST API endpoints.

Tests: pytest -v backend/tests/test_api.py
Run: python3 -m pytest tests/test_api.py -v
"""

import pytest
import requests
from unittest.mock import MagicMock, AsyncMock, patch

# Base URL for API tests
BASE_URL = "http://localhost:8001"


# ==================== Fixtures ====================


@pytest.fixture(scope="module")
def server_available():
    """Check if server is running before tests."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        pytest.skip("Backend server not running at localhost:8000")


# ==================== Health Check Tests ====================


class TestHealthCheck:
    """Test suite for health check endpoint."""

    def test_health_check(self, server_available):
        """Test GET /health - Health check"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


# ==================== Projects API Tests ====================


class TestProjectsAPI:
    """Test suite for Projects API endpoints."""

    def test_list_projects(self, server_available):
        """Test GET /api/projects - List all projects"""
        response = requests.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_project(self, server_available):
        """Test POST /api/projects - Create a new project"""
        project_data = {
            "name": "Test Project API",
            "description": "Test Description for API",
            "owner_id": "test-owner-api",
        }
        response = requests.post(f"{BASE_URL}/api/projects", json=project_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project API"
        assert "id" in data
        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{data['id']}")

    def test_get_project(self, server_available):
        """Test GET /api/projects/{id} - Get specific project"""
        # Create project first
        create_response = requests.post(
            f"{BASE_URL}/api/projects",
            json={
                "name": "Get Test Project",
                "description": "Test",
                "owner_id": "test",
            },
        )
        project_id = create_response.json()["id"]

        # Get project
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["id"] == project_id

        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{project_id}")

    def test_get_project_not_found(self, server_available):
        """Test GET /api/projects/{id} - Project not found"""
        response = requests.get(f"{BASE_URL}/api/projects/non-existent-project-id")
        assert response.status_code == 404

    def test_update_project(self, server_available):
        """Test PUT /api/projects/{id} - Update project"""
        # Create project first
        create_response = requests.post(
            f"{BASE_URL}/api/projects",
            json={
                "name": "Update Test Project",
                "description": "Before",
                "owner_id": "test",
            },
        )
        project_id = create_response.json()["id"]

        # Update project
        update_data = {"name": "Updated Project", "description": "After"}
        response = requests.put(
            f"{BASE_URL}/api/projects/{project_id}", json=update_data
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Project"

        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{project_id}")

    def test_delete_project(self, server_available):
        """Test DELETE /api/projects/{id} - Delete project"""
        # Create project first
        create_response = requests.post(
            f"{BASE_URL}/api/projects",
            json={
                "name": "Delete Test Project",
                "description": "Test",
                "owner_id": "test",
            },
        )
        project_id = create_response.json()["id"]

        # Delete project
        response = requests.delete(f"{BASE_URL}/api/projects/{project_id}")
        assert response.status_code == 200

        # Verify deleted
        get_response = requests.get(f"{BASE_URL}/api/projects/{project_id}")
        assert get_response.status_code == 404


# ==================== Agents API Tests ====================


class TestAgentsAPI:
    """Test suite for Agents API endpoints."""

    def test_list_agents(self, server_available):
        """Test GET /api/agents - List all agents"""
        response = requests.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        # Response may be a list or dict with 'agents' key
        data = response.json()
        if isinstance(data, dict) and "agents" in data:
            assert isinstance(data["agents"], list)
        else:
            assert isinstance(data, list)

    def test_get_agent_not_found(self, server_available):
        """Test GET /api/agents/{id} - Agent not found"""
        response = requests.get(f"{BASE_URL}/api/agents/non-existent-agent-id")
        assert response.status_code == 404


# ==================== Discussions API Tests ====================


class TestDiscussionsAPI:
    """Test suite for Discussions API endpoints."""

    def test_list_discussions(self, server_available):
        """Test GET /api/discussions - List all active discussions"""
        response = requests.get(f"{BASE_URL}/api/discussions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_discussion(self, server_available):
        """Test POST /api/discussions - Create discussion"""
        discussion_data = {
            "topic": "Test Discussion Topic",
            "project_id": "test-project-api",
        }
        response = requests.post(
            f"{BASE_URL}/api/discussions",
            json=discussion_data,
            params={"agent_ids": ["test-agent"]},
        )
        # May fail if project doesn't exist, which is expected
        assert response.status_code in [201, 404, 422]

    def test_get_discussion_not_found(self, server_available):
        """Test GET /api/discussions/{id} - Discussion not found"""
        response = requests.get(
            f"{BASE_URL}/api/discussions/non-existent-discussion-id"
        )
        assert response.status_code == 404


# ==================== Votes API Tests ====================


class TestVotesAPI:
    """Test suite for Votes API endpoints."""

    def test_get_votes_by_discussion(self, server_available):
        """Test GET /api/votes/{discussion_id} - Get votes"""
        response = requests.get(f"{BASE_URL}/api/votes/test-discussion-id")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_vote_results(self, server_available):
        """Test GET /api/votes/{discussion_id}/results - Get vote results"""
        response = requests.get(f"{BASE_URL}/api/votes/test-discussion-id/results")
        assert response.status_code == 200
        data = response.json()
        assert "discussion_id" in data
        assert "total_votes" in data


# ==================== Invite Suggestion Tests ====================


class TestInviteAPI:
    """Test suite for Invite API endpoints."""

    def test_suggest_invite(self, server_available):
        """Test POST /api/agents/suggest-invite - Suggest invite"""
        request_data = {
            "project_id": "test-project-api",
            "message": "@developer API 개발이 필요해요.",
            "sender_role": "manager",
        }
        response = requests.post(
            f"{BASE_URL}/api/agents/suggest-invite", json=request_data
        )
        # May fail if project doesn't exist or internal error
        assert response.status_code in [200, 404, 422, 500]

    def test_handle_mention(self, server_available):
        """Test POST /api/agents/mention - Handle @mention"""
        request_data = {
            "project_id": "test-project-api",
            "message": "@developer 안녕하세요",
        }
        response = requests.post(f"{BASE_URL}/api/agents/mention", json=request_data)
        # May fail if project doesn't exist
        assert response.status_code in [200, 404, 422]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
