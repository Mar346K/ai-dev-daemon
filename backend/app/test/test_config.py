import os
from pathlib import Path
from app.core.config import get_settings

def test_settings_default_values():
    """Verify that settings fall back to secure defaults when env vars are missing."""
    # Temporarily remove DAEMON_WORKSPACE from the environment if it exists
    original_workspace = os.environ.pop("DAEMON_WORKSPACE", None)
    
    # We clear the cache to force a fresh read of the environment
    get_settings.cache_clear()
    settings = get_settings()
    
    assert settings.project_name == "AI Dev Daemon"
    assert settings.api_v1_str == "/api/v1"
    assert isinstance(settings.daemon_workspace, Path)
    assert settings.daemon_workspace == Path.home().resolve()
    
    # Restore the environment
    if original_workspace:
        os.environ["DAEMON_WORKSPACE"] = original_workspace