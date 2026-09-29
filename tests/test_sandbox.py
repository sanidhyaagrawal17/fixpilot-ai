import pytest
from core.sandbox import CodeSandbox


@pytest.mark.asyncio
async def test_sandbox_successful_execution():
    sandbox = CodeSandbox(timeout=5)
    code = "def add(a, b): return a + b\nassert add(2, 3) == 5\nprint('PASSED')"
    res = await sandbox.execute_code(code)
    assert res.passed is True
    assert res.exit_code == 0
    assert "PASSED" in res.output


@pytest.mark.asyncio
async def test_sandbox_failure_detection():
    sandbox = CodeSandbox(timeout=5)
    code = "assert 1 == 2, 'Value mismatch'"
    res = await sandbox.execute_code(code)
    assert res.passed is False
    assert res.exit_code != 0
    assert "AssertionError" in res.output


@pytest.mark.asyncio
async def test_sandbox_with_test_code_harness():
    sandbox = CodeSandbox(timeout=5)
    solution = "def multiply(x, y): return x * y"
    test_harness = "from solution import multiply\nassert multiply(4, 5) == 20\nprint('HARNESS OK')"
    res = await sandbox.execute_code(code=solution, test_code=test_harness)
    assert res.passed is True
    assert "HARNESS OK" in res.output


@pytest.mark.asyncio
async def test_sandbox_security_gate():
    sandbox = CodeSandbox(timeout=5)
    dangerous_code = "import os\nos.system('format C:')"
    res = await sandbox.execute_code(dangerous_code)
    assert res.passed is False
    assert "Security Gate Failure" in res.output
