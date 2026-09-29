import pytest
from core.agent import DebugAgent
from core.models import DebugRequest
from tests.scenarios.scenario_index_error import ERROR_TRACEBACK, SOURCE_CODE, TEST_CODE


@pytest.mark.asyncio
async def test_agent_end_to_end_remediation():
    agent = DebugAgent()
    req = DebugRequest(
        error_traceback=ERROR_TRACEBACK,
        source_code=SOURCE_CODE,
        test_code=TEST_CODE,
        language="python"
    )

    response = await agent.run(req)

    assert response is not None
    assert response.classification is not None
    assert response.fix is not None
    assert response.test_result is not None
    assert len(response.steps) >= 4
    assert response.success is True
    assert "len(items) - 1" in response.fix.fixed_code
