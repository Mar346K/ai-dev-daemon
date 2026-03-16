import os
import pytest
from pathlib import Path

# We import the modules we are about to upgrade
from app.core.context_builder import ContextCompiler
from app.core.telemetry import get_project_logger

def test_dynamic_gitignore_inheritance(tmp_path):
    """
    V2 Requirement 1: The ContextCompiler must respect the target project's .gitignore
    so we do not accidentally scrape secrets or heavy build folders into the LLM context.
    """
    # 1. Setup a fake project directory with a secret file and a .gitignore
    (tmp_path / "main.py").write_text("print('hello world')")
    (tmp_path / "secrets.json").write_text('{"api_key": "12345"}')
    (tmp_path / ".gitignore").write_text("secrets.json\n")

    # 2. Run the compiler
    compiler = ContextCompiler(root_path=str(tmp_path))
    output_file = compiler.compile()
    content = output_file.read_text(encoding="utf-8")

    # 3. Mathematical Proof: main.py is included, but the secret payload is completely ignored
    assert "main.py" in content
    
    # We test for the secret payload, because the string "secrets.json" is technically inside .gitignore!
    assert "12345" not in content, "SECURITY BREACH: Ignored file contents were scraped into context!"
    assert "└── secrets.json" not in content, "SECURITY BREACH: Ignored file appeared in directory tree!"

def test_segmented_telemetry_directory_creation(tmp_path, monkeypatch):
    """
    V2 Requirement 2a: Telemetry must dynamically create a unique log folder 
    for every target project (e.g., logs/nexusrisk/crash_reports.log).
    """
    # 1. Mock the base log directory to our tmp_path so we don't pollute the real repo
    monkeypatch.setattr("app.core.telemetry.LOGS_DIR", tmp_path / "logs", raising=False)
    
    project_name = "nexusrisk"
    logger = get_project_logger(project_name)
    
    # 2. Emit a test log
    logger.error("Test crash for segmentation")
    
    # 3. Assert the isolated directory and log file were automatically created
    expected_log_file = tmp_path / "logs" / project_name / "crash_reports.log"
    assert expected_log_file.exists(), f"Expected isolated log file at {expected_log_file}"

def test_security_intercept_metric():
    """
    V2 Requirement 2b: The backend must track how many times the security 
    regex successfully intercepts and masks a secret.
    """
    import app.core.telemetry as telemetry
    
    # Ensure the metric starts at 0 (or exists at all!)
    telemetry.SECURITY_INTERCEPT_COUNT = 0
    
    # Trigger the new intercept tracking function
    telemetry.increment_security_intercept()
    
    assert telemetry.SECURITY_INTERCEPT_COUNT == 1, "Metric failed to increment."