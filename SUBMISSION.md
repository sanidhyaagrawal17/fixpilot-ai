# FixPilot: Autonomous 5-Stage Code Remediation Agent
> **Nebius x NVIDIA Global AI Hackathon Submission**  
> **Track**: Coding and Agentic Engineering  
> **Target Prizes**: Coding & Agentic Track Winner • Best Use of Tavily ($3,000) • Most Valuable Feedback ($100 + NVIDIA Swag)  
> **Repository**: [https://github.com/sanidhyaagrawal17/fixpilot-ai](https://github.com/sanidhyaagrawal17/fixpilot-ai)  
> **Live Demo Web App**: `http://localhost:8000` (Docker container ready)

[![FixPilot CI](https://github.com/sanidhyaagrawal17/fixpilot-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/sanidhyaagrawal17/fixpilot-ai/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/Tests-28%2F28%20Passing-10B981?style=flat-square&logo=pytest)](https://github.com/sanidhyaagrawal17/fixpilot-ai)
[![NVIDIA Nemotron-3](https://img.shields.io/badge/NVIDIA%20Nemotron--3-Nano%2030B%20%E2%80%A2%20Super%20120B%20%E2%80%A2%20Ultra%20550B-76B900?style=flat-square&logo=nvidia)](https://build.nvidia.com)
[![Tavily Search](https://img.shields.io/badge/Tavily%20Search-Adaptive%20Grounding-0EA5E9?style=flat-square)](https://tavily.com)
[![Sandbox](https://img.shields.io/badge/Sandbox-Python%20AST%20%2B%20Node.js-6366F1?style=flat-square&logo=nodedotjs)](https://github.com/sanidhyaagrawal17/fixpilot-ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

---

## ⚡ 1. Elevator Pitch (48 Words)
FixPilot is an autonomous 5-stage debugging agent powered by NVIDIA Nemotron-3 (Nano 30B, Ultra 550B, Super 120B) and Tavily Search. It triages errors, grounds hypotheses against live documentation, synthesizes surgical diffs, and evaluates fixes inside an isolated AST sandbox—adaptively re-grounding via Tavily Delta Search if edge cases emerge.

---

## 💡 2. Inspiration & The Problem
Developers spend over 35% of their working hours reproducing, Googling, and diagnosing runtime exceptions and library migration errors. Traditional AI coding assistants are **single-shot prompt-and-pray generators**:
1. **They hallucinate deprecated syntax** because static training weights cannot track breaking API changes (such as Pydantic v1 ➔ v2 or Node.js v22 deprecations).
2. **They operate without feedback loops**: If an AI-generated patch introduces a secondary bug or crashes on an empty collection, standard tools leave the developer stranded.
3. **They risk executing dangerous payloads** without static AST inspection.

FixPilot was built to replace blind generation with **adversarial, closed-loop agentic engineering**: combining specialized reasoning tiers with real-time web retrieval and deterministic sandboxed verification.

---

## 🏗️ 3. How It Works: The 5-Stage Multi-Model Architecture

Rather than routing all tasks to an expensive generic LLM, FixPilot decomposes software remediation into a specialized 5-stage economic cascade:

```
               [ User Traceback / Broken Script / GitHub Repo ]
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Master Agent State Machine                        │
│             (Async Queue Producer-Consumer • 10s Heartbeat Keep-Alive)       │
└──────┬───────────────────────┬──────────────────────┬───────────────────────┘
       │                       │                      │
       ▼                       ▼                      ▼
┌──────────────┐        ┌──────────────┐       ┌──────────────┐
│  STAGE 1     │        │  STAGE 2     │       │   STAGE 3    │
│   CLASSIFY   │        │ SEARCH DOCS  │       │   DIAGNOSE   │
│Nemotron Nano │        │  Tavily API  │       │Nemotron Ultra│
│     30B      │        │  (Advanced)  │       │     550B     │
└──────┬───────┘        └──────┬───────┘       └──────┬───────┘
       │                       │                      │
       └───────────────────────┼──────────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   STAGE 4    │
                        │  SYNTHESIZE  │
                        │Nemotron Super│
                        │     120B     │
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   STAGE 5    │
                        │  AST SANDBOX │
                        │  Python/Node │
                        └──────┬───────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
                 [PASS]                [FAIL]
             Verified Diff         Adaptive Feedback
             & Action Bar        Tavily Delta Re-Ground
                                 (Retry Loop up to 3x)
```

### Model & Provider Economics
| Stage | Engine / Model | Latency | Primary Responsibility |
|---|---|---|---|
| **1. Classification** | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | **<4.1s** | Sub-second polyglot triage (`python` vs `javascript`), traceback frame parsing, and zero-test reproduction harness synthesis. |
| **2. Doc Grounding** | **Tavily Search API** (`search_depth="advanced"`) | **<0.8s** | Real-time web retrieval querying authoritative documentation (`docs.python.org`, `developer.mozilla.org`, StackOverflow). |
| **3. Diagnosis** | `nvidia/nemotron-3-ultra-550b-a55b` | **<1.5s** | Frontier reasoning for deep execution state tracing, root-cause isolation, and hypothesis formulation. |
| **4. Synthesis** | `nvidia/nemotron-3-super-120b-a12b` | **<14.0s** | High-precision code repair generating surgical patches, guard clauses, and unified git diffs (`.patch`). |
| **5. Verification** | `CodeSandbox` (AST Security + Isolated Subprocess) | **<0.12s** | Deterministic pre-flight syntax gates and isolated execution. Evaluates exit code, stdout, and stderr. |

FixPilot connects directly to the **official NVIDIA API** (`integrate.api.nvidia.com`), with cascading fallbacks to **Nebius Token Factory**, **OpenRouter**, and a deterministic local diagnostic engine with zero external network dependencies.

---

## 🏆 4. Tavily $3,000 Bonus Prize Qualification

FixPilot deeply integrates Tavily as an active cognitive participant in the agent's feedback loop:

### 1. Polyglot Target Domain Routing
Tavily queries are dynamically filtered based on language detection:
- **Python**: Targets `docs.python.org`, `peps.python.org`, `github.com`, and StackOverflow.
- **JavaScript / TypeScript**: Targets `developer.mozilla.org`, `nodejs.org/api`, and StackOverflow.

### 2. Adaptive Delta Re-Grounding inside the Retry Loop
When the sandbox uncovers a secondary bug or hidden assertion failure on Attempt 2 or 3 (e.g., in `scenario_self_healing_cascade`), FixPilot does not blindly re-prompt the LLM. It extracts the new stderr failure message, constructs an **Adaptive Tavily Delta Query**, retrieves fresh documentation targeting the new exception, and feeds the delta citations into Nemotron-3 Ultra before Attempt 2 synthesis.

### 3. Relevance Scoring & Interactive UI Citations
Every citation returned by Tavily includes full attribution: title, URL, snippet, and a floating-point relevance score (`DocReference.score`). These are rendered live in the UI as clickable citation pills with score badges (e.g. `0.827`), providing instant auditability.

---

## 🔒 5. Security & Production Engineering Rigor

1. **Layered AST Static Analysis (`SecurityASTVisitor`)**:
   - Inspects `ast.Import`, `ast.ImportFrom`, and dangerous calls.
   - Prohibits dangerous modules (`os`, `subprocess`, `socket`, `shutil`, `sys`, `ctypes`, `builtins.__import__`, `eval`, `exec`) before execution.
2. **Sub-Millisecond Pre-Sandbox Syntax Gate**:
   - Validates generated patches with `ast.parse()` (Python) and `node --check` (JavaScript via stdin) before burning compute.
3. **Polyglot Production Container (`Dockerfile`)**:
   - Built on `python:3.11-slim-bookworm` + `Node.js` + `git`.
   - Runs under isolated non-root user `fixpilot` (`UID 1000`).
   - `PYTHONUNBUFFERED=1` and `--timeout-keep-alive 120`.
4. **Proxy Keep-Alive SSE Streaming**:
   - True producer-consumer streaming using an `asyncio.Queue`.
   - Emits `: keep-alive\n\n` comments every 10 seconds to keep reverse proxies (Render, Railway, Nginx) open during deep Nemotron-3 Ultra reasoning.
   - Includes `"X-Accel-Buffering": "no"` and `"Cache-Control": "no-cache, no-transform"`.
5. **100% Automated Test Suite**:
   - **28 automated unit and integration tests** passing with 100% reliability (`pytest tests/ -v`).

---

## 📊 6. Verified Real-World Benchmarks (NVIDIA API • Live Run)

| Stage | Service / Model | Measured Latency | Measured Output |
|---|---|---|---|
| **Tier 1: Classification** | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | **4,094 ms** | `TYPE: list index out of range` |
| **Tier 2: Doc Grounding** | Tavily Search API (`advanced` search) | **701 ms** | 3 citations (top score: `0.827`) |
| **Tier 3: Diagnosis** | `nvidia/nemotron-3-ultra-550b-a55b` | **1,447 ms** | Isolated collection boundary overrun |
| **Tier 4: Synthesis** | `nvidia/nemotron-3-super-120b-a12b` | **13,885 ms** | Correct unified diff with guard clause |
| **Tier 5: Sandbox** | Isolated Subprocess Runner | **115 ms** | **VERIFIED PASS** (`exit_code: 0`) |
| **Total Pipeline** | Master Async State Machine | **20,245 ms** | **100% Verified Pass (Attempt 1/3)** |

---

## 🎬 7. 3-Minute Demo Video Script & Recording Walkthrough

### Part 1: Architecture & UI Tour (0:00 - 0:45)
- Open `http://localhost:8000`.
- Point out the **Linear/Vercel minimalist dark UI**, live provider badge (`NVIDIA API • Active + Tavily`), and collapsible Quick-Start Guide.
- Explain the 5-stage decomposition: `Nano 30B` (triage) ➔ `Tavily` (grounding) ➔ `Ultra 550B` (reasoning) ➔ `Super 120B` (diff synthesis) ➔ `Sandbox` (verification).

### Part 2: Tavily Spotlight — Modern API Migration (0:45 - 1:45)
- Click **`✦ MODERN API MIGRATION`** in Quick Scenarios.
- Point out the error: `PydanticImportError: 'BaseSettings' has been moved to 'pydantic-settings'`.
- Press `Ctrl + Enter`.
- Watch the live SSE timeline:
  - Tavily retrieves official Pydantic v2 documentation (`docs.pydantic.dev`).
  - Point to the clickable citation pills with relevance scores (`0.80+`).
  - Nemotron-3 Super synthesizes the modern import: `from pydantic_settings import BaseSettings`.
  - The sandbox confirms 100% test pass.

### Part 3: The Multi-Attempt Self-Healing Retry Loop (1:45 - 2:40)
- Click **`↻ SELF-HEALING RETRY`** in Quick Scenarios.
- Explain the two-layer bug: an initial `KeyError` hides a runtime `ZeroDivisionError` on empty batches.
- Click **Run Autonomous Debugger**:
  - **Attempt 1**: Resolves `KeyError`, runs sandbox, catches `ZeroDivisionError: division by zero` (`[FAIL]`).
  - Watch the UI trigger: `↻ Retry Triggered: ZeroDivisionError`.
  - Highlight the **Adaptive Tavily Delta Search**: Tavily queries the new zero-division error live.
  - **Attempt 2**: Nemotron-3 synthesizes an empty collection guard.
  - Sandbox verifies `ALL TESTS PASSED` (`[SANDBOX VERIFIED PASS - Attempt 2/3]`).

### Part 4: One-Click Action Bar & Cloud Readiness (2:40 - 3:00)
- Click **Copy Unified Diff (.patch)** and **Download Verification Report (JSON)**.
- Highlight the production-ready Docker container and 1-click `render.yaml` and `railway.json` manifests.
- Conclude: *"FixPilot: Autonomous, grounded, and verified."*

---

## 👥 8. Author & Repository Information
- **Creator**: [Sanidhya Agrawal](https://github.com/sanidhyaagrawal17)
- **Email**: sanidhyaagrawal2005@gmail.com
- **Repository**: [https://github.com/sanidhyaagrawal17/fixpilot-ai](https://github.com/sanidhyaagrawal17/fixpilot-ai)
- **License**: MIT License
