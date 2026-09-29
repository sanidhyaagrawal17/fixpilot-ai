import logging
import re
from pathlib import Path
from core.config import settings, PROMPTS_DIR
from core.llm_client import call_nemotron, clean_json_response
from core.models import ClassificationResult, ErrorSeverity

logger = logging.getLogger("fixpilot.classifier")


class ErrorClassifier:
    """Classifies software errors and tracebacks using NVIDIA Nemotron-3 Nano."""

    def __init__(self):
        prompt_file = PROMPTS_DIR / "classify.txt"
        if prompt_file.exists():
            self.system_prompt = prompt_file.read_text(encoding="utf-8")
        else:
            self.system_prompt = (
                "You are an error classification engine. Return a JSON object with error_type, "
                "error_message, affected_file, affected_line, language, and confidence."
            )

    async def classify(self, traceback_text: str, source_code: str = "") -> ClassificationResult:
        """Analyzes traceback and code to produce structured classification metadata."""
        user_prompt = f"TRACEBACK / ERROR:\n{traceback_text}\n"
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

            return ClassificationResult(
                error_type=err_enum,
                error_message=parsed.get("error_message", "Unknown runtime error"),
                affected_file=parsed.get("affected_file"),
                affected_line=parsed.get("affected_line"),
                language=parsed.get("language", "python"),
                confidence=float(parsed.get("confidence", 0.9))
            )
        except Exception as exc:
            logger.warning(f"Nemotron classification call failed: {exc}. Using deterministic regex fallback.")
            return self._heuristic_fallback(traceback_text)

    def _heuristic_fallback(self, traceback_text: str) -> ClassificationResult:
        """Fast regex heuristic if LLM response parsing fails."""
        lines = [line.strip() for line in traceback_text.splitlines() if line.strip()]
        last_line = lines[-1] if lines else "Error"

        err_type = ErrorSeverity.RUNTIME
        if "IndexError" in last_line or "KeyError" in last_line or "TypeError" in last_line or "AttributeError" in last_line:
            err_type = ErrorSeverity.TYPE
        elif "SyntaxError" in last_line or "IndentationError" in last_line:
            err_type = ErrorSeverity.SYNTAX
        elif "ImportError" in last_line or "ModuleNotFoundError" in last_line:
            err_type = ErrorSeverity.IMPORT
        elif "AssertionError" in last_line:
            err_type = ErrorSeverity.LOGIC

        # Search for file and line
        file_match = re.search(r'File "([^"]+)", line (\d+)', traceback_text)
        aff_file = file_match.group(1) if file_match else None
        aff_line = int(file_match.group(2)) if file_match else None

        return ClassificationResult(
            error_type=err_type,
            error_message=last_line,
            affected_file=aff_file,
            affected_line=aff_line,
            language="python",
            confidence=0.85
        )
