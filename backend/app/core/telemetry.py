import logging
import sys
import structlog

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
    Every log emitted by this logger will automatically include the project_name key.
    """
    return structlog.get_logger("project").bind(project=project_name)