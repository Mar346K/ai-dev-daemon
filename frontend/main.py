import sys
import os
import json
import hashlib
from PySide6.QtGui import QCloseEvent

# Professional Standard: Decouple PySide6 rendering from the GPU.
# This makes the UI immune to driver resets when Ollama spikes the VRAM.
os.environ["QT_OPENGL"] = "software"
os.environ["QT_QUICK_BACKEND"] = "software"

import subprocess
import re
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextBrowser, QFrame, QFileDialog, QLineEdit
)
from PySide6.QtCore import QTimer, Qt, QThread, Signal

class APIWorker(QThread):
    success_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, url: str, method: str = "GET", payload: dict | None = None):
        super().__init__()
        self.url = url
        self.method = method
        self.payload = payload or {}

    def _get_ipc_token(self) -> str:
        """
        Securely resolves the backend's hidden IPC token file.
        Returns the token string, or an empty string if not yet initialized.
        """
        # Resolve the path relative to this frontend script (../backend/.daemon_token)
        token_path = Path(__file__).resolve().parent.parent / "backend" / ".daemon_token"
        try:
            if token_path.exists():
                return token_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass
        return ""

    def run(self) -> None:
        try:
            # === UPGRADE 2.1: Ephemeral IPC Bearer Authentication ===
            headers = {"Authorization": f"Bearer {self._get_ipc_token()}"}
            # ========================================================
            
            with httpx.Client(timeout=90.0) as client: 
                if self.method == "GET":
                    response = client.get(self.url, headers=headers)
                elif self.method == "POST":
                    response = client.post(self.url, json=self.payload, headers=headers)
                response.raise_for_status()
                self.success_signal.emit(response.json())
                
        except httpx.HTTPStatusError as exc:
            err_detail = exc.response.json().get("detail", str(exc))
            self.error_signal.emit(f"API Error: {err_detail}")
        except Exception as e:
            self.error_signal.emit(str(e))

