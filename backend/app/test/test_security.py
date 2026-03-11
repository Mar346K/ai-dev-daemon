import pytest
import os
from pathlib import Path
from fastapi import HTTPException
from app.core.security import secure_resolve_path, WORKSPACE_ROOT

def test_secure_resolve_valid_path():
    """Verify that a project path within the designated workspace is allowed."""
    valid_path = WORKSPACE_ROOT / "my_valid_project"
    resolved = secure_resolve_path(str(valid_path))
    assert resolved == valid_path.resolve()

def test_secure_resolve_path_traversal():
    """Verify that attempting to traverse outside the workspace raises a 403 HTTPException."""
    # Force a path that attempts to go up one level from the workspace root
    escape_path = WORKSPACE_ROOT.parent / "forbidden_system_dir"
    
    with pytest.raises(HTTPException) as exc_info:
        secure_resolve_path(str(escape_path))
        
    assert exc_info.value.status_code == 403
    assert "Path traversal blocked" in exc_info.value.detail