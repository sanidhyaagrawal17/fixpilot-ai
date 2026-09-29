import asyncio
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

from core.config import settings
from core.models import TestResult

logger = logging.getLogger("fixpilot.sandbox")

DANGEROUS_PATTERNS = [
    r"os\.system\(",
    r"shutil\.rmtree\(",
    r"format\s+[a-zA-Z]:",
    r"mkfs",
    r":\(\)\{\s*:\|\:&\s*\};:",
    r"subprocess\.(?:Popen|call|run)\(.*(?:rm\s+-rf|del\s+/f)",
    r"ctypes\.windll",
]


class CodeSandbox:
    """Isolated execution sandbox for validating synthesized code fixes against test assertions."""

    def __init__(self, timeout: int = settings.SANDBOX_TIMEOUT):
        self.timeout = timeout
        self.python_bin = sys.executable

    def check_safety(self, code: str) -> Tuple[bool, Optional[str]]:
        """Scans code for dangerous OS destruction patterns before executing."""
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Prohibited dangerous execution pattern detected: {pattern}"
        return True, None

    async def execute_code(
        self,
        code: str,
        test_code: Optional[str] = None,
        test_command: Optional[str] = None,
        filename: str = "solution.py"
    ) -> TestResult:
        """Executes the fixed code and optional test harness in an isolated temporary directory."""
        is_safe, reason = self.check_safety(code)
        if not is_safe:
            return TestResult(
                passed=False,
                output=f"Security Gate Failure: {reason}",
                exit_code=-1,
                duration_ms=0
            )

        if test_code:
            is_safe, reason = self.check_safety(test_code)
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
            # 1. Write the main solution file
            solution_file = Path(temp_dir) / filename
            solution_file.write_text(code, encoding="utf-8")

            # 2. Determine command to run
            if test_command:
                cmd = test_command
            elif test_code:
                # Write test harness file
                test_file = Path(temp_dir) / "test_harness.py"
                test_file.write_text(test_code, encoding="utf-8")
                cmd = f'"{self.python_bin}" test_harness.py'
            else:
                # Directly execute the solution file
                cmd = f'"{self.python_bin}" "{filename}"'

            # 3. Execute subprocess asynchronously with timeout
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
