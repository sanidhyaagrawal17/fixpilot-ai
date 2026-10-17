from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ErrorSeverity(str, Enum):
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    LOGIC = "logic"
    IMPORT = "import"
    TYPE = "type"
    UNKNOWN = "unknown"


class AgentStatus(str, Enum):
    IDLE = "idle"
    CLASSIFYING = "classifying"
    SEARCHING_DOCS = "searching_docs"
    ANALYZING = "analyzing"
    GENERATING_FIX = "generating_fix"
    VALIDATING = "validating"
    TESTING = "testing"
    RETRYING = "retrying"
    SUCCESS = "success"
    FAILED = "failed"


# --- API Request ---

class DebugRequest(BaseModel):
    error_traceback: str = Field(..., description="Raw error traceback or compiler output")
    source_code: Optional[str] = Field(None, description="Source code containing the issue")
    github_url: Optional[str] = Field(None, description="GitHub repository URL to inspect")
    file_path: Optional[str] = Field(None, description="Target file inside repo")
    language: str = Field(default="python", description="Programming language")
    test_code: Optional[str] = Field(None, description="Optional unit test code to verify the fix")
    test_command: Optional[str] = Field(None, description="Shell command to run validation tests")


# --- Diagnostic Artefacts ---

class ClassificationResult(BaseModel):
    error_type: ErrorSeverity
    error_message: str
    affected_file: Optional[str] = None
    affected_line: Optional[int] = None
    language: str = "python"
    confidence: float = 1.0


class DocReference(BaseModel):
    title: str
    url: str
    snippet: str
    score: Optional[float] = None
    id: Optional[str] = None


class AnalysisResult(BaseModel):
    root_cause: str
    explanation: str
    affected_code_snippet: str
    suggested_approach: str
    doc_references: List[DocReference] = Field(default_factory=list)


class FixResult(BaseModel):
    original_code: str
    fixed_code: str
    diff: str
    explanation: str
    changes_summary: List[str] = Field(default_factory=list)


class TestResult(BaseModel):
    __test__ = False
    passed: bool
    output: str
    exit_code: int
    duration_ms: int


# --- Agent Step Telemetry & Final Response ---

class AgentStep(BaseModel):
    step: int
    status: AgentStatus
    model_used: str
    detail: str
    duration_ms: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DebugResponse(BaseModel):
    success: bool
    attempts: int
    classification: Optional[ClassificationResult] = None
    analysis: Optional[AnalysisResult] = None
    fix: Optional[FixResult] = None
    test_result: Optional[TestResult] = None
    steps: List[AgentStep] = Field(default_factory=list)
    total_duration_ms: int = 0
    models_used: List[str] = Field(default_factory=list)
    doc_references: List[DocReference] = Field(default_factory=list)
    telemetry: Optional[dict] = Field(default_factory=dict)
