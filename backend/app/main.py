from contextlib import asynccontextmanager
from fastapi import FastAPI, status, HTTPException, Request # <-- Added Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path
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

# === ADD THIS GLOBAL EXCEPTION HANDLER ===
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches all unhandled exceptions, logs them securely, and masks the output to the client."""
    daemon_logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please check the daemon logs."},
    )
# ==========================================

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

    # Removed the try/except block. Let it bubble up!
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

    # Removed the try/except block. Let it bubble up!
    git_mgr = GitManager(repo_path=str(target_dir))
    commit_msg = await git_mgr.force_ai_commit()
    
    daemon_logger.info(f"Commit generated: {commit_msg}")
    return JSONResponse(content={
        "status": "success", 
        "message": f"Committed successfully:\n{commit_msg}"
    })

@app.post("/log-crash", status_code=status.HTTP_200_OK)
async def log_crash(request: CrashLogRequest) -> JSONResponse:
    project_logger = get_project_logger(request.project_name)
    project_logger.error(request.log_message)
    return JSONResponse(content={"status": "logged"})