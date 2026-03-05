import os
import re
from pathlib import Path

# Professional Standard: Compile Regex patterns for performance
# This detects generic API keys and OpenAI specifically.
SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{32,}", "OPENAI_API_KEY"),
    (r"(?i)(?:api_key|secret|token)[\s:=]+['\"]([a-zA-Z0-9_\-]{16,})['\"]", "GENERIC_API_KEY")
]

def redact_secrets_in_file(file_path: Path) -> bool:
    """
    Scans a file for hardcoded secrets. Replaces them with os.getenv() calls
    and appends the key name to .env.example.

    Args:
        file_path (Path): The path to the file being scanned.

    Returns:
        bool: True if secrets were found and redacted, False otherwise.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content
        secrets_found = set()

        for pattern, key_name in SECRET_PATTERNS:
            if re.search(pattern, content):
                # Replace the matched secret with a safe os.getenv call
                content = re.sub(pattern, f"os.getenv('{key_name}')", content)
                secrets_found.add(key_name)

        if secrets_found:
            file_path.write_text(content, encoding="utf-8")
            _update_env_example(secrets_found)
            return True
            
        return False
    except Exception as e:
        # We will integrate our formal logger here in Phase 7
        print(f"Error scanning {file_path}: {e}")
        return False

def _update_env_example(keys: set[str]) -> None:
    """
    Appends newly discovered secret keys to .env.example safely.
    """
    example_path = Path(".env.example")
    existing_keys = ""
    
    if example_path.exists():
        existing_keys = example_path.read_text(encoding="utf-8")
        
    with example_path.open("a", encoding="utf-8") as f:
        for key in keys:
            if key not in existing_keys:
                f.write(f"{key}=\n")