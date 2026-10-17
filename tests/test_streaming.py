import json
import pytest
from core.agent import DebugAgent
from core.models import DebugRequest


@pytest.mark.asyncio
async def test_streaming_event_sequence_and_queue_drain():
    agent = DebugAgent()
    request = DebugRequest(
        error_traceback="""Traceback (most recent call last):
  File "main.py", line 2, in <module>
    item = items[len(items)]
IndexError: list index out of range""",
        source_code="def get_item(items):\n    return items[len(items)]\n",
        test_code="from solution import get_item\nassert get_item([10, 20]) == 20\n",
        language="python"
    )

    events_received = []
    tiers_started = []
    tiers_completed = []

    async for raw_sse in agent.run_streaming(request):
        # Ignore keep-alive comments
        if raw_sse.startswith(":"):
            continue

        assert raw_sse.startswith("data: ")
        json_payload = raw_sse.replace("data: ", "").strip()
        parsed = json.loads(json_payload)
        ev_name = parsed.get("event")
        events_received.append(ev_name)

        if ev_name == "tier_start":
            tiers_started.append(parsed["data"]["tier"])
        elif ev_name == "tier_complete":
            tiers_completed.append(parsed["data"]["tier"])

    # 1. Verify required event types were received
    assert "tier_start" in events_received
    assert "tier_complete" in events_received
    assert "pipeline_complete" in events_received
    assert "step" in events_received
    assert "complete" in events_received

    # 2. Verify all 5 core tiers executed
    assert "classify" in tiers_started
    assert "classify" in tiers_completed
    assert "ground" in tiers_started
    assert "ground" in tiers_completed
    assert "diagnose" in tiers_started
    assert "diagnose" in tiers_completed
    assert "synthesize" in tiers_started
    assert "synthesize" in tiers_completed
    assert "verify" in tiers_started
    assert "verify" in tiers_completed
