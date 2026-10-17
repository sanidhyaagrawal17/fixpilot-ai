# 🔧 FixPilot — Autonomous Code Debugging Agent

[![Hackathon](https://img.shields.io/badge/Nebius%20x%20NVIDIA-Global%20AI%20Hackathon-76B900?style=flat-square&logo=nvidia)](https://nebiusglobalaihackathon.devpost.com/)
[![Track](https://img.shields.io/badge/Track-Coding%20%26%20Agentic%20Engineering-blue?style=flat-square)](https://nebiusglobalaihackathon.devpost.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)

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

## 🐳 Docker Deployment

FixPilot is fully containerized and production-ready for deployment to Nebius Serverless Endpoints, Railway, or Render:

```bash
# Build and run with Docker Compose
docker-compose up --build
```

---

## 🧪 Running the Test Suite

FixPilot includes a comprehensive suite of unit and integration tests:

```bash
pytest tests/ -v
```

All 18 unit and integration tests validate models, classification, multi-language sandboxed execution, AST security gates, diff calculation, end-to-end agent remediation, async SSE streaming, and API endpoints.

---

## 📁 Repository Structure

```
fixpilot-ai/
├── LICENSE                          # MIT License
├── README.md                        # Documentation & setup guide
├── requirements.txt                 # Pinned dependencies
├── Dockerfile                       # Multi-stage production container
├── docker-compose.yml               # Compose orchestration file
├── .env.example                     # Environment template
│
├── main.py                          # FastAPI server & streaming SSE endpoints
│
├── core/
│   ├── __init__.py
│   ├── config.py                    # Centralized settings & model IDs
│   ├── models.py                    # Pydantic v2 schemas
│   ├── llm_client.py                # Unified Nebius / OpenRouter / local LLM client
│   ├── classifier.py                # Error classification (Nemotron Nano)
│   ├── doc_search.py                # Tavily search integration
│   ├── analyzer.py                  # Root cause analysis (Nemotron Ultra)
│   ├── fixer.py                     # Code repair synthesis (Nemotron Super)
│   ├── sandbox.py                   # Isolated code execution sandbox
│   ├── repo_reader.py               # GitHub repo shallow cloner
│   └── agent.py                     # Master orchestrator state machine
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
├── tests/                           # Complete test suite
│   ├── test_models.py
│   ├── test_sandbox.py
│   ├── test_sandbox_multilang.py    # AST gate & Node.js sandbox tests
│   ├── test_streaming.py            # SSE async queue & heartbeat tests
│   ├── test_classifier.py
│   ├── test_fixer.py
│   ├── test_agent.py
│   ├── test_api.py
│   └── scenarios/                   # Pre-built demonstration scenarios
│       ├── scenario_index_error.py
│       ├── scenario_type_error.py
│       ├── scenario_import_error.py
│       ├── scenario_logic_bug.py
│       └── scenario_js_type_error.py
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
