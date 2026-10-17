import importlib
import pytest
from core.sandbox import CodeSandbox
from core.fixer import compute_unified_diff

SCENARIOS = [
    "scenario_index_error",
    "scenario_type_error",
    "scenario_import_error",
    "scenario_logic_bug",
    "scenario_js_type_error",
    "scenario_modern_api_migration",
    "scenario_self_healing_cascade"
]


@pytest.mark.parametrize("scenario_name", SCENARIOS)
def test_scenario_structure_and_diff(scenario_name):
    """Verifies each scenario module contains valid metadata and computes a clean diff."""
    mod = importlib.import_module(f"tests.scenarios.{scenario_name}")
    assert hasattr(mod, "DESCRIPTION")
    assert hasattr(mod, "SOURCE_CODE")
    assert hasattr(mod, "ERROR_TRACEBACK")
    assert hasattr(mod, "TEST_CODE")
    assert len(mod.DESCRIPTION) > 5
    assert len(mod.SOURCE_CODE) > 5
    assert len(mod.ERROR_TRACEBACK) > 5
    assert len(mod.TEST_CODE) > 5

    # Verify unified diff computation
    diff = compute_unified_diff(mod.SOURCE_CODE, mod.SOURCE_CODE + "\n# fix\n")
    assert "---" in diff and "+++" in diff


@pytest.mark.asyncio
async def test_scenario_modern_api_migration_sandbox_reproduction_and_fix():
    """Confirms the Tavily spotlight scenario reproduces PydanticImportError and passes when patched."""
    from tests.scenarios.scenario_modern_api_migration import SOURCE_CODE, TEST_CODE
    sandbox = CodeSandbox()

    # Initial code must fail due to BaseSettings moved to pydantic-settings
    res_initial = await sandbox.execute_code(SOURCE_CODE, test_code=TEST_CODE, language="python")
    assert res_initial.passed is False
    assert res_initial.exit_code != 0
    assert "PydanticImportError" in res_initial.output or "BaseSettings" in res_initial.output

    # Patched code with modern import must pass
    fixed_code = SOURCE_CODE.replace(
        "from pydantic import BaseModel, BaseSettings",
        "from pydantic import BaseModel\nfrom pydantic_settings import BaseSettings"
    )
    res_fixed = await sandbox.execute_code(fixed_code, test_code=TEST_CODE, language="python")
    assert res_fixed.passed is True
    assert res_fixed.exit_code == 0
    assert "ALL TESTS PASSED" in res_fixed.output
    assert res_fixed.duration_ms < 1500


@pytest.mark.asyncio
async def test_scenario_js_type_error_sandbox_reproduction_and_fix():
    """Confirms the JavaScript scenario reproduces unhandled TypeError and passes when patched."""
    from tests.scenarios.scenario_js_type_error import SOURCE_CODE, TEST_CODE
    sandbox = CodeSandbox()

    # Initial JS code fails with TypeError on null / undefined user
    res_initial = await sandbox.execute_code(SOURCE_CODE, test_code=TEST_CODE, language="javascript")
    assert res_initial.passed is False
    assert res_initial.exit_code != 0

    # Patched code with nullish guard passes
    fixed_code = """function getUserDisplayName(user) {
    if (!user || !user.name) {
        return '';
    }
    return user.name.toUpperCase();
}

module.exports = { getUserDisplayName };
"""
    res_fixed = await sandbox.execute_code(fixed_code, test_code=TEST_CODE, language="javascript")
    assert res_fixed.passed is True
    assert res_fixed.exit_code == 0
    assert "ALL JS TESTS PASSED" in res_fixed.output
    assert res_fixed.duration_ms < 1500


@pytest.mark.asyncio
async def test_scenario_self_healing_cascade_multi_attempt_sandbox():
    """Confirms the self-healing scenario exposes KeyError initially, ZeroDivisionError on Attempt 1, and passes on Attempt 2."""
    from tests.scenarios.scenario_self_healing_cascade import SOURCE_CODE, TEST_CODE
    sandbox = CodeSandbox()

    # Initial code fails with KeyError on missing key
    res_initial = await sandbox.execute_code(SOURCE_CODE, test_code=TEST_CODE, language="python")
    assert res_initial.passed is False
    assert res_initial.exit_code != 0

    # Attempt 1 partial fix (fixes KeyError only, leaves empty collection unhandled)
    attempt1_patch = (
        "def calculate_metrics_batch(payload):\n"
        "    items = (payload.get('metrics') or payload.get('telemetry', [])) if payload else []\n"
        "    total_score = sum(item.get('score', 0) for item in items)\n"
        "    average = total_score / len(items)\n"
        "    return {'count': len(items), 'average': round(average, 2)}\n"
    )
    res_att1 = await sandbox.execute_code(attempt1_patch, test_code=TEST_CODE, language="python")
    assert res_att1.passed is False
    assert res_att1.exit_code != 0
    assert "ZeroDivisionError" in res_att1.output

    # Attempt 2 complete patch (fixes both KeyError and ZeroDivisionError)
    attempt2_patch = (
        "def calculate_metrics_batch(payload):\n"
        "    if not payload:\n"
        "        return {'count': 0, 'average': 0.0}\n"
        "    items = payload.get('metrics') or payload.get('telemetry', [])\n"
        "    if not items:\n"
        "        return {'count': 0, 'average': 0.0}\n"
        "    total_score = sum(item.get('score', 0) for item in items)\n"
        "    average = total_score / len(items)\n"
        "    return {'count': len(items), 'average': round(average, 2)}\n"
    )
    res_att2 = await sandbox.execute_code(attempt2_patch, test_code=TEST_CODE, language="python")
    assert res_att2.passed is True
    assert res_att2.exit_code == 0
    assert "ALL TESTS PASSED" in res_att2.output

