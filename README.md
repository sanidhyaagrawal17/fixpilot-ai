# 🔧 FixPilot — Autonomous Code Debugging Agent

[![FixPilot CI](https://github.com/sanidhyaagrawal17/fixpilot-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/sanidhyaagrawal17/fixpilot-ai/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/static/v1?label=Tests&message=28%2F28%20Passing&color=10B981&style=flat-square&logo=pytest)](https://github.com/sanidhyaagrawal17/fixpilot-ai)
[![NVIDIA Nemotron-3](https://img.shields.io/static/v1?label=NVIDIA%20Nemotron-3&message=Nano%2030B%20%E2%80%A2%20Super%20120B%20%E2%80%A2%20Ultra%20550B&color=76B900&style=flat-square&logo=nvidia)](https://build.nvidia.com)
[![Tavily Search](https://img.shields.io/static/v1?label=Tavily%20Search&message=Adaptive%20Grounding&color=0EA5E9&style=flat-square)](https://tavily.com)
[![Sandbox](https://img.shields.io/static/v1?label=Sandbox&message=Python%20AST%20%2B%20Node.js&color=6366F1&style=flat-square&logo=nodedotjs)](https://github.com/sanidhyaagrawal17/fixpilot-ai)
[![Nebius x NVIDIA](https://img.shields.io/static/v1?label=Nebius%20x%20NVIDIA&message=Global%20AI%20Hackathon&color=76B900&style=flat-square&logo=nvidia)](https://nebiusglobalaihackathon.devpost.com/)
[![Track](https://img.shields.io/static/v1?label=Track&message=Coding%20%26%20Agentic%20Engineering&color=2563EB&style=flat-square)](https://nebiusglobalaihackathon.devpost.com/)
[![Docker](https://img.shields.io/static/v1?label=Docker&message=Ready&color=2496ED&style=flat-square&logo=docker)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/static/v1?label=License&message=MIT&color=EAB308&style=flat-square)](https://opensource.org/licenses/MIT)

> **FixPilot** is an autonomous code debugging and repair agent built on open infrastructure. Given an error traceback and faulty source code (or GitHub repository URL), FixPilot reasons about the root cause using **NVIDIA Nemotron** models on **Nebius Token Factory**, grounds its diagnosis with **Tavily Web Search**, synthesizes surgically minimal unified diffs, and validates the repair in an isolated execution sandbox.

---

## 🚀 Key Capabilities

- **Autonomous State Machine**: Progresses seamlessly through `Classify` ➔ `Search Docs` ➔ `Analyze` ➔ `Synthesize Fix` ➔ `Sandbox Validate` with automated retry feedback loops (up to 3 attempts).
- **NVIDIA Model Cascading**: Optimizes inference latency, reasoning quality, and credit expenditure by matching tasks to the appropriate Nemotron model:
  - `nemotron-3-nano`: Sub-second error classification and boundary parsing.
  - `nemotron-3-ultra`: Deep architectural root-cause analysis.
  - `nemotron-3-super`: High-fidelity code synthesis and git-style unified diff generation.
- **Tavily Web Search Grounding**: Discovers relevant documentation, PEPs, and StackOverflow patterns to ground LLM reasoning and avoid hallucinations.
- **Sandboxed Execution & Safety Gate**: Code executes in isolated ephemeral workspaces with security regex scanners that prevent destructive OS-level execution.
- **GitHub Repository Extraction**: Clones remote GitHub repositories shallowly and extracts the faulty source files directly from stack trace line numbers.
- **Real-Time Streaming UI**: Minimalist, dark-themed Linear/Vercel style dashboard with Server-Sent Events (SSE) telemetry, live execution step timeline, and syntax-highlighted diffs.

---

## 🏗️ Technical Architecture

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

## 🤖 NVIDIA Models & Multi-Tier Provider Cascade

FixPilot connects directly to the official **NVIDIA API** (`integrate.api.nvidia.com`), with cascading fallbacks to **Nebius Token Factory**, **OpenRouter**, and deterministic local simulation. Calls employ escalating timeouts (30s → 60s → 90s) to guarantee resilience under heavy reasoning loads:

| Step | Model Name | Primary Task | Reasoning Tier |
|---|---|---|---|
| **Classification** | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | Categorize syntax, type, import, or runtime errors | Fast & Lightweight |
| **Analysis** | `nvidia/nemotron-3-ultra-550b-a55b` | Deep execution flow diagnosis and root-cause identification | Frontier Reasoning |
| **Synthesis** | `nvidia/nemotron-3-super-120b-a12b` | Generate surgical code fixes and unified diffs | High-Accuracy Code Generation |
| **Grounding** | Tavily Search API | Contextual documentation & StackOverflow lookup | Real-Time Web Grounding |

### ⏱️ Live Benchmark Telemetry (NVIDIA API • Verified Run)

Below is the per-tier execution latency and verification telemetry captured from a real end-to-end debugging run:

| Pipeline Stage | Model / Service | Latency | Output & Verification |
|---|---|---|---|
| **Tier 1: Classification** | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | **4.09s** | `TYPE: list index out of range` identified |
| **Tier 2: Doc Grounding** | Tavily Search API (`advanced` search) | **0.70s** | 3 citations retrieved (top score: `0.827`) |
| **Tier 3: Diagnosis** | `nvidia/nemotron-3-ultra-550b-a55b` | **1.45s** | Root cause isolated to collection boundary overrun |
| **Tier 4: Synthesis** | `nvidia/nemotron-3-super-120b-a12b` | **13.88s** | Surgical patch with guard clause synthesized |
| **Tier 5: Sandbox Verification**| `sandbox/eval` (Isolated AST/Subprocess) | **0.11s** | **VERIFIED PASS** (Exit Code 0, All assertions passed) |
| **Total Orchestration** | Master Async State Machine | **20.25s** | **100% Verified on Attempt 1/3** |

---

## ⚡ Quickstart

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/sanidhyaagrawal17/fixpilot-ai.git
cd fixpilot-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials

Copy the template environment file:
```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```env
# NVIDIA API (build.nvidia.com - Primary Provider)
NVIDIA_API_KEY=your_nvidia_api_key_here
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# Tavily Search API (from tavily.com)
TAVILY_API_KEY=your_tavily_api_key_here

# Optional: Nebius Token Factory
NEBIUS_API_KEY=your_nebius_api_key_here

# Optional: OpenRouter fallback
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

*(Note: If no API keys are configured, FixPilot automatically activates its built-in simulated diagnostic engine so you can test all features and UI locally without external credentials!)*

### 3. Run the Application

```bash
python main.py
```

Open your browser to:
```
http://localhost:8000
```

---

## 🐳 Docker & Cloud Deployment

FixPilot is fully containerized with a polyglot base (`python:3.11-slim-bookworm` + `Node.js` + `git`), supporting non-root user isolation and zero-downtime 1-click cloud deployments.

### Local Docker Build & Run
```bash
# Build production polyglot container
docker build -t fixpilot-ai .

# Run with .env configuration
docker run -p 8000:8000 --env-file .env fixpilot-ai
```

### Docker Compose
```bash
# Build and run with Docker Compose
docker-compose up --build
```

### 1-Click Cloud Deployment Manifests
- **Render**: Included [`render.yaml`](render.yaml) automatically provisions a Docker web service with keep-alive buffer flushing, dynamic `$PORT` binding, and `/api/health` monitoring.
- **Railway**: Included [`railway.json`](railway.json) configures container-level healthchecks and automatic restart policies.

---

## 🧪 Running the Test Suite

FixPilot includes a comprehensive suite of 28 unit and integration tests:

```bash
pytest tests/ -v
```

All 28 test cases validate:
- Pydantic v2 data models and serialization.
- Hardened AST security gates (`SecurityASTVisitor`) blocking prohibited imports (`os`, `subprocess`, `ctypes`, `sys`, `eval`, `exec`).
- Pre-sandbox fast syntax validation (`ast.parse` and `node --check`).
- Isolated Node.js sandbox runner and JavaScript security controls.
- Asynchronous SSE queue streaming, event ordering, and 10s heartbeat keep-alives.
- Multi-tier error classification and heuristic fallbacks.
- End-to-end sandbox reproduction and patch verification across all 7 scenarios (including the Tavily spotlight Pydantic v2 migration, JavaScript nullish type error, and multi-attempt self-healing retry cascade).

---

## 📁 Repository Structure

```
fixpilot-ai/
├── LICENSE                          # MIT License
├── README.md                        # Documentation & setup guide
├── SUBMISSION.md                    # Hackathon submission writeup & demo script
├── requirements.txt                 # Pinned dependencies
├── Dockerfile                       # Polyglot container (Python + Node.js + Git)
├── .dockerignore                    # Build exclusion rules
├── docker-compose.yml               # Compose orchestration file
├── render.yaml                      # Render 1-click deployment manifest
├── railway.json                     # Railway deployment manifest
├── .env.example                     # Environment template
│
├── main.py                          # FastAPI server & streaming SSE endpoints
│
├── core/
│   ├── __init__.py
│   ├── config.py                    # Centralized settings & model IDs
│   ├── models.py                    # Pydantic v2 schemas
│   ├── llm_client.py                # Unified NVIDIA / Nebius / OpenRouter / local LLM client
│   ├── classifier.py                # Error classification (Nemotron Nano)
│   ├── doc_search.py                # Tavily search integration
│   ├── analyzer.py                  # Root cause analysis (Nemotron Ultra)
│   ├── fixer.py                     # Code repair synthesis (Nemotron Super)
│   ├── sandbox.py                   # Hardened AST & Node.js sandbox
│   ├── repo_reader.py               # GitHub repo shallow cloner
│   └── agent.py                     # Master orchestrator state machine & SSE queue
│
├── prompts/                         # Model prompt templates
│   ├── classify.txt
│   ├── analyze.txt
│   ├── fix.txt
│   └── validate.txt
│
├── static/                          # Minimalist web interface
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── tests/                           # Complete test suite (28 tests)
│   ├── test_models.py
│   ├── test_sandbox.py
│   ├── test_sandbox_multilang.py    # AST gate & Node.js sandbox tests
│   ├── test_streaming.py            # SSE async queue & heartbeat tests
│   ├── test_classifier.py
│   ├── test_fixer.py
│   ├── test_agent.py
│   ├── test_api.py
│   ├── test_scenarios_e2e.py        # End-to-end scenario reproduction & verification
│   └── scenarios/                   # Built-in demonstration scenarios
│       ├── scenario_index_error.py
│       ├── scenario_type_error.py
│       ├── scenario_import_error.py
│       ├── scenario_logic_bug.py
│       ├── scenario_js_type_error.py
│       ├── scenario_modern_api_migration.py # Tavily Live-Docs Spotlight
│       └── scenario_self_healing_cascade.py # Multi-Attempt Retry Loop
│
└── docs/
    ├── ARCHITECTURE.md              # In-depth architectural design
    └── DEMO_SCENARIOS.md            # Scenario walkthroughs
```

---

## 👥 Author & Hackathon Submission

- **Author**: [Sanidhya Agrawal](https://github.com/sanidhyaagrawal17)
- **Hackathon**: [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/)
- **Track**: Coding and Agentic Engineering
- **Target Prizes**:
  - Coding & Agentic Engineering Track Winner (NVIDIA Jetson Orin Nano)
  - Best Use of Tavily (\$3,000)
  - Most Valuable Feedback (\$100 + NVIDIA Swag)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
