from contextlib import asynccontextmanager
from fastapi import FastAPI, status, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path
import httpx
import asyncio  # <-- ADDED FOR DEBOUNCER

from app.core.context_builder import ContextCompiler
from app.core.telemetry import daemon_logger, get_project_logger
from app.core.git_manager import GitManager
from app.core.security import secure_resolve_path

@asynccontextmanager
async def lifespan(app: FastAPI):
    daemon_logger.info("AI Dev Daemon initialized and listening for connections.")
    yield
    daemon_logger.info("AI Dev Daemon shutting down safely.")

app = FastAPI(
    title="AI Dev Daemon API",
    description="Backend for the local AI Developer Dashboard and Version Control Daemon.",
    version="0.1.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches all unhandled exceptions, logs them securely, and masks the output to the client."""
    daemon_logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please check the daemon logs."},
    )

class ProjectRequest(BaseModel):
    project_path: str

class CrashLogRequest(BaseModel):
    project_name: str
    log_message: str

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    return JSONResponse(content={"status": "healthy", "service": "ai_dev_daemon"})

@app.post("/compile-context", status_code=status.HTTP_200_OK)
async def compile_context(request: ProjectRequest) -> JSONResponse:
    target_dir = secure_resolve_path(request.project_path)
    daemon_logger.info(f"Received request to compile context for: {target_dir}")
    
    if not target_dir.exists() or not target_dir.is_dir():
        daemon_logger.warning(f"Rejected invalid directory path: {target_dir}")
        raise HTTPException(status_code=400, detail="Invalid project directory path.")

    compiler = ContextCompiler(root_path=str(target_dir))
    output_path = compiler.compile()
    daemon_logger.info(f"Context compiled successfully: {output_path.name}")
    
    return JSONResponse(content={
        "status": "success", 
        "message": f"Context compiled successfully to {output_path}"
    })

@app.post("/force-commit", status_code=status.HTTP_200_OK)
async def force_commit(request: ProjectRequest) -> JSONResponse:
    target_dir = secure_resolve_path(request.project_path)
    daemon_logger.info(f"Received request to force commit for: {target_dir}")
    
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Invalid project directory path.")

    git_mgr = GitManager(repo_path=str(target_dir))
    commit_msg = await git_mgr.force_ai_commit()
    
    daemon_logger.info(f"Commit generated: {commit_msg}")
    return JSONResponse(content={
        "status": "success", 
        "message": f"Committed successfully:\n{commit_msg}"
    })

# === UPGRADE 4.1: The AI Healer Background Task ===
async def analyze_crash_with_llm(project_name: str, log_message: str):
    """
    Asynchronously queries the local Ollama 8B model to diagnose 
    crashes without blocking the main FastAPI event loop.
    """
    daemon_logger.info(f"system.ai_healer.spooling: warming up local LLM for {project_name}...")
    
    prompt = f"""You are a Principal AI DevSecOps Engineer. 
A local Python process in the project '{project_name}' just crashed.
Analyze the following stack trace or error log and provide:
1. The Root Cause (be brief and technical).
2. A specific, actionable 1-line code fix or terminal command.

CRASH LOG:
{log_message}
"""
    
    try:
        # 120s timeout allows the GPU time to load the model weights from disk
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.1",  # Matches your installed 4.9GB model
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            analysis = data.get("response", "No response generated.")
            
            # Print the AI's diagnosis directly to the backend terminal
            print("\n" + "="*80)
            print(f"🤖 AI HEALER DIAGNOSIS FOR: {project_name}")
            print("="*80)
            print(analysis.strip())
            print("="*80 + "\n")
            
            daemon_logger.info(f"system.ai_healer.complete: Diagnosis generated for {project_name}")
            
    except Exception as e:
        daemon_logger.error(f"system.ai_healer.failed: {str(e)}")
# ==================================================

# === UPGRADE 4.2: Async Telemetry Debouncer ===
# Global state to hold crash lines and timer tasks while the 1.5s window is open
crash_buffers = {}
debounce_timers = {}

async def debounced_ai_healer(project_name: str):
    """Waits for the telemetry window to close, then fires the unified prompt."""
    # The 1.5 second collection window
    await asyncio.sleep(1.5)
    
    # Window closed! Extract the unified log and clean up state
    full_log = "\n".join(crash_buffers.pop(project_name, []))
    debounce_timers.pop(project_name, None)
    
    if not full_log.strip():
        return
        
    # Fire the single, unified payload to the AI
    await analyze_crash_with_llm(project_name, full_log)

@app.post("/log-crash", status_code=status.HTTP_200_OK)
async def log_crash(request: CrashLogRequest) -> JSONResponse:
    """Ingests crash telemetry and batches it via an async debouncer."""
    # 1. Log the raw crash immediately to the project-specific file
    project_logger = get_project_logger(request.project_name)
    project_logger.error(request.log_message)
    
    project = request.project_name
    
    # 2. Append the new line to the project's active buffer
    if project not in crash_buffers:
        crash_buffers[project] = []
    crash_buffers[project].append(request.log_message)
    
    # 3. If a timer is already running for this project, cancel it (reset the clock)
    if project in debounce_timers:
        debounce_timers[project].cancel()
        
    # 4. Start a fresh 1.5-second countdown
    task = asyncio.create_task(debounced_ai_healer(project))
    debounce_timers[project] = task
    
    return JSONResponse(content={"status": "Crash logged. Debouncing for AI Healer."})
# ==============================================