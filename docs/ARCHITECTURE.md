# FixPilot Architecture & Technical Specification

FixPilot is an autonomous, multi-tier code debugging agent designed for the **Nebius x NVIDIA Global AI Hackathon** in the **Coding and Agentic Engineering Track**.

---

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Client UI / API                                 │
│                   FastAPI + SSE Real-Time Streaming                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DebugAgent Brain                                │
│                     (Orchestration & State Machine)                         │
└──────┬───────────────────────┬──────────────────────┬───────────────────────┘
       │                       │                      │
       ▼                       ▼                      ▼
┌──────────────┐        ┌──────────────┐       ┌──────────────┐
│  CLASSIFY    │        │  SEARCH DOCS │       │   ANALYZE    │
│ Nemotron Nano│        │  Tavily API  │       │Nemotron Ultra│
└──────┬───────┘        └──────┬───────┘       └──────┬───────┘
       │                       │                      │
       └───────────────────────┼──────────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   SYNTHESIZE │
                        │Nemotron Super│
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   SANDBOX    │
                        │ Isolated Run │
                        └──────┬───────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
                 [PASS]                [FAIL]
             Verified Fix         Feedback Loop
                                (Retry up to 3x)
```

---

## 2. NVIDIA Model Cascading Strategy

FixPilot optimizes compute latency, reasoning depth, and API credit expenditure by cascading between NVIDIA Nemotron models:

| Pipeline Step | NVIDIA Model | Primary Responsibility | Justification |
|---|---|---|---|
| **Classification** | `nemotron-3-nano` | Categorize error type & boundary | Ultra-fast inference (<800ms) with lightweight token cost. |
| **Grounding** | Tavily Web Search API | Retrieve relevant StackOverflow & official docs | Enforces grounded reasoning and targets the \$3,000 Tavily Bonus Prize. |
| **Root Cause Analysis** | `nemotron-3-ultra` | Deep reasoning on code state & execution flow | Maximum parameter reasoning capacity for subtle logic and boundary violations. |
| **Code Synthesis** | `nemotron-3-super` | Surgical unified diff & repair generation | High-fidelity code generation with minimal collateral refactoring. |
| **Validation** | `nemotron-3-nano` / Sandbox | AST syntax validation & subprocess test execution | Safety verification before local execution. |

---

## 3. Sandboxed Execution Safety Model

FixPilot executes synthesized fixes inside ephemeral isolated directories:
1. **Safety Pre-Screening**: Code is scanned for prohibited OS-level destructive calls (`os.system("format")`, `rmtree("/")`, fork bombs).
2. **Resource Boundaries**: Strict execution timeouts (default 30s) kill runaway processes or infinite loops.
3. **Automatic Cleanup**: Temporary workspace directories are destroyed immediately upon test completion.
4. **Isolated Subprocesses**: Each run runs in an independent interpreter instance.

---

## 4. API Specification

- `POST /api/debug`: Synchronous diagnosis returning `DebugResponse`.
- `POST /api/debug/stream`: Server-Sent Events (SSE) streaming real-time status, timeline, and final payload.
- `GET /api/scenarios`: Returns pre-built test scenarios.
- `GET /api/health`: Provides operational health and provider telemetry.
