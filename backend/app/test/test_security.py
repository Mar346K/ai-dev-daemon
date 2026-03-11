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

def test_scan_for_secrets_clean_file(tmp_path):
    """Verify that a file without secrets passes the scan silently."""
    clean_file = tmp_path / "clean_code.py"
    clean_file.write_text("print('Hello World')\nAPI_URL = 'https://api.example.com'")
    
    from app.core.security import scan_file_for_secrets
    # Should not raise any exceptions
    scan_file_for_secrets(clean_file)

def test_scan_for_secrets_halt_and_catch_fire(tmp_path):
    """Verify that discovering a secret instantly halts the process."""
    tainted_file = tmp_path / "leaky_code.py"
    tainted_file.write_text("def connect():\n    return 'sk-1234567890abcdef1234567890abcdef1234'")
    
    from app.core.security import scan_file_for_secrets
    
    with pytest.raises(HTTPException) as exc_info:
        scan_file_for_secrets(tainted_file)
        
    assert exc_info.value.status_code == 400
    assert "HARDCODED SECRET DETECTED" in exc_info.value.detail