import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_daemon_logger() -> logging.Logger:
    """
    Configures a professional rotating file logger for the backend daemon.
    Caps at 5MB per file with 2 backups to prevent disk space exhaustion.
    """
    # Create logs directory at the root level
    log_dir = Path("..") / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "daemon_health.log"
    
    logger = logging.getLogger("ai_dev_daemon")
    logger.setLevel(logging.INFO)
    
    # Prevent adding multiple handlers if the logger is called multiple times
    if not logger.handlers:
        # Professional Standard: 5MB limit, keep the last 2 files
        handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
        )
        
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

# Initialize singleton instance
daemon_logger = setup_daemon_logger()