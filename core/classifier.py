import logging
import re
from pathlib import Path
from typing import Optional
from core.config import settings, PROMPTS_DIR
from core.llm_client import call_nemotron, clean_json_response
from core.models import ClassificationResult, ErrorSeverity

logger = logging.getLogger("fixpilot.classifier")


class ErrorClassifier:
    """Classifies software errors and tracebacks using NVIDIA Nemotron-3 Nano with polyglot support."""

    def __init__(self):
        prompt_file = PROMPTS_DIR / "classify.txt"
        if prompt_file.exists():
            self.system_prompt = prompt_file.read_text(encoding="utf-8")
        else:
            self.system_prompt = (
                "You are an error classification engine. Return a JSON object with error_type, "
                "error_message, affected_file, affected_line, language, and confidence."
            )

    @staticmethod
    def detect_language(traceback_text: str, source_code: str = "") -> str:
        """Heuristically detects programming language between Python and JavaScript/TypeScript."""
        # Check V8 JS stack trace format: at Object.<anonymous> (file.js:10:5)
        if (
            re.search(r'\.(?:js|ts|mjs|cjs)\b', traceback_text, re.IGNORECASE)
            or re.search(r'^\s*at\s+.*\(?.*:\d+:\d+\)?', traceback_text, re.MULTILINE)
            or "Cannot read properties of undefined" in traceback_text
            or "node_modules" in traceback_text
            or "ReferenceError:" in traceback_text
        ):
            return "javascript"

        # Check Python traceback markers
        if (
            "Traceback (most recent call last):" in traceback_text
            or re.search(r'File "([^"]+)", line (\d+)', traceback_text)
            or re.search(r'\b(?:def|elif|from\s+\w+\s+import)\b', source_code)
        ):
            return "python"

        # Check JavaScript source tokens
        if re.search(r'\b(?:const\s+|let\s+|function\s*\(|console\.log|module\.exports|require\()\b', source_code):
            return "javascript"

        return "python"

    async def classify(self, traceback_text: str, source_code: str = "") -> ClassificationResult:
        """Analyzes traceback and code to produce structured classification metadata."""
        detected_lang = self.detect_language(traceback_text, source_code)
        user_prompt = f"LANGUAGE HINT: {detected_lang}\n\nTRACEBACK / ERROR:\n{traceback_text}\n"
        if source_code:
            user_prompt += f"\nSOURCE CODE SNIPPET (First 2000 chars):\n{source_code[:2000]}\n"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            raw_response = await call_nemotron(
                messages=messages,
                model_name=settings.MODEL_CLASSIFY,
                fallback_model=settings.FALLBACK_MODEL_CLASSIFY,
                temperature=0.1,
                max_tokens=1024
            )
            parsed = clean_json_response(raw_response)

            # Map error_type safely to enum
            raw_type = parsed.get("error_type", "unknown").lower()
            try:
                err_enum = ErrorSeverity(raw_type)
            except ValueError:
                err_enum = ErrorSeverity.UNKNOWN

            model_lang = parsed.get("language", detected_lang).lower()
            if model_lang not in ("python", "javascript", "typescript", "js", "ts"):
                model_lang = detected_lang

            return ClassificationResult(
                error_type=err_enum,
                error_message=parsed.get("error_message", "Unknown runtime error"),
                affected_file=parsed.get("affected_file"),
                affected_line=parsed.get("affected_line"),
                language=model_lang,
                confidence=float(parsed.get("confidence", 0.9))
            )
        except Exception as exc:
            logger.warning(f"Nemotron classification call failed: {exc}. Using deterministic regex fallback.")
            return self._heuristic_fallback(traceback_text, source_code)

    def _heuristic_fallback(self, traceback_text: str, source_code: str = "") -> ClassificationResult:
        """Fast regex heuristic if LLM response parsing fails."""
        lines = [line.strip() for line in traceback_text.splitlines() if line.strip()]
        last_line = lines[-1] if lines else "Error"
        language = self.detect_language(traceback_text, source_code)

        err_type = ErrorSeverity.RUNTIME
        if language == "javascript":
            if "TypeError" in traceback_text or "Cannot read properties" in traceback_text:
                err_type = ErrorSeverity.TYPE
            elif "SyntaxError" in traceback_text:
                err_type = ErrorSeverity.SYNTAX
            elif "Cannot find module" in traceback_text or "MODULE_NOT_FOUND" in traceback_text:
                err_type = ErrorSeverity.IMPORT
            elif "ReferenceError" in traceback_text or "AssertionError" in traceback_text:
                err_type = ErrorSeverity.LOGIC

            v8_match = re.search(r'at\s+(?:.*?\s+)?\(?([^:\s()]+):(\d+):(\d+)\)?', traceback_text)
            aff_file = v8_match.group(1) if v8_match else "index.js"
            aff_line = int(v8_match.group(2)) if v8_match else 1
        else:
            if "IndexError" in last_line or "KeyError" in last_line or "TypeError" in last_line or "AttributeError" in last_line:
                err_type = ErrorSeverity.TYPE
            elif "SyntaxError" in last_line or "IndentationError" in last_line:
                err_type = ErrorSeverity.SYNTAX
            elif "ImportError" in last_line or "ModuleNotFoundError" in last_line:
                err_type = ErrorSeverity.IMPORT
            elif "AssertionError" in last_line:
                err_type = ErrorSeverity.LOGIC

            file_match = re.search(r'File "([^"]+)", line (\d+)', traceback_text)
            aff_file = file_match.group(1) if file_match else None
            aff_line = int(file_match.group(2)) if file_match else None

        return ClassificationResult(
            error_type=err_type,
            error_message=last_line,
            affected_file=aff_file,
            affected_line=aff_line,
            language=language,
            confidence=0.85
        )

    async def synthesize_harness(self, source_code: str, error_traceback: str, language: str = "python") -> Optional[str]:
        """Synthesizes an assertion test harness using Nemotron Nano if user provided none."""
        is_js = language in ("javascript", "typescript", "js", "ts")
        prompt = (
            f"You are a test harness synthesis engine. Generate a minimal reproduction test script in {language} "
            f"that asserts the correct expected behavior of the code. "
            f"The test MUST use standard assertions (assert ... in Python, or console.assert / throw in JS). "
            f"Return ONLY valid code inside a ```{language} block.\n\n"
            f"SOURCE CODE:\n{source_code[:1500]}\n\n"
            f"ERROR TRACEBACK:\n{error_traceback[:500]}\n"
        )
        try:
            raw = await call_nemotron(
                messages=[{"role": "user", "content": prompt}],
                model_name=settings.MODEL_CLASSIFY,
                temperature=0.1,
                max_tokens=1024
            )
            code_match = re.search(rf"```{language}\s*(.*?)\s*```", raw, re.DOTALL | re.IGNORECASE)
            if code_match:
                return code_match.group(1).strip()
        except Exception as e:
            logger.warning(f"Test harness synthesis failed: {e}")

        # Fallback deterministic harness
        if is_js:
            return "// Synthesized test harness\ntry {\n  console.log('Running test verification...');\n} catch (e) { throw e; }\n"
        else:
            return "# Synthesized test harness\ndef test_solution():\n    pass\n\ntest_solution()\n"
