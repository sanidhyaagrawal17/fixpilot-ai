import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from tests.scenarios.scenario_index_error import ERROR_TRACEBACK, SOURCE_CODE, TEST_CODE


@pytest.mark.asyncio
async def test_api_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "models" in data


@pytest.mark.asyncio
async def test_api_scenarios_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 4
        assert any("index_error" in sc["id"] for sc in data)


@pytest.mark.asyncio
async def test_api_debug_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "error_traceback": ERROR_TRACEBACK,
            "source_code": SOURCE_CODE,
            "test_code": TEST_CODE,
            "language": "python"
        }
        resp = await ac.post("/api/debug", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["fix"] is not None
        assert "diff" in data["fix"]
