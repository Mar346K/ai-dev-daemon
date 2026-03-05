import os
import pytest
from pathlib import Path
from app.core.context_builder import ContextCompiler

def test_context_compiler_generation(tmp_path: Path) -> None:
    """
    Creates a temporary mock directory structure to verify the compiler
    correctly builds the markdown file and ignores excluded folders.
    """
    # 1. Setup mock repository structure using pytest's built-in tmp_path
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("print('Hello World')", encoding="utf-8")
    
    # 2. Setup a forbidden directory that should be ignored
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "secret.py").write_text("API_KEY = '123'", encoding="utf-8")
    
    # 3. Run the compiler
    compiler = ContextCompiler(root_path=str(tmp_path))
    output_path = compiler.compile()
    
    # 4. Assertions
    assert output_path.exists()
    assert output_path.name == "llm_context_dump.md"
    
    content = output_path.read_text(encoding="utf-8")
    
    # Verify the tree and code sections exist
    assert "## Directory Tree" in content
    assert "## Source Code" in content
    
    # Verify valid files were included
    assert "### File: `app/main.py`" in content.replace("\\", "/")
    assert "print('Hello World')" in content
    
    # Verify forbidden directories were STRICTLY excluded
    assert ".venv" not in content
    assert "API_KEY" not in content