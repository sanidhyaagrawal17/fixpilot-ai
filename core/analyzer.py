import logging
from typing import List, Optional
from core.config import settings, PROMPTS_DIR
from core.llm_client import call_nemotron, clean_json_response
from core.models import AnalysisResult, ClassificationResult, DocReference

logger = logging.getLogger("fixpilot.analyzer")


class RootCauseAnalyzer:
    """Performs deep reasoning and root-cause diagnostics using NVIDIA Nemotron-3 Ultra."""

    def __init__(self):
        prompt_file = PROMPTS_DIR / "analyze.txt"
        if prompt_file.exists():
            self.system_prompt = prompt_file.read_text(encoding="utf-8")
        else:
            self.system_prompt = (
                "You are a root cause debugging analyzer. Return a JSON object with root_cause, "
                "explanation, affected_code_snippet, suggested_approach, and doc_references."
            )

    async def analyze(
        self,
        classification: ClassificationResult,
        source_code: str,
        doc_references: List[DocReference],
        previous_failed_fix: Optional[str] = None,
        test_failure_output: Optional[str] = None,
        test_code: Optional[str] = None
    ) -> AnalysisResult:
        """Invokes Nemotron-3 Ultra to determine why the code failed and outline the fix strategy."""
        docs_summary = "\n".join([f"- {d.title} ({d.url}): {d.snippet}" for d in doc_references])

        user_content = (
            f"ERROR TYPE: {classification.error_type.value.upper()}\n"
            f"ERROR MESSAGE: {classification.error_message}\n"
            f"AFFECTED FILE: {classification.affected_file or 'Unknown'}\n"
            f"AFFECTED LINE: {classification.affected_line or 'Unknown'}\n\n"
            f"TARGET SOURCE CODE:\n```python\n{source_code}\n```\n\n"
            f"DOCUMENTATION & WEB CONTEXT:\n{docs_summary}\n"
        )

        if test_code and test_code.strip():
            user_content += (
                f"\nTEST HARNESS & VERIFICATION ASSERTIONS:\n```python\n{test_code}\n```\n"
            )

        if previous_failed_fix and test_failure_output:
            user_content += (
                f"\n--- PREVIOUS ATTEMPT FAILURE FEEDBACK ---\n"
                f"Previous Proposed Fix:\n```python\n{previous_failed_fix}\n```\n"
                f"Validation Test Output (FAILED):\n{test_failure_output}\n"
                f"Please diagnose why this previous attempt failed and revise your root-cause analysis.\n"
            )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            raw_response = await call_nemotron(
                messages=messages,
                model_name=settings.MODEL_ANALYZE,
                fallback_model=settings.FALLBACK_MODEL_ANALYZE,
                temperature=0.2,
                max_tokens=2048
            )
            parsed = clean_json_response(raw_response)

            return AnalysisResult(
                root_cause=parsed.get("root_cause", "State or boundary constraint violation."),
                explanation=parsed.get("explanation", "The execution sequence triggered an unhandled exception."),
                affected_code_snippet=parsed.get("affected_code_snippet", ""),
                suggested_approach=parsed.get("suggested_approach", "Refactor the logic to enforce boundary checks."),
                doc_references=doc_references
            )
        except Exception as exc:
            logger.warning(f"Nemotron Ultra analysis call failed: {exc}. Using fallback reasoning.")
            return AnalysisResult(
                root_cause=f"Runtime exception triggered by {classification.error_message}",
                explanation="Execution encountered an unexpected value or state violation at runtime.",
                affected_code_snippet=source_code.splitlines()[0] if source_code else "",
                suggested_approach="Add boundary validation and guard checks to ensure robust execution.",
                doc_references=doc_references
            )
