import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.mark.anyio
async def test_review_code_success(async_client):
    """Test successful code review."""
    response = await async_client.post(
        "/review",
        json={
            "assignment_description": "Review this code.",
            "github_repo_url": "https://github.com/NikitaVishnyak/string_processing",  # Заміна на ваш реальний URL
            "candidate_level": "Junior"
        }
    )
    assert response.status_code == 200  # Перевірка статусу

@pytest.mark.anyio
async def test_review_code_invalid_repo(async_client):
    """Test code review with invalid GitHub repo URL."""
    response = await async_client.post(
        "/review",
        json={
            "assignment_description": "Review this code.",
            "github_repo_url": "https://invalid.url",
            "candidate_level": "Junior"
        }
    )
    assert response.status_code == 404

@pytest.mark.anyio
async def test_review_code_invalid_level(async_client):
    """Test code review with invalid candidate level."""
    response = await async_client.post(
        "/review",
        json={
            "assignment_description": "Review this code.",
            "github_repo_url": "https://github.com/NikitaVishnyak/string_processing",  # Заміна на ваш реальний URL
            "candidate_level": "InvalidLevel"
        }
    )
    assert response.status_code == 422
