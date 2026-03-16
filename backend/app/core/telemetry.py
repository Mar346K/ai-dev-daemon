import logging
import sys
import structlog
from pathlib import Path

# === V2 UPGRADE: Global Security Metric ===
SECURITY_INTERCEPT_COUNT = 0

def increment_security_intercept():
    """Increments the global metric whenever a secret is scrubbed by the AI."""
    global SECURITY_INTERCEPT_COUNT
    SECURITY_INTERCEPT_COUNT += 1
# ==========================================

LOGS_DIR = Path("logs")

# Professional Standard: Configure structlog for JSON structured logging globally
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Intercept standard library logging and format it to match our structlog setup
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

# Global logger for internal daemon operations
daemon_logger = structlog.get_logger("ai_dev_daemon")

def get_project_logger(project_name: str):
    """
    Returns a structured logger strictly bound to a specific project.
    Automatically creates an isolated logging directory for the project
    and routes error logs to a local crash_reports.log file.
    """
    # === V2 UPGRADE: Segmented Telemetry Routing ===
    project_log_dir = LOGS_DIR / project_name
    project_log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = project_log_dir / "crash_reports.log"
    
    # Create a standard python logger specific to this project
    std_logger = logging.getLogger(f"project.{project_name}")
    std_logger.setLevel(logging.ERROR)
    
    # Prevent adding multiple file handlers if logger is requested multiple times
    if not std_logger.handlers:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        std_logger.addHandler(file_handler)
        
    # Bind the structlog wrapper to our file-routed logger
    return structlog.wrap_logger(std_logger).bind(project=project_name)