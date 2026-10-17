import pytest
from core.sandbox import CodeSandbox


@pytest.mark.asyncio
async def test_ast_security_blocks_dangerous_python_imports():
    sandbox = CodeSandbox()
    
    # 1. Test direct import os
    code_os = "import os\nprint(os.getcwd())"
    safe, reason = sandbox.check_safety(code_os, language="python")
    assert not safe
    assert "os" in reason.lower()

    # 2. Test from subprocess import Popen
    code_sub = "from subprocess import Popen\nPopen(['ls'])"
    safe, reason = sandbox.check_safety(code_sub, language="python")
    assert not safe
    assert "subprocess" in reason.lower()

    # 3. Test eval() call
    code_eval = "x = '1 + 1'\nprint(eval(x))"
    safe, reason = sandbox.check_safety(code_eval, language="python")
    assert not safe
    assert "eval" in reason.lower()


@pytest.mark.asyncio
async def test_pre_sandbox_syntax_gate():
    sandbox = CodeSandbox()
    broken_syntax = "def broken(:\n    pass"
    res = await sandbox.execute_code(code=broken_syntax, language="python")
    assert not res.passed
    assert "Syntax" in res.output
    assert res.duration_ms == 0


@pytest.mark.asyncio
async def test_javascript_sandbox_execution():
    sandbox = CodeSandbox()
    
    # 1. Valid JavaScript execution
    js_code = """function add(a, b) { return a + b; }
console.log('Result:', add(2, 3));
"""
    js_test = """const assert = require('assert');
// Test harness
assert.strictEqual(2 + 3, 5);
console.log('JS PASS');
"""
    res = await sandbox.execute_code(
        code=js_code,
        test_code=js_test,
        filename="solution.js",
        language="javascript"
    )
    assert res.passed
    assert res.exit_code == 0
    assert "JS PASS" in res.output


@pytest.mark.asyncio
async def test_javascript_security_gate_blocks_child_process():
    sandbox = CodeSandbox()
    dangerous_js = "const cp = require('child_process'); cp.execSync('calc');"
    safe, reason = sandbox.check_safety(dangerous_js, language="javascript")
    assert not safe
    assert "child_process" in reason