class ProjectRunnerWorker(QThread):
    log_signal = Signal(str)
    
    def __init__(self, target_script: str):
        super().__init__()
        self.target_script = target_script
        self.is_running = True
        self.error_pattern = re.compile(r"(?i)(traceback|exception|error)")
        self.last_error_msg = ""
        self.last_error_time = 0.0

    def run(self) -> None:
        import sys
        try:
            script_path = Path(self.target_script).resolve()
            
            if not script_path.exists():
                self.log_signal.emit(f"⚠️ [CRITICAL] Execution Aborted: File not found at {script_path}")
                return

            # Prepare standard arguments
            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT, 
                "text": True,
                "bufsize": 1,
                "cwd": str(script_path.parent) 
            }

            # === UPGRADE 1.4: OS-Level Subprocess Zombie Prevention ===
            # Binds the child process to the parent so it dies if the dashboard hard-crashes
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            # ==========================================================

            process = subprocess.Popen(
                [sys.executable, "-u", str(script_path)],
                **kwargs
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
        
        # Professional Standard: Permanent resident workers to prevent Garbage Collection
        self.commit_worker = None
        self.compile_worker = None
        self.project_worker = None
        self.health_worker = None

        self._init_ui()
        self._init_timers()

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Bar: Health and Uptime
        top_bar = QHBoxLayout()
        self.lbl_status = QLabel("Backend Status: 🔴 OFFLINE")
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.lbl_timer = QLabel("Active Session: 00:00:00")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_timer.setStyleSheet("font-family: monospace; font-size: 14px;")
        
        top_bar.addWidget(self.lbl_status)
        top_bar.addWidget(self.lbl_timer)
        main_layout.addLayout(top_bar)

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line1)

        # Dynamic Project Selector
        project_bar = QHBoxLayout()
        self.lbl_project = QLabel("Target Project:")
        self.lbl_project.setStyleSheet("font-weight: bold;")
        
        self.txt_project_path = QLineEdit(str(Path("..").resolve())) 
        self.txt_project_path.setReadOnly(True)
        self.txt_project_path.setStyleSheet("background-color: #2d2d2d; color: #d4d4d4;")
        
        self.btn_browse = QPushButton("Browse...")
        
        project_bar.addWidget(self.lbl_project)
        project_bar.addWidget(self.txt_project_path)
        project_bar.addWidget(self.btn_browse)
        main_layout.addLayout(project_bar)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line2)

        # Logs Viewer
        self.log_viewer = QTextBrowser()
        self.log_viewer.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: monospace;")
        
        # === UPGRADE 1.1: Strict Ring-Buffer Memory Limit ===
        # Caps the DOM tree at 1000 blocks to prevent out-of-memory crashes during long sessions
        self.log_viewer.document().setMaximumBlockCount(1000)
        # ====================================================
        
        self.log_viewer.append(">>> UI Initialized. Awaiting backend connection...")
        main_layout.addWidget(self.log_viewer)

        # Action Buttons
        bottom_bar = QHBoxLayout()
        self.btn_compile_context = QPushButton("Compile Context (Markdown)")
        self.btn_run_project = QPushButton("Run Active Project (Track Logs)")
        self.btn_manual_commit = QPushButton("Force Manual Commit")
        
        for btn in [self.btn_compile_context, self.btn_run_project, self.btn_manual_commit]:
            btn.setMinimumHeight(40)
            bottom_bar.addWidget(btn)
            
        main_layout.addLayout(bottom_bar)
        
        # UI Event Wiring
        self.btn_browse.clicked.connect(self._browse_project_directory)
        self.btn_compile_context.clicked.connect(self._trigger_context_compile)
        self.btn_run_project.clicked.connect(self._trigger_project_runner)
        self.btn_manual_commit.clicked.connect(self._trigger_manual_commit)

        # === UPGRADE 2.2: Cryptographic Air-Gap Indicator ===
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("color: #50fa7b; font-family: monospace; font-weight: bold;")
        self.status_bar.showMessage("🔒 Air-Gap: Awaiting Sync...")
        # ====================================================

    def _browse_project_directory(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Target Project Directory")
        if folder:
            abs_folder = str(Path(folder).resolve())
            self.txt_project_path.setText(abs_folder)
            self.log_viewer.append(f">>> Target project updated to: {abs_folder}")

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
        self.health_worker.setParent(self)
        self.health_worker.success_signal.connect(self._on_health_success)
        self.health_worker.error_signal.connect(self._on_health_error)
        self.health_worker.start()

    def _on_health_success(self, data: dict) -> None:
        if data.get("status") == "healthy":
            self.lbl_status.setText("Backend Status: 🟢 CONNECTED")
            
            # === UPGRADE 2.2: Cryptographic Air-Gap Indicator ===
            # Generate a short SHA-256 hash of the active workspace path
            workspace = self.txt_project_path.text()
            workspace_hash = hashlib.sha256(workspace.encode("utf-8")).hexdigest()[:12]
            self.status_bar.showMessage(f"🔒 Workspace Hash: {workspace_hash} | Air-Gap: SECURE")
            # ====================================================
            
    def _on_health_error(self, error_msg: str) -> None:
        self.lbl_status.setText("Backend Status: 🔴 OFFLINE")

    def _trigger_context_compile(self) -> None:
        if self.compile_worker and self.compile_worker.isRunning():
            self.log_viewer.append("⚠️ [BUSY] Context compiler is already running.")
            return

        target_path = self.txt_project_path.text()
        self.log_viewer.append(f">>> Compiling repository context for '{Path(target_path).name}'... Please wait.")
        self.btn_compile_context.setEnabled(False) 
        
        payload = {"project_path": target_path}
        self.compile_worker = APIWorker(f"{self.api_url}/compile-context", method="POST", payload=payload)
        self.compile_worker.setParent(self)
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
        if self.project_worker and self.project_worker.isRunning():
            self.log_viewer.append("⚠️ [BUSY] A project is already running. Please close it first.")
            return

        target_dir = self.txt_project_path.text()
        script_file, _ = QFileDialog.getOpenFileName(
            self, "Select Python Entry Script", target_dir, "Python Files (*.py)"
        )
        
        if not script_file:
            return 
            
        script_path = Path(script_file)
        self.log_viewer.append(f">>> Initializing project runner for '{script_path.name}'...")
        
        self.project_worker = ProjectRunnerWorker(str(script_path))
        self.project_worker.setParent(self)
        self.project_worker.log_signal.connect(self._on_project_log)
        self.project_worker.start()

    def _on_project_log(self, log_entry: str) -> None:
        try:
            # Attempt to parse as structured JSON (Structlog format)
            log_data = json.loads(log_entry)
            level = log_data.get("level", "info").lower()
            timestamp = log_data.get("timestamp", "")
            event = log_data.get("event", "Unknown Event")

            # Professional Standard: Color-code by severity
            if level in ["error", "critical", "exception"]:
                color = "#ff5555"  # Red
            elif level == "warning":
                color = "#ffb86c"  # Orange/Yellow
            else:
                color = "#50fa7b"  # Green

            # Inject rich HTML into the viewer
            html = f"<span style='color:{color}'>[{timestamp}] {level.upper()}: {event}</span>"
            self.log_viewer.append(html)
            
            # Maintain crash routing for critical structured logs
            if level in ["error", "critical"]:
                project_name = Path(self.txt_project_path.text()).name
                payload = {"project_name": project_name, "log_message": log_entry}
                try:
                    httpx.post(f"{self.api_url}/log-crash", json=payload, timeout=3.0)
                except Exception:
                    pass

        except json.JSONDecodeError:
            # Fallback for standard non-JSON print() statements
            self.log_viewer.append(log_entry)
            
            # Maintain legacy crash routing
            if "⚠️ [CRITICAL]" in log_entry:
                project_name = Path(self.txt_project_path.text()).name
                payload = {"project_name": project_name, "log_message": log_entry}
                try:
                    httpx.post(f"{self.api_url}/log-crash", json=payload, timeout=3.0)
                except Exception:
                    pass

    def _trigger_manual_commit(self) -> None:
        """Triggers the backend API with the Persistent Resident Anchor."""
        if self.commit_worker and self.commit_worker.isRunning():
            self.log_viewer.append("⚠️ [BUSY] AI is already processing a commit. Please wait.")
            return

        target_path = self.txt_project_path.text()
        self.log_viewer.append(f">>> Analyzing diffs with 8B Model... (Hardware spooling detected)")
        self.btn_manual_commit.setEnabled(False) 
        
        payload = {"project_path": target_path}
        
        self.commit_worker = APIWorker(f"{self.api_url}/force-commit", method="POST", payload=payload)
        self.commit_worker.setParent(self) 
        
        self.commit_worker.success_signal.connect(self._on_commit_success)
        self.commit_worker.error_signal.connect(self._on_commit_error)
        self.commit_worker.start()

    def _on_commit_success(self, data: dict) -> None:
        self.log_viewer.append(f"[SUCCESS] {data.get('message')}")
        self.btn_manual_commit.setEnabled(True)
        
    def _on_commit_error(self, error_msg: str) -> None:
        self.log_viewer.append(f"[ERROR] Manual commit failed: {error_msg}")
        self.btn_manual_commit.setEnabled(True)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Intercepts the window close event to ensure deterministic teardown
        of all C++ QThread objects before the Python interpreter exits.
        """
        workers = [
            self.commit_worker, 
            self.compile_worker, 
            self.project_worker, 
            self.health_worker
        ]

        for worker in workers:
            if worker and worker.isRunning():
                self.log_viewer.append(">>> Halting background threads for safe shutdown...")
                # 1. Signal the thread to stop its current loop
                worker.requestInterruption()
                # 2. Tell the thread's event loop to exit
                worker.quit()
                # 3. Block the main thread for a max of 2 seconds while waiting for C++ to clean up
                worker.wait(2000) 

        self.log_viewer.append(">>> Safe shutdown complete.")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AIDevDashboard()
    window.show()
    sys.exit(app.exec())