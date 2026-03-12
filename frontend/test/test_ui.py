import pytest
import json
from main import AIDevDashboard
from unittest.mock import MagicMock
from PySide6.QtGui import QCloseEvent
import sys
import subprocess
from unittest.mock import patch, MagicMock
from main import ProjectRunnerWorker

def test_ring_buffer_memory_limit(qtbot, monkeypatch):
    """
    Verify that the log viewer strictly enforces a block limit, 
    preventing infinite RAM expansion over long sessions.
    """
    # FIX: Neuter the timers to prevent background QThreads from 
    # causing a C++ segfault when the test tears down the window.
    monkeypatch.setattr(AIDevDashboard, "_init_timers", lambda self: None)
    
    # qtbot automatically handles widget instantiation and cleanup
    window = AIDevDashboard()
    qtbot.addWidget(window)
    
    # 1. Verify the architectural limit is set to 1000 lines
    limit = window.log_viewer.document().maximumBlockCount()
    assert limit == 1000, f"Expected memory limit of 1000, got {limit}"
    
    # 2. Simulate a heavy log flood (1500 lines)
    for i in range(1500):
        window.log_viewer.append(f"Simulated log payload line {i}")
        
    # 3. Mathematical Proof: The document must have discarded the oldest 500 lines
    current_blocks = window.log_viewer.document().blockCount()
    assert current_blocks == 1000, f"Memory leak detected! Expected 1000 blocks, got {current_blocks}"

def test_structlog_json_ingestion(qtbot, monkeypatch):
    """
    Verify the frontend correctly parses JSON logs and renders severity-based HTML,
    while maintaining fallback support for standard plaintext print statements.
    """
    monkeypatch.setattr(AIDevDashboard, "_init_timers", lambda self: None)
    window = AIDevDashboard()
    qtbot.addWidget(window)
    
    window.log_viewer.clear()
    
    # 1. Inject a mocked Structlog JSON payload (Simulating an Error)
    mock_log = json.dumps({
        "level": "error",
        "event": "Database connection failed",
        "timestamp": "2026-03-12T10:30:00Z"
    })
    window._on_project_log(mock_log)
    
    # 2. Verify HTML rendering triggered with the correct color and data
    html_output = window.log_viewer.toHtml()
    assert "#ff5555" in html_output  # Hex color for errors
    assert "Database connection failed" in html_output
    assert "2026-03-12T10:30:00Z" in html_output
    
    # 3. Inject a raw text payload (Simulating a standard print statement fallback)
    window._on_project_log("Standard stdout print statement")
    text_output = window.log_viewer.toPlainText()
    assert "Standard stdout print statement" in text_output

def test_deterministic_qthread_teardown(qtbot, monkeypatch):
    """
    Verify that closing the application explicitly cleans up running 
    background threads to prevent zombie processes and C++ segfaults.
    """
    monkeypatch.setattr(AIDevDashboard, "_init_timers", lambda self: None)
    window = AIDevDashboard()
    qtbot.addWidget(window)
    
    # 1. Inject a mocked active worker thread
    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    window.compile_worker = mock_worker
    
    # 2. Simulate the user clicking the "X" to close the window
    close_event = QCloseEvent()
    window.closeEvent(close_event)
    
    # 3. Mathematical Proof: The C++ teardown sequence MUST be executed
    mock_worker.requestInterruption.assert_called_once()
    mock_worker.quit.assert_called_once()
    mock_worker.wait.assert_called_once()
    
    # Ensure the event was eventually accepted so the window actually closes
    assert close_event.isAccepted()

def test_subprocess_creation_flags(monkeypatch):
    """
    Verify that on Windows, the subprocess is created with the 
    CREATE_NEW_PROCESS_GROUP flag to prevent OS-level zombie processes.
    """
    worker = ProjectRunnerWorker("dummy_script.py")
    
    with patch("subprocess.Popen") as mock_popen:
        # Mock path existence so the runner doesn't abort early
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
        
        # Mock the stdout iterator to immediately exit the read loop
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = [''] # Returns empty string to break the loop
        mock_popen.return_value = mock_process
        
        worker.run()
        
        # Verify Popen was called
        mock_popen.assert_called_once()
        kwargs = mock_popen.call_args[1]
        
        if sys.platform == "win32":
            assert "creationflags" in kwargs
            assert kwargs["creationflags"] == subprocess.CREATE_NEW_PROCESS_GROUP

from main import APIWorker

def test_ipc_bearer_token_injection(monkeypatch):
    """
    Verify that the APIWorker securely reads the local IPC token
    and injects it into the Authorization header of every request.
    """
    from unittest.mock import patch, MagicMock
    
    # 1. Mock the file system to pretend the .daemon_token file exists
    monkeypatch.setattr("main.Path.exists", lambda self: True)
    monkeypatch.setattr("main.Path.read_text", lambda *args, **kwargs: "secure_ipc_token_123")
    
    worker = APIWorker("http://fake-url", method="GET")
    
    with patch("main.httpx.Client") as mock_client_class:
        # Setup the deep mock for the context manager and the get() method
        mock_client_instance = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_client_instance.get.return_value = mock_response
        
        worker.run()
        
        # 2. Verify the GET request was made with the strict Authorization header
        mock_client_instance.get.assert_called_once()
        kwargs = mock_client_instance.get.call_args[1]
        
        assert "headers" in kwargs
        assert kwargs["headers"]["Authorization"] == "Bearer secure_ipc_token_123"