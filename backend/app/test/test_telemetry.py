import pytest
import structlog
from app.core.telemetry import daemon_logger, get_project_logger

def test_telemetry_configuration():
    """Verify that loggers are correctly configured as structlog instances."""
    # Verify the global daemon logger
    assert hasattr(daemon_logger, "bind"), "daemon_logger is not a structlog bound logger"
    
    # Verify the dynamic project logger
    proj_logger = get_project_logger("test_repo")
    assert hasattr(proj_logger, "bind"), "project logger is not a structlog bound logger"
    
    # Verify we can bind contextual data to the logger without crashing
    bound_logger = proj_logger.bind(user_id="12345")
    assert bound_logger is not None