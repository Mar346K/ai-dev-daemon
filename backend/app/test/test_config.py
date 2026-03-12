import os
from pathlib import Path
from app.core.config import Settings, get_settings

def test_settings_default_values():
    """Verify that settings fall back to secure defaults when env vars are missing."""
    # By passing _env_file=None, we force Pydantic to ignore the local .env file
    # and strictly test the hardcoded default fallbacks.
    settings = Settings(_env_file=None)
    
    assert settings.project_name == "AI Dev Daemon"
    assert settings.api_v1_str == "/api/v1"
    assert isinstance(settings.daemon_workspace, Path)
    assert settings.daemon_workspace == Path.home().resolve()