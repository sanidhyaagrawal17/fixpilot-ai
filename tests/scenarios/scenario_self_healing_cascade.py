"""Scenario 7: Multi-Attempt Self-Healing Cascade (KeyError ➔ ZeroDivisionError)
Showcases FixPilot's autonomous closed-loop state machine and Adaptive Tavily Delta Search:
- Attempt 1: Resolves the initial KeyError crash on dictionary property access.
- Sandbox Trigger: Uncovers a hidden ZeroDivisionError on empty batches during edge-case test assertion.
- Attempt 2: Triggers an Adaptive Tavily Delta Search for the new traceback, updates Nemotron Ultra reasoning,
  and synthesizes a 100% verified zero-safe calculation patch.
"""

DESCRIPTION = "Self-Healing Cascade: Multi-attempt KeyError repair revealing hidden ZeroDivisionError"

SOURCE_CODE = """def calculate_metrics_batch(payload):
    # Bug Layer 1: KeyError when 'metrics' key is missing in payload
    items = payload["metrics"]

    # Bug Layer 2: Hidden ZeroDivisionError on empty batch ([] or None)
    total_score = sum(item["score"] for item in items)
    average = total_score / len(items)

    return {
        "count": len(items),
        "average": round(average, 2)
    }
"""

ERROR_TRACEBACK = """Traceback (most recent call last):
  File "solution.py", line 3, in calculate_metrics_batch
    items = payload["metrics"]
KeyError: 'metrics'
"""

TEST_CODE = """from solution import calculate_metrics_batch

def test_metrics_suite():
    # Test 1: Standard populated batch
    res1 = calculate_metrics_batch({"metrics": [{"score": 80}, {"score": 100}]})
    assert res1["count"] == 2
    assert res1["average"] == 90.0

    # Test 2: Fallback key access
    res2 = calculate_metrics_batch({"telemetry": [{"score": 50}]})
    assert res2["count"] == 1
    assert res2["average"] == 50.0

    # Test 3: Edge Case - Empty batch (exposes hidden ZeroDivisionError in Attempt 1)
    res_empty = calculate_metrics_batch({"metrics": []})
    assert res_empty["count"] == 0
    assert res_empty["average"] == 0.0

    # Test 4: Edge Case - None / empty payload dict
    res_none = calculate_metrics_batch({})
    assert res_none["count"] == 0
    assert res_none["average"] == 0.0

    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_metrics_suite()
"""
