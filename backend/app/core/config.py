from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    project_name: str = "AI Dev Daemon"
    api_v1_str: str = "/api/v1"
    
    # Defaults to the user's home directory
    daemon_workspace: Path = Path.home().resolve()

    # Tells pydantic to look for a .env file to override these defaults
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings object.
    lru_cache ensures we only read the .env file once on startup.
    """
    return Settings()