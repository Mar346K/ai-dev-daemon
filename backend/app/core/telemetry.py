import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_daemon_logger() -> logging.Logger:
    """
    Configures a professional rotating file logger for the backend daemon.
    Caps at 5MB per file with 2 backups to prevent disk space exhaustion.
    """
    log_dir = Path("..") / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "daemon_health.log"
    
    logger = logging.getLogger("ai_dev_daemon")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

def get_project_logger(project_name: str) -> logging.Logger:
    """
    Generates a dynamically routed logger for specific active projects.
    Isolates crash reports into their own project-specific directories.
    """
    log_dir = Path("..") / "logs" / project_name
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "crash_reports.log"
    
    logger = logging.getLogger(f"project_{project_name}")
    logger.setLevel(logging.WARNING) # Professional Standard: Only log warnings and errors for external projects
    
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
        )
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

# Initialize singleton instance for the internal daemon
daemon_logger = setup_daemon_logger()