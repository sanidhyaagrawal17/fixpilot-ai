import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from core.agent import DebugAgent
from core.config import settings
from core.models import DebugRequest, DebugResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("fixpilot.server")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="FixPilot",
    description="Autonomous Code Debugging Agent powered by NVIDIA Nemotron on Nebius Token Factory",
    version="1.0.0"
)

# Enable CORS for local and web UI clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Returns platform operational health and credential telemetry."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "models": {
            "classify": settings.MODEL_CLASSIFY,
            "analyze": settings.MODEL_ANALYZE,
            "fix": settings.MODEL_FIX,
            "validate": settings.MODEL_VALIDATE
        },
        "providers": {
            "nvidia_api": bool(settings.NVIDIA_API_KEY and not settings.NVIDIA_API_KEY.startswith("your_")),
            "nebius_token_factory": bool(settings.NEBIUS_API_KEY and not settings.NEBIUS_API_KEY.startswith("your_")),
            "openrouter_fallback": bool(settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("your_")),
            "tavily_search": bool(settings.TAVILY_API_KEY and not settings.TAVILY_API_KEY.startswith("your_"))
        }
    }


@app.post("/api/debug", response_model=DebugResponse)
async def debug_code(request: DebugRequest) -> DebugResponse:
    """Synchronous debug entrypoint executing full autonomous remediation lifecycle."""
    if not request.error_traceback.strip():
        raise HTTPException(status_code=400, detail="Error traceback must not be empty.")
    
    agent = DebugAgent()
    try:
        response = await agent.run(request)
        return response
    except Exception as exc:
        logger.exception("Error executing debug lifecycle")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/debug/stream")
async def debug_code_stream(request: DebugRequest):
    """Server-Sent Events (SSE) streaming endpoint delivering real-time agent progression."""
    if not request.error_traceback.strip():
        raise HTTPException(status_code=400, detail="Error traceback must not be empty.")

    agent = DebugAgent()

    async def event_generator():
        async for payload in agent.run_streaming(request):
            yield payload

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/scenarios")
async def get_scenarios() -> List[Dict[str, str]]:
    """Returns pre-built test scenarios for instant demonstration."""
    scenarios_dir = BASE_DIR / "tests" / "scenarios"
    scenario_list = []

    modules = [
        "scenario_index_error",
        "scenario_type_error",
        "scenario_import_error",
        "scenario_logic_bug",
        "scenario_js_type_error",
        "scenario_modern_api_migration"
    ]

    for mod_name in modules:
        try:
            mod = importlib.import_module(f"tests.scenarios.{mod_name}")
            scenario_list.append({
                "id": mod_name,
                "description": getattr(mod, "DESCRIPTION", mod_name),
                "source_code": getattr(mod, "SOURCE_CODE", ""),
                "error_traceback": getattr(mod, "ERROR_TRACEBACK", ""),
                "test_code": getattr(mod, "TEST_CODE", "")
            })
        except Exception as e:
            logger.warning(f"Could not load scenario {mod_name}: {e}")

    return scenario_list


# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_index():
    """Serves the main single-page debug UI."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "FixPilot API is active. UI static files not found."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
