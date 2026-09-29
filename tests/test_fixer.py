import pytest
from core.fixer import CodeFixer, compute_unified_diff
from core.models import AnalysisResult


def test_unified_diff_generation():
    orig = "def fn():\n    return 1\n"
    fixed = "def fn():\n    return 2\n"
    diff = compute_unified_diff(orig, fixed, filename="fn.py")
    assert "--- a/fn.py" in diff
    assert "+++ b/fn.py" in diff
    assert "-    return 1" in diff
    assert "+    return 2" in diff


@pytest.mark.asyncio
async def test_code_fixer_heuristic_generation():
    fixer = CodeFixer()
    analysis = AnalysisResult(
        root_cause="Off by one list access",
        explanation="Attempted to access len(items)",
        affected_code_snippet="items[len(items)]",
        suggested_approach="Use items[len(items) - 1]"
    )
    broken_code = "def get_last(items):\n    return items[len(items)]\n"
    res = await fixer.generate_fix(analysis, broken_code)
    assert "len(items) - 1" in res.fixed_code
    assert res.diff != ""
