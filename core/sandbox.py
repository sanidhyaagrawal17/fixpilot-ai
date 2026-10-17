import ast
import asyncio
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

from core.config import settings
from core.models import TestResult

logger = logging.getLogger("fixpilot.sandbox")

DANGEROUS_PATTERNS_PY = [
    r"os\.system\(",
    r"shutil\.rmtree\(",
    r"format\s+[a-zA-Z]:",
    r"mkfs",
    r":\(\)\{\s*:\|\:&\s*\};:",
    r"subprocess\.(?:Popen|call|run)\(.*(?:rm\s+-rf|del\s+/f)",
    r"ctypes\.windll",
]

DANGEROUS_MODULES_PY = {
    "os", "subprocess", "socket", "shutil", "sys", "ctypes", "pty", "commands"
}

DANGEROUS_PATTERNS_JS = [
    r"child_process",
    r"fs\.(?:rmSync|rmdirSync|unlinkSync)",
    r"process\.kill\(",
    r"require\(['\"](?:child_process|net|dgram|cluster)['\"]\)",
    r"import\s+.*from\s+['\"](?:child_process|net|dgram|cluster)['\"]",
]


class SecurityASTVisitor(ast.NodeVisitor):
    """Deep AST static analysis gate inspecting imports and execution calls in Python."""

    def __init__(self):
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            root_mod = alias.name.split('.')[0]
            if root_mod in DANGEROUS_MODULES_PY:
                self.violations.append(f"Prohibited module import: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            root_mod = node.module.split('.')[0]
            if root_mod in DANGEROUS_MODULES_PY:
                self.violations.append(f"Prohibited from-import of restricted module: '{node.module}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Detect builtins: eval, exec, __import__
        if isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec", "__import__"):
                self.violations.append(f"Prohibited execution call: '{node.func.id}()'")
        elif isinstance(node.func, ast.Attribute):
            # Detect os.system, subprocess.run etc.
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id in ("os", "posix") and node.func.attr in ("system", "popen", "spawn"):
                    self.violations.append(f"Prohibited execution call: '{node.func.value.id}.{node.func.attr}()'")
        self.generic_visit(node)


class CodeSandbox:
    """Isolated execution sandbox validating synthesized code fixes across Python and JavaScript."""

    def __init__(self, timeout: int = settings.SANDBOX_TIMEOUT):
        self.timeout = timeout
        self.python_bin = sys.executable
        self.node_bin = shutil.which("node") or "node"

    def check_syntax(self, code: str, language: str = "python") -> Tuple[bool, Optional[str]]:
        """Pre-sandbox fast syntax validation gate."""
        is_js = language.lower() in ("javascript", "typescript", "js", "ts")
        if not is_js:
            try:
                ast.parse(code)
                return True, None
            except SyntaxError as e:
                return False, f"SyntaxError at line {e.lineno}: {e.msg}"
        else:
            # For JS, check syntax using node --check via stdin
            if shutil.which("node"):
                try:
                    res = subprocess.run(
                        ["node", "--check"],
                        input=code,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if res.returncode != 0:
                        err_line = res.stderr.splitlines()[0] if res.stderr else "Syntax check failed"
                        return False, f"JS SyntaxError: {err_line}"
                except Exception:
                    pass
        return True, None

    def check_safety(self, code: str, language: str = "python") -> Tuple[bool, Optional[str]]:
        """Dual-layer security gate: AST static analysis + regex patterns."""
        is_js = language.lower() in ("javascript", "typescript", "js", "ts")

        if is_js:
            for pattern in DANGEROUS_PATTERNS_JS:
                if re.search(pattern, code, re.IGNORECASE):
                    return False, f"Prohibited dangerous JavaScript API pattern detected: {pattern}"
            return True, None

        # 1. Backward-compatible regex check
        for pattern in DANGEROUS_PATTERNS_PY:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Prohibited dangerous execution pattern detected: {pattern}"

        # 2. Hardened AST Static Analysis check
        try:
            tree = ast.parse(code)
            visitor = SecurityASTVisitor()
            visitor.visit(tree)
            if visitor.violations:
                return False, f"AST Security Gate Failure: {'; '.join(visitor.violations)}"
        except SyntaxError:
            # Syntax errors are caught by pre-flight syntax gate
            pass

        return True, None

    async def execute_code(
        self,
        code: str,
        test_code: Optional[str] = None,
        test_command: Optional[str] = None,
        filename: Optional[str] = None,
        language: str = "python"
    ) -> TestResult:
        """Executes code and optional test harness in an isolated temporary sandbox directory."""
        clean_lang = language.lower().strip()
        is_js = clean_lang in ("javascript", "typescript", "js", "ts")

        if not filename:
            filename = "solution.js" if is_js else "solution.py"

        # 1. Pre-Sandbox Fast Syntax Gate
        syntax_ok, syntax_err = self.check_syntax(code, language=clean_lang)
        if not syntax_ok:
            return TestResult(
                passed=False,
                output=f"Pre-Sandbox Syntax Gate Failure: {syntax_err}",
                exit_code=1,
                duration_ms=0
            )

        # 2. Security Gate
        is_safe, reason = self.check_safety(code, language=clean_lang)
        if not is_safe:
            return TestResult(
                passed=False,
                output=f"Security Gate Failure: {reason}",
                exit_code=-1,
                duration_ms=0
            )

        if test_code:
            is_safe, reason = self.check_safety(test_code, language=clean_lang)
            if not is_safe:
                return TestResult(
                    passed=False,
                    output=f"Security Gate Failure in test code: {reason}",
                    exit_code=-1,
                    duration_ms=0
                )

        temp_dir = tempfile.mkdtemp(prefix="fixpilot_sandbox_")
        start_time = time.perf_counter()

        try:
            # 3. Write solution file
            solution_file = Path(temp_dir) / filename
            solution_file.write_text(code, encoding="utf-8")

            # 4. Formulate execution command based on language and harness
            if test_command:
                cmd = test_command
            elif test_code:
                test_filename = "test_harness.js" if is_js else "test_harness.py"
                test_file = Path(temp_dir) / test_filename
                test_file.write_text(test_code, encoding="utf-8")
                if is_js:
                    cmd = f'"{self.node_bin}" "{test_filename}"'
                else:
                    cmd = f'"{self.python_bin}" "{test_filename}"'
            else:
                if is_js:
                    cmd = f'"{self.node_bin}" "{filename}"'
                else:
                    cmd = f'"{self.python_bin}" "{filename}"'

            # 5. Execute subprocess asynchronously with timeout
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
                stdout_str = stdout_data.decode("utf-8", errors="replace")
                stderr_str = stderr_data.decode("utf-8", errors="replace")
                combined_output = (stdout_str + ("\n" + stderr_str if stderr_str else "")).strip()

                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                passed = (process.returncode == 0)

                return TestResult(
                    passed=passed,
                    output=combined_output if combined_output else ("Execution completed successfully with no output." if passed else "Process exited with non-zero exit code."),
                    exit_code=process.returncode or 0,
                    duration_ms=elapsed_ms
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                return TestResult(
                    passed=False,
                    output=f"Execution timed out after {self.timeout} seconds.",
                    exit_code=-1,
                    duration_ms=elapsed_ms
                )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return TestResult(
                passed=False,
                output=f"Sandbox execution error: {str(exc)}",
                exit_code=-1,
                duration_ms=elapsed_ms
            )
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
