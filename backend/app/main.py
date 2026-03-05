from fastapi import FastAPI, status, HTTPException
from fastapi.responses import JSONResponse
from app.core.context_builder import ContextCompiler
from app.core.telemetry import daemon_logger

app = FastAPI(
    title="AI Dev Daemon API",
    description="Backend for the local AI Developer Dashboard and Version Control Daemon.",
    version="0.1.0",
)

@app.on_event("startup")
async def startup_event() -> None:
    """Logs the ignition of the backend daemon."""
    daemon_logger.info("AI Dev Daemon initialized and listening for connections.")

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"status": "healthy", "service": "ai_dev_daemon"})

@app.post("/compile-context", status_code=status.HTTP_200_OK)
async def compile_context() -> JSONResponse:
    """Triggers the context builder and logs the event."""
    daemon_logger.info("Received request to compile context payload.")
    try:
        compiler = ContextCompiler()
        output_path = compiler.compile()
        daemon_logger.info(f"Context compiled successfully: {output_path.name}")
        return JSONResponse(content={
            "status": "success", 
            "message": f"Context compiled successfully to {output_path.name}"
        })
    except Exception as e:
        daemon_logger.error(f"Context compilation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))