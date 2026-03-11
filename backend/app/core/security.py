import os
import re
from pathlib import Path
from fastapi import HTTPException

# Enforce a strict root directory for all AI operations. 
# Defaults to the user's home directory unless explicitly overridden.
WORKSPACE_ROOT = Path(os.getenv("DAEMON_WORKSPACE", Path.home())).resolve()

def secure_resolve_path(requested_path: str) -> Path:
    """
    Resolves a requested path and ensures it does not escape the WORKSPACE_ROOT.
    Fails fast with a 403 if traversal is detected.
    """
    target = Path(requested_path).resolve()
    
    # Python 3.9+ native method for strict path containment
    if not target.is_relative_to(WORKSPACE_ROOT):
        raise HTTPException(
            status_code=403, 
            detail=f"Path traversal blocked. Target must be within {WORKSPACE_ROOT}"
        )
    return target

# ... (rest of your existing security.py code remains unchanged)

# This detects generic API keys and OpenAI specifically.
SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{32,}", "OPENAI_API_KEY"),
    (r"(?i)(?:api_key|secret|token)[\s:=]+['\"]([a-zA-Z0-9_\-]{16,})['\"]", "GENERIC_API_KEY")
]

def scan_file_for_secrets(file_path: Path) -> None:
    """
    Scans a file for hardcoded secrets. 
    Implements Halt-and-Catch-Fire: instantly raises an HTTPException if a secret is found.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        
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