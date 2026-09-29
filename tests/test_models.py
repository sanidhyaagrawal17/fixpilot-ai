import pytest
from core.models import (
    ErrorSeverity,
    AgentStatus,
    DebugRequest,
    ClassificationResult,
    AnalysisResult,
    FixResult,
    TestResult,
    DebugResponse
)


def test_models_validation():
    req = DebugRequest(
        error_traceback="IndexError: list index out of range",
        source_code="def fn(): pass",
        language="python"
    )
    assert req.language == "python"
    assert "IndexError" in req.error_traceback

    cls_res = ClassificationResult(
        error_type=ErrorSeverity.TYPE,
        error_message="IndexError: list index out of range",
        affected_line=3
    )
    assert cls_res.error_type == ErrorSeverity.TYPE

    fix_res = FixResult(
        original_code="bad",
        fixed_code="good",
        diff="@@ -1 +1 @@",
        explanation="fixed",
        changes_summary=["changed line 1"]
    )
    assert len(fix_res.changes_summary) == 1

    resp = DebugResponse(
        success=True,
        attempts=1,
        classification=cls_res,
        fix=fix_res,
        total_duration_ms=450
    )
    assert resp.success is True
    assert resp.attempts == 1
