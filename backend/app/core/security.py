# Add anyio to your imports at the top
import os
import re
import anyio
from pathlib import Path
from fastapi import HTTPException
from app.core.config import get_settings
from functools import partial

# DELTE THIS LINE: WORKSPACE_ROOT = Path(os.getenv("DAEMON_WORKSPACE", Path.home())).resolve()

def secure_resolve_path(requested_path: str) -> Path:
    """
    Resolves a requested path and ensures it does not escape the workspace root.
    Fails fast with a 403 if traversal is detected.
    """
    settings = get_settings()
    workspace_root = settings.daemon_workspace
    target = Path(requested_path).resolve()
    
    if not target.is_relative_to(workspace_root):
        raise HTTPException(
            status_code=403, 
            detail=f"Path traversal blocked. Target must be within {workspace_root}"
        )
    return target

# ... (rest of your existing security.py code remains unchanged)

# ... (rest of your existing security.py code remains unchanged)

# This detects generic API keys and OpenAI specifically.
SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{32,}", "OPENAI_API_KEY"),
    (r"(?i)(?:api_key|secret|token)[\s:=]+['\"]([a-zA-Z0-9_\-]{16,})['\"]", "GENERIC_API_KEY")
]
# CHANGE to async def
async def scan_file_for_secrets(file_path: Path) -> None:
    """
    Scans a file for hardcoded secrets asynchronously. 
    Implements Halt-and-Catch-Fire: instantly raises an HTTPException if a secret is found.
    """
    try:
        # Offload the blocking disk read to a worker thread
        # FIX: Use partial to bundle the keyword argument before handing it to anyio
        read_func = partial(file_path.read_text, encoding="utf-8")
        content = await anyio.to_thread.run_sync(read_func)
        
        for pattern, key_name in SECRET_PATTERNS:
            if re.search(pattern, content):
                # HALT AND CATCH FIRE
                raise HTTPException(
                    status_code=400,
                    detail=f"HARDCODED SECRET DETECTED: A suspected {key_name} was found in {file_path.name}. "
                           f"Operation aborted. Remove the secret and use environment variables."
                )
    except UnicodeDecodeError:
        # Silently skip binary files or non-utf8 assets like images/fonts
        pass

def fence_prompt_data(data: str, tag_name: str) -> str:
    """
    Wraps untrusted data in XML tags for safe LLM consumption.
    Neutralizes any matching closing tags inside the data to prevent prompt injection escapes.
    """
    # Neutralize malicious closing tags by escaping the slash so the LLM ignores it
    escaped_data = data.replace(f"</{tag_name}>", f"<\\/{tag_name}>")
    
    return f"<{tag_name}>\n{escaped_data}\n</{tag_name}>"