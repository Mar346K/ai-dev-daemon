import sys
import subprocess
import re
import time
from datetime import datetime, timezone
import httpx
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextBrowser, QFrame
)
from PySide6.QtCore import QTimer, Qt, QThread, Signal

class APIWorker(QThread):
    """Background worker thread to handle HTTP requests."""
    success_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, url: str, method: str = "GET"):
        super().__init__()
        self.url = url
        self.method = method

    def run(self) -> None:
        try:
            with httpx.Client(timeout=10.0) as client:
                if self.method == "GET":
                    response = client.get(self.url)
                elif self.method == "POST":
                    response = client.post(self.url)
                response.raise_for_status()
                self.success_signal.emit(response.json())
        except Exception as e:
            self.error_signal.emit(str(e))

class ProjectRunnerWorker(QThread):
    """
    Executes a target python script as a subprocess. Pipes stdout/stderr,
    filters out noise via Regex, and deduplicates rapid-fire identical errors.
    """
    log_signal = Signal(str)
    
    def __init__(self, target_script: str):
        super().__init__()
        self.target_script = target_script
        self.is_running = True
        self.error_pattern = re.compile(r"(?i)(traceback|exception|error)")
        
        self.last_error_msg = ""
        self.last_error_time = 0.0

    def run(self) -> None:
        from pathlib import Path
        import sys
        
        try:
            # Professional Standard: Absolute Path Resolution & Verification
            script_path = Path(self.target_script).resolve()
            
            if not script_path.exists():
                self.log_signal.emit(f"⚠️ [CRITICAL] Execution Aborted: File not found at {script_path}")
                return

            # Professional Standard: Use sys.executable to lock the environment, and cwd to lock the directory
            process = subprocess.Popen(
                [sys.executable, "-u", str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, 
                text=True,
                bufsize=1,
                cwd=str(script_path.parent) 
            )
            
            self.log_signal.emit(f">>> Target project '{script_path.name}' launched.")
            
            for line in iter(process.stdout.readline, ''):
                if not self.is_running:
                    process.terminate()
                    break
                    
                line = line.strip()
                if not line:
                    continue
                    
                if self.error_pattern.search(line):
                    current_time = time.time()
                    
                    if line == self.last_error_msg and (current_time - self.last_error_time) < 2.0:
                        continue
                        
                    self.last_error_msg = line
                    self.last_error_time = current_time
                    self.log_signal.emit(f"⚠️ [CRITICAL] {line}")
                    
            self.log_signal.emit(f">>> Target project '{script_path.name}' terminated.")
            
        except Exception as e:
             self.log_signal.emit(f"⚠️ [CRITICAL] Subprocess failed: {e}")

class AIDevDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Dev Daemon - Control Center")
        self.resize(900, 600)
        
        self.session_start_time = datetime.now(timezone.utc)
        self.api_url = "http://localhost:8000"

        self._init_ui()
        self._init_timers()

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_bar = QHBoxLayout()
        self.lbl_status = QLabel("Backend Status: 🔴 OFFLINE")
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.lbl_timer = QLabel("Active Session: 00:00:00")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_timer.setStyleSheet("font-family: monospace; font-size: 14px;")
        
        top_bar.addWidget(self.lbl_status)
        top_bar.addWidget(self.lbl_timer)
        main_layout.addLayout(top_bar)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        self.log_viewer = QTextBrowser()
        self.log_viewer.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: monospace;")
        self.log_viewer.append(">>> UI Initialized. Awaiting backend connection...")
        main_layout.addWidget(self.log_viewer)

        bottom_bar = QHBoxLayout()
        self.btn_compile_context = QPushButton("Compile Context (Markdown)")
        self.btn_run_project = QPushButton("Run Active Project (Track Logs)")
        self.btn_manual_commit = QPushButton("Force Manual Commit")
        
        for btn in [self.btn_compile_context, self.btn_run_project, self.btn_manual_commit]:
            btn.setMinimumHeight(40)
            bottom_bar.addWidget(btn)
            
        main_layout.addLayout(bottom_bar)
        
        self.btn_compile_context.clicked.connect(self._trigger_context_compile)
        self.btn_run_project.clicked.connect(self._trigger_project_runner)

    def _init_timers(self) -> None:
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_session_clock)
        self.clock_timer.start(1000)

        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self._ping_backend)
        self.health_timer.start(5000)
        self._ping_backend()

    def _update_session_clock(self) -> None:
        now = datetime.now(timezone.utc)
        delta = now - self.session_start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.lbl_timer.setText(f"Active Session: {hours:02d}:{minutes:02d}:{seconds:02d}")

    def _ping_backend(self) -> None:
        self.health_worker = APIWorker(f"{self.api_url}/health")
        self.health_worker.success_signal.connect(self._on_health_success)
        self.health_worker.error_signal.connect(self._on_health_error)
        self.health_worker.start()

    def _on_health_success(self, data: dict) -> None:
        if data.get("status") == "healthy":
            self.lbl_status.setText("Backend Status: 🟢 CONNECTED")
            
    def _on_health_error(self, error_msg: str) -> None:
        self.lbl_status.setText("Backend Status: 🔴 OFFLINE")

    def _trigger_context_compile(self) -> None:
        self.log_viewer.append(">>> Compiling repository context... Please wait.")
        self.btn_compile_context.setEnabled(False) 
        
        self.compile_worker = APIWorker(f"{self.api_url}/compile-context", method="POST")
        self.compile_worker.success_signal.connect(self._on_compile_success)
        self.compile_worker.error_signal.connect(self._on_compile_error)
        self.compile_worker.start()

    def _on_compile_success(self, data: dict) -> None:
        self.log_viewer.append(f"[SUCCESS] {data.get('message')}")
        self.btn_compile_context.setEnabled(True)

    def _on_compile_error(self, error_msg: str) -> None:
        self.log_viewer.append(f"[ERROR] Context compilation failed: {error_msg}")
        self.btn_compile_context.setEnabled(True)

    def _trigger_project_runner(self) -> None:
        """Launches the smart telemetry subprocess."""
        self.log_viewer.append(">>> Initializing project runner with Smart Telemetry...")
        
        # We target a dummy script in the root folder for testing
        self.project_worker = ProjectRunnerWorker("../test_crash.py")
        self.project_worker.log_signal.connect(self._on_project_log)
        self.project_worker.start()

    def _on_project_log(self, log_entry: str) -> None:
        """Appends intercepted subprocess logs to the UI."""
        self.log_viewer.append(log_entry)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AIDevDashboard()
    window.show()
    sys.exit(app.exec())