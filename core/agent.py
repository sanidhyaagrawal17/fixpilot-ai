import asyncio
import json
import logging
import time
from typing import AsyncGenerator, List, Optional

from core.analyzer import RootCauseAnalyzer
from core.classifier import ErrorClassifier
from core.config import settings
from core.doc_search import DocSearchEngine
from core.fixer import CodeFixer
from core.models import (
    AgentStatus,
    AgentStep,
    AnalysisResult,
    ClassificationResult,
    DebugRequest,
    DebugResponse,
    DocReference,
    FixResult,
    TestResult,
)
from core.repo_reader import GitHubRepoReader
from core.sandbox import CodeSandbox

logger = logging.getLogger("fixpilot.agent")


class DebugAgent:
    """Autonomous debugging orchestrator coordinating Nemotron models and sandbox validation."""

    def __init__(self):
        self.classifier = ErrorClassifier()
        self.doc_search = DocSearchEngine()
        self.analyzer = RootCauseAnalyzer()
        self.fixer = CodeFixer()
        self.sandbox = CodeSandbox()
        self.repo_reader = GitHubRepoReader()

    async def run(self, request: DebugRequest) -> DebugResponse:
        """Executes the complete autonomous debug lifecycle and returns a full response."""
        steps: List[AgentStep] = []
        models_used = set()
        start_overall = time.perf_counter()

        def record_step(status: AgentStatus, model: str, detail: str, duration_ms: int):
            step_obj = AgentStep(
                step=len(steps) + 1,
                status=status,
                model_used=model,
                detail=detail,
                duration_ms=duration_ms
            )
            steps.append(step_obj)
            if model and model != "internal":
                models_used.add(model)
            return step_obj

        # 0. Resolve source code (from direct input or GitHub repo)
        source_code = request.source_code or ""
        filename = "solution.py"

        if not source_code and request.github_url:
            t0 = time.perf_counter()
            target_name, repo_code, _ = await self.repo_reader.fetch_target_code(
                github_url=request.github_url,
                traceback_text=request.error_traceback,
                specified_file_path=request.file_path
            )
            d_ms = int((time.perf_counter() - t0) * 1000)
            if repo_code:
                source_code = repo_code
                filename = target_name or filename
                record_step(
                    AgentStatus.IDLE,
                    "git/clone",
                    f"Cloned {request.github_url} and identified target file '{filename}'.",
                    d_ms
                )
            else:
                record_step(
                    AgentStatus.FAILED,
                    "git/clone",
                    f"Failed to extract source code from GitHub URL: {request.github_url}.",
                    d_ms
                )

        if not source_code:
            # Minimal dummy fallback to allow diagnosis from traceback
            source_code = "# Source code was not provided directly.\n# FixPilot is inferring the fix from the traceback.\n"

        # 1. Step: Error Classification (Nano)
        t_cls = time.perf_counter()
        classification: ClassificationResult = await self.classifier.classify(
            traceback_text=request.error_traceback,
            source_code=source_code
        )
        d_cls_ms = int((time.perf_counter() - t_cls) * 1000)
        record_step(
            AgentStatus.CLASSIFYING,
            settings.MODEL_CLASSIFY,
            f"Classified error as '{classification.error_type.value.upper()}': {classification.error_message}",
            d_cls_ms
        )

        # 2. Step: Documentation & Web Grounding (Tavily)
        t_doc = time.perf_counter()
        doc_refs: List[DocReference] = await self.doc_search.search(
            error_message=classification.error_message,
            language=request.language,
            max_results=settings.MAX_DOC_RESULTS
        )
        d_doc_ms = int((time.perf_counter() - t_doc) * 1000)
        record_step(
            AgentStatus.SEARCHING_DOCS,
            "tavily-search-api",
            f"Retrieved {len(doc_refs)} documentation and StackOverflow references for grounding.",
            d_doc_ms
        )

        # 3. Iterative Analysis, Fix, and Sandbox Validation Loop
        attempts = 0
        current_fix: Optional[FixResult] = None
        test_result: Optional[TestResult] = None
        previous_failed_fix: Optional[str] = None
        test_failure_output: Optional[str] = None
        is_resolved = False

        while attempts < settings.MAX_RETRIES:
            attempts += 1
            loop_label = f"Attempt {attempts}/{settings.MAX_RETRIES}"

            # Step 3A: Root Cause Analysis (Nemotron Ultra)
            t_ana = time.perf_counter()
            analysis: AnalysisResult = await self.analyzer.analyze(
                classification=classification,
                source_code=source_code,
                doc_references=doc_refs,
                previous_failed_fix=previous_failed_fix,
                test_failure_output=test_failure_output
            )
            d_ana_ms = int((time.perf_counter() - t_ana) * 1000)
            record_step(
                AgentStatus.ANALYZING,
                settings.MODEL_ANALYZE,
                f"[{loop_label}] Root cause identified: {analysis.root_cause[:120]}...",
                d_ana_ms
            )

            # Step 3B: Code Repair Synthesis (Nemotron Super)
            t_fix = time.perf_counter()
            current_fix = await self.fixer.generate_fix(
                analysis=analysis,
                source_code=source_code,
                previous_failed_fix=previous_failed_fix,
                test_failure_output=test_failure_output,
                filename=filename
            )
            d_fix_ms = int((time.perf_counter() - t_fix) * 1000)
            record_step(
                AgentStatus.GENERATING_FIX,
                settings.MODEL_FIX,
                f"[{loop_label}] Synthesized repaired code ({len(current_fix.changes_summary)} modifications).",
                d_fix_ms
            )

            # Step 3C: Isolated Sandbox Execution & Validation
            t_tst = time.perf_counter()
            test_result = await self.sandbox.execute_code(
                code=current_fix.fixed_code,
                test_code=request.test_code,
                test_command=request.test_command,
                filename=filename
            )
            d_tst_ms = int((time.perf_counter() - t_tst) * 1000)

            if test_result.passed:
                record_step(
                    AgentStatus.SUCCESS,
                    "sandbox/eval",
                    f"[{loop_label}] Fix verified! All assertions passed ({test_result.duration_ms}ms).",
                    d_tst_ms
                )
                is_resolved = True
                break
            else:
                record_step(
                    AgentStatus.RETRYING,
                    "sandbox/eval",
                    f"[{loop_label}] Validation failed with exit code {test_result.exit_code}. Preparing feedback loop.",
                    d_tst_ms
                )
                previous_failed_fix = current_fix.fixed_code
                test_failure_output = test_result.output

        total_ms = int((time.perf_counter() - start_overall) * 1000)

        return DebugResponse(
            success=is_resolved,
            attempts=attempts,
            classification=classification,
            analysis=analysis,
            fix=current_fix,
            test_result=test_result,
            steps=steps,
            total_duration_ms=total_ms,
            models_used=sorted(list(models_used)),
            doc_references=doc_refs
        )

    async def run_streaming(self, request: DebugRequest) -> AsyncGenerator[str, None]:
        """Streams real-time step events formatted as Server-Sent Events (SSE)."""
        response = await self.run(request)
        for step in response.steps:
            yield json.dumps({
                "event": "step",
                "data": step.model_dump(mode="json")
            })
            await asyncio.sleep(0.05)

        # Send final completed payload
        yield json.dumps({
            "event": "complete",
            "data": response.model_dump(mode="json")
        })
