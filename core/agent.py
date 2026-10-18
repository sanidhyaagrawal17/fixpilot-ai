import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, List, Optional, Set

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
    """Autonomous debugging orchestrator coordinating Nemotron models, Tavily grounding, and sandbox verification."""

    def __init__(self):
        self.classifier = ErrorClassifier()
        self.doc_search = DocSearchEngine()
        self.analyzer = RootCauseAnalyzer()
        self.fixer = CodeFixer()
        self.sandbox = CodeSandbox()
        self.repo_reader = GitHubRepoReader()

    def _detect_provider(self, model: str) -> str:
        """Determines the active upstream provider for a given model tier."""
        if settings.NVIDIA_API_KEY and not settings.NVIDIA_API_KEY.startswith("your_"):
            return "nvidia"
        if settings.NEBIUS_API_KEY and not settings.NEBIUS_API_KEY.startswith("your_"):
            return "nebius"
        if settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("your_"):
            return "openrouter"
        return "local"

    async def run(self, request: DebugRequest) -> DebugResponse:
        """Executes the complete autonomous debug lifecycle synchronously/batched."""
        # Use streaming pipeline internally with a dummy queue
        dummy_queue: asyncio.Queue = asyncio.Queue()
        response_holder: List[DebugResponse] = []

        async def _consumer():
            while True:
                item = await dummy_queue.get()
                if item is None:
                    break
                if item.get("event") == "complete" or item.get("event") == "pipeline_complete":
                    if "response" in item.get("data", {}):
                        response_holder.append(DebugResponse.model_validate(item["data"]["response"]))
                    elif "steps" in item.get("data", {}):
                        response_holder.append(DebugResponse.model_validate(item["data"]))

        consumer_task = asyncio.create_task(_consumer())
        await self._execute_pipeline(request, dummy_queue)
        await consumer_task

        if response_holder:
            return response_holder[-1]

        # Fallback empty response
        return DebugResponse(success=False, attempts=0)

    async def run_streaming(self, request: DebugRequest) -> AsyncGenerator[str, None]:
        """Streams real-time step events formatted as Server-Sent Events (SSE) with heartbeat ping."""
        queue: asyncio.Queue = asyncio.Queue()

        # Spawn pipeline execution as a producer task
        pipeline_task = asyncio.create_task(self._execute_pipeline(request, queue))

        try:
            while True:
                try:
                    # Wait up to 10 seconds for next event
                    item = await asyncio.wait_for(queue.get(), timeout=10.0)
                    if item is None:
                        break
                    # Format standard SSE data payload
                    yield f"data: {json.dumps(item)}\n\n"
                except asyncio.TimeoutError:
                    # Emit SSE comment keep-alive heartbeat while waiting for long LLM inference
                    yield ": keep-alive\n\n"
        finally:
            if not pipeline_task.done():
                pipeline_task.cancel()

    async def _execute_pipeline(self, request: DebugRequest, queue: asyncio.Queue) -> None:
        """Executes the 5-stage agent loop, pushing real-time tier events to the consumer queue."""
        steps: List[AgentStep] = []
        models_used: Set[str] = set()
        telemetry_breakdown: Dict[str, int] = {}
        start_overall = time.perf_counter()

        async def emit_event(event_name: str, data: dict):
            await queue.put({"event": event_name, "data": data})

        def record_step(status: AgentStatus, model: str, detail: str, duration_ms: int) -> AgentStep:
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

        try:
            # 0. Resolve source code & language
            source_code = request.source_code or ""
            target_lang = self.classifier.detect_language(request.error_traceback, source_code)
            is_js = target_lang in ("javascript", "typescript", "js", "ts")
            filename = "solution.js" if is_js else "solution.py"

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
                    step = record_step(
                        AgentStatus.IDLE,
                        "git/clone",
                        f"Cloned {request.github_url} and identified target file '{filename}'.",
                        d_ms
                    )
                    await emit_event("step", step.model_dump(mode="json"))
                else:
                    step = record_step(
                        AgentStatus.FAILED,
                        "git/clone",
                        f"Failed to extract source code from GitHub URL: {request.github_url}.",
                        d_ms
                    )
                    await emit_event("step", step.model_dump(mode="json"))

            if not source_code:
                comment_prefix = "//" if is_js else "#"
                source_code = f"{comment_prefix} Source code was not provided directly.\n{comment_prefix} FixPilot is inferring the fix from the traceback.\n"

            # Check if test harness needs auto-synthesis (Phase 3: Zero-Test Auto-Harness)
            active_test_code = request.test_code
            if not active_test_code and not request.test_command:
                synthesized = await self.classifier.synthesize_harness(
                    source_code=source_code,
                    error_traceback=request.error_traceback,
                    language=target_lang
                )
                if synthesized:
                    active_test_code = synthesized

            # Tier 1: Classify Error (Nemotron 3 Nano)
            await emit_event("tier_start", {
                "tier": "classify",
                "model": settings.MODEL_CLASSIFY,
                "attempt": 1,
                "timestamp": time.time()
            })
            t_cls = time.perf_counter()
            classification: ClassificationResult = await self.classifier.classify(
                traceback_text=request.error_traceback,
                source_code=source_code
            )
            d_cls_ms = int((time.perf_counter() - t_cls) * 1000)
            telemetry_breakdown["classify_ms"] = d_cls_ms

            step_cls = record_step(
                AgentStatus.CLASSIFYING,
                settings.MODEL_CLASSIFY,
                f"Classified error as '{classification.error_type.value.upper()}': {classification.error_message}",
                d_cls_ms
            )
            await emit_event("tier_complete", {
                "tier": "classify",
                "latency_ms": d_cls_ms,
                "provider": self._detect_provider(settings.MODEL_CLASSIFY),
                "payload": classification.model_dump(mode="json")
            })
            await emit_event("step", step_cls.model_dump(mode="json"))

            # Tier 2: Ground in Real Docs (Tavily Search API)
            await emit_event("tier_start", {
                "tier": "ground",
                "model": "tavily-search-api",
                "attempt": 1,
                "timestamp": time.time()
            })
            t_doc = time.perf_counter()
            doc_refs: List[DocReference] = await self.doc_search.search(
                error_message=classification.error_message,
                language=target_lang,
                max_results=settings.MAX_DOC_RESULTS
            )
            d_doc_ms = int((time.perf_counter() - t_doc) * 1000)
            telemetry_breakdown["ground_ms"] = d_doc_ms

            step_doc = record_step(
                AgentStatus.SEARCHING_DOCS,
                "tavily-search-api",
                f"Retrieved {len(doc_refs)} documentation and StackOverflow references for grounding.",
                d_doc_ms
            )
            await emit_event("tier_complete", {
                "tier": "ground",
                "latency_ms": d_doc_ms,
                "provider": "tavily",
                "payload": {
                    "count": len(doc_refs),
                    "references": [d.model_dump(mode="json") for d in doc_refs]
                }
            })
            await emit_event("step", step_doc.model_dump(mode="json"))

            # Tier 3 - 5: Iterative Loop (Diagnose ➔ Synthesize ➔ Verify)
            attempts = 0
            current_fix: Optional[FixResult] = None
            test_result: Optional[TestResult] = None
            previous_failed_fix: Optional[str] = None
            test_failure_output: Optional[str] = None
            is_resolved = False

            while attempts < settings.MAX_RETRIES:
                attempts += 1
                loop_label = f"Attempt {attempts}/{settings.MAX_RETRIES}"

                # Phase 2: Adaptive Retry Re-Grounding if new error occurred on subsequent attempts
                if attempts > 1 and test_failure_output:
                    lines = [l.strip() for l in test_failure_output.splitlines() if l.strip()]
                    new_error_line = lines[-1] if lines else "test failure"
                    delta_query = f"{target_lang} {new_error_line} fix"

                    await emit_event("retry_triggered", {
                        "attempt": attempts,
                        "new_error": new_error_line,
                        "delta_query": delta_query
                    })

                    # Perform adaptive Tavily delta lookup
                    try:
                        delta_refs = await self.doc_search.search(
                            error_message=new_error_line,
                            language=target_lang,
                            max_results=2
                        )
                        # Prepend newly discovered references
                        for ref in delta_refs:
                            if not any(existing.url == ref.url for existing in doc_refs):
                                doc_refs.insert(0, ref)
                    except Exception as e:
                        logger.warning(f"Adaptive Tavily search failed: {e}")

                # Tier 3: Root Cause Analysis (Nemotron 3 Ultra 550B)
                await emit_event("tier_start", {
                    "tier": "diagnose",
                    "model": settings.MODEL_ANALYZE,
                    "attempt": attempts,
                    "timestamp": time.time()
                })
                t_ana = time.perf_counter()
                analysis: AnalysisResult = await self.analyzer.analyze(
                    classification=classification,
                    source_code=source_code,
                    doc_references=doc_refs,
                    previous_failed_fix=previous_failed_fix,
                    test_failure_output=test_failure_output,
                    test_code=active_test_code
                )
                d_ana_ms = int((time.perf_counter() - t_ana) * 1000)
                telemetry_breakdown[f"diagnose_attempt_{attempts}_ms"] = d_ana_ms

                step_ana = record_step(
                    AgentStatus.ANALYZING,
                    settings.MODEL_ANALYZE,
                    f"[{loop_label}] Root cause identified: {analysis.root_cause[:120]}...",
                    d_ana_ms
                )
                await emit_event("tier_complete", {
                    "tier": "diagnose",
                    "latency_ms": d_ana_ms,
                    "provider": self._detect_provider(settings.MODEL_ANALYZE),
                    "payload": analysis.model_dump(mode="json")
                })
                await emit_event("step", step_ana.model_dump(mode="json"))

                # Tier 4: Code Repair Synthesis (Nemotron 3 Super 120B)
                await emit_event("tier_start", {
                    "tier": "synthesize",
                    "model": settings.MODEL_FIX,
                    "attempt": attempts,
                    "timestamp": time.time()
                })
                t_fix = time.perf_counter()
                current_fix = await self.fixer.generate_fix(
                    analysis=analysis,
                    source_code=source_code,
                    previous_failed_fix=previous_failed_fix,
                    test_failure_output=test_failure_output,
                    filename=filename,
                    test_code=active_test_code
                )
                d_fix_ms = int((time.perf_counter() - t_fix) * 1000)
                telemetry_breakdown[f"synthesize_attempt_{attempts}_ms"] = d_fix_ms

                step_fix = record_step(
                    AgentStatus.GENERATING_FIX,
                    settings.MODEL_FIX,
                    f"[{loop_label}] Synthesized repaired code ({len(current_fix.changes_summary)} modifications).",
                    d_fix_ms
                )
                await emit_event("tier_complete", {
                    "tier": "synthesize",
                    "latency_ms": d_fix_ms,
                    "provider": self._detect_provider(settings.MODEL_FIX),
                    "payload": current_fix.model_dump(mode="json")
                })
                await emit_event("step", step_fix.model_dump(mode="json"))

                # Tier 5: Isolated Sandbox Execution & Validation
                await emit_event("tier_start", {
                    "tier": "verify",
                    "model": "sandbox/eval",
                    "attempt": attempts,
                    "timestamp": time.time()
                })
                t_tst = time.perf_counter()
                test_result = await self.sandbox.execute_code(
                    code=current_fix.fixed_code,
                    test_code=active_test_code,
                    test_command=request.test_command,
                    filename=filename,
                    language=target_lang
                )
                d_tst_ms = int((time.perf_counter() - t_tst) * 1000)
                telemetry_breakdown[f"verify_attempt_{attempts}_ms"] = d_tst_ms

                if test_result.passed:
                    step_tst = record_step(
                        AgentStatus.SUCCESS,
                        "sandbox/eval",
                        f"[{loop_label}] Fix verified! All assertions passed ({test_result.duration_ms}ms).",
                        d_tst_ms
                    )
                    await emit_event("tier_complete", {
                        "tier": "verify",
                        "latency_ms": d_tst_ms,
                        "provider": "sandbox",
                        "payload": test_result.model_dump(mode="json")
                    })
                    await emit_event("step", step_tst.model_dump(mode="json"))
                    is_resolved = True
                    break
                else:
                    step_tst = record_step(
                        AgentStatus.RETRYING,
                        "sandbox/eval",
                        f"[{loop_label}] Validation failed with exit code {test_result.exit_code}. Preparing feedback loop.",
                        d_tst_ms
                    )
                    await emit_event("tier_complete", {
                        "tier": "verify",
                        "latency_ms": d_tst_ms,
                        "provider": "sandbox",
                        "payload": test_result.model_dump(mode="json")
                    })
                    await emit_event("step", step_tst.model_dump(mode="json"))
                    previous_failed_fix = current_fix.fixed_code
                    test_failure_output = test_result.output

            total_ms = int((time.perf_counter() - start_overall) * 1000)
            telemetry_breakdown["total_ms"] = total_ms

            final_response = DebugResponse(
                success=is_resolved,
                attempts=attempts,
                classification=classification,
                analysis=analysis,
                fix=current_fix,
                test_result=test_result,
                steps=steps,
                total_duration_ms=total_ms,
                models_used=sorted(list(models_used)),
                doc_references=doc_refs,
                telemetry=telemetry_breakdown
            )

            # Emit final structured completion event
            await emit_event("pipeline_complete", {
                "verified": is_resolved,
                "total_attempts": attempts,
                "final_diff": current_fix.diff if current_fix else "",
                "telemetry": {
                    "total_duration_ms": total_ms,
                    "breakdown": telemetry_breakdown,
                    "models_used": sorted(list(models_used)),
                    "active_provider": self._detect_provider(settings.MODEL_ANALYZE)
                },
                "response": final_response.model_dump(mode="json")
            })

            # Emit legacy complete event for backward compatibility
            await emit_event("complete", final_response.model_dump(mode="json"))

        except Exception as exc:
            logger.exception(f"Unhandled error in debug pipeline: {exc}")
            err_step = record_step(AgentStatus.FAILED, "error", f"Pipeline aborted: {str(exc)}", 0)
            await emit_event("step", err_step.model_dump(mode="json"))
        finally:
            # Sentinel signaling completion to the SSE consumer generator
            await queue.put(None)
