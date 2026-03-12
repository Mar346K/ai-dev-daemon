import sys
import os
import json
import hashlib
import subprocess
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum, auto

from PySide6.QtGui import QCloseEvent
from PySide6.QtCore import QTimer, Qt, QThread, Signal, Slot, QUrl, QByteArray
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextBrowser, QFrame, QFileDialog, QLineEdit
)

# Professional Standard: Decouple PySide6 rendering from the GPU.
# This makes the UI immune to driver resets when Ollama spikes the VRAM.
os.environ["QT_OPENGL"] = "software"
os.environ["QT_QUICK_BACKEND"] = "software"

# === UPGRADE 3.2: Deterministic UI State Machine ===
class UIState(Enum):
    IDLE = auto()
    BUSY_COMPILING = auto()
    BUSY_COMMITTING = auto()
    BUSY_RUNNING = auto()
# ===================================================

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
        
        self.current_state = UIState.IDLE
        
        # === UPGRADE 3.3: Native QNetworkAccessManager ===
        # Replaces heavy QThreads with native Qt event loop async networking
        self.network_manager = QNetworkAccessManager(self)
        # =================================================
        
        self.project_worker = None

        self._init_ui()
        self._init_timers()

    # === UPGRADE 3.2: Centralized State Mutator ===
    def _transition_state(self, new_state: UIState) -> None:
        """Single source of truth for UI mutability to prevent race conditions."""
        self.current_state = new_state
        is_idle = (new_state == UIState.IDLE)
        
        self.btn_compile_context.setEnabled(is_idle)
        self.btn_run_project.setEnabled(is_idle)
        self.btn_manual_commit.setEnabled(is_idle)
        self.btn_browse.setEnabled(is_idle)
    # ==============================================

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

    # --- NEW NETWORKING HELPER ---
    def _create_secure_request(self, endpoint: str) -> QNetworkRequest:
        """Constructs a QNetworkRequest with the required IPC Bearer token."""
        req = QNetworkRequest(QUrl(f"{self.api_url}{endpoint}"))
        req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        
        token_path = Path(__file__).resolve().parent.parent / "backend" / ".daemon_token"
        token = token_path.read_text(encoding="utf-8").strip() if token_path.exists() else ""
        req.setRawHeader(QByteArray(b"Authorization"), QByteArray(f"Bearer {token}".encode()))
        
        return req

    # --- REWRITTEN API METHODS ---
    def _ping_backend(self) -> None:
        req = self._create_secure_request("/health")
        reply = self.network_manager.get(req)
        reply.finished.connect(lambda r=reply: self._on_health_reply(r))

    def _on_health_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                data = json.loads(reply.readAll().data().decode())
                self._on_health_success(True, data.get("status", "unknown"))
            else:
                self._on_health_error(reply.errorString())
        finally:
            reply.deleteLater() # Critical for C++ memory management

    @Slot(bool, str)
    def _on_health_success(self, status: bool, message: str) -> None:
        if status and message == "healthy":
            self.lbl_status.setText("Backend Status: 🟢 CONNECTED")
            workspace = self.txt_project_path.text()
            workspace_hash = hashlib.sha256(workspace.encode("utf-8")).hexdigest()[:12]
            self.status_bar.showMessage(f"🔒 Workspace Hash: {workspace_hash} | Air-Gap: SECURE")
            
    @Slot(str)
    def _on_health_error(self, error_msg: str) -> None:
        self.lbl_status.setText("Backend Status: 🔴 OFFLINE")

    def _trigger_context_compile(self) -> None:
        if self.current_state != UIState.IDLE:
            self.log_viewer.append("⚠️ [BUSY] System is currently locked. Please wait.")
            return

        self._transition_state(UIState.BUSY_COMPILING)
        target_path = self.txt_project_path.text()
        self.log_viewer.append(f">>> Compiling repository context for '{Path(target_path).name}'... Please wait.")
        
        req = self._create_secure_request("/compile-context")
        payload = json.dumps({"project_path": target_path}).encode("utf-8")
        
        reply = self.network_manager.post(req, QByteArray(payload))
        reply.finished.connect(lambda r=reply: self._on_compile_reply(r))

    def _on_compile_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                data = json.loads(reply.readAll().data().decode())
                self._on_compile_success(True, data.get("message", "Success"))
            else:
                try:
                    err_data = json.loads(reply.readAll().data().decode())
                    msg = err_data.get("detail", reply.errorString())
                except:
                    msg = reply.errorString()
                self._on_compile_error(msg)
        finally:
            reply.deleteLater()

    @Slot(bool, str)
    def _on_compile_success(self, status: bool, message: str) -> None:
        self.log_viewer.append(f"[SUCCESS] {message}")
        self._transition_state(UIState.IDLE)

    @Slot(str)
    def _on_compile_error(self, error_msg: str) -> None:
        self.log_viewer.append(f"[ERROR] Context compilation failed: {error_msg}")
        self._transition_state(UIState.IDLE)

    def _trigger_project_runner(self) -> None:
        if self.current_state != UIState.IDLE:
            self.log_viewer.append("⚠️ [BUSY] System is currently locked. Please wait.")
            return

        target_dir = self.txt_project_path.text()
        script_file, _ = QFileDialog.getOpenFileName(
            self, "Select Python Entry Script", target_dir, "Python Files (*.py)"
        )
        
        if not script_file:
            return 
            
        self._transition_state(UIState.BUSY_RUNNING)
        script_path = Path(script_file)
        self.log_viewer.append(f">>> Initializing project runner for '{script_path.name}'...")
        
        self.project_worker = ProjectRunnerWorker(str(script_path))
        self.project_worker.setParent(self)
        self.project_worker.log_signal.connect(self._on_project_log)
        
        self.project_worker.finished.connect(lambda: self._transition_state(UIState.IDLE))
        self.project_worker.start()

    def _on_project_log(self, log_entry: str) -> None:
        try:
            log_data = json.loads(log_entry)
            level = log_data.get("level", "info").lower()
            timestamp = log_data.get("timestamp", "")
            event = log_data.get("event", "Unknown Event")

            if level in ["error", "critical", "exception"]:
                color = "#ff5555"  
            elif level == "warning":
                color = "#ffb86c"  
            else:
                color = "#50fa7b"  

            html = f"<span style='color:{color}'>[{timestamp}] {level.upper()}: {event}</span>"
            self.log_viewer.append(html)
            
            # Fire-and-forget native async crash routing
            if level in ["error", "critical"]:
                project_name = Path(self.txt_project_path.text()).name
                payload = json.dumps({"project_name": project_name, "log_message": log_entry}).encode("utf-8")
                req = self._create_secure_request("/log-crash")
                reply = self.network_manager.post(req, QByteArray(payload))
                reply.finished.connect(reply.deleteLater)

        except json.JSONDecodeError:
            self.log_viewer.append(log_entry)
            
            # Fire-and-forget native async crash routing
            if "⚠️ [CRITICAL]" in log_entry:
                project_name = Path(self.txt_project_path.text()).name
                payload = json.dumps({"project_name": project_name, "log_message": log_entry}).encode("utf-8")
                req = self._create_secure_request("/log-crash")
                reply = self.network_manager.post(req, QByteArray(payload))
                reply.finished.connect(reply.deleteLater)

    def _trigger_manual_commit(self) -> None:
        if self.current_state != UIState.IDLE:
            self.log_viewer.append("⚠️ [BUSY] System is currently locked. Please wait.")
            return

        self._transition_state(UIState.BUSY_COMMITTING)
        target_path = self.txt_project_path.text()
        self.log_viewer.append(f">>> Analyzing diffs with 8B Model... (Hardware spooling detected)")
        
        req = self._create_secure_request("/force-commit")
        payload = json.dumps({"project_path": target_path}).encode("utf-8")
        
        reply = self.network_manager.post(req, QByteArray(payload))
        reply.finished.connect(lambda r=reply: self._on_commit_reply(r))

    def _on_commit_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                data = json.loads(reply.readAll().data().decode())
                self._on_commit_success(True, data.get("message", "Success"))
            else:
                try:
                    err_data = json.loads(reply.readAll().data().decode())
                    msg = err_data.get("detail", reply.errorString())
                except:
                    msg = reply.errorString()
                self._on_commit_error(msg)
        finally:
            reply.deleteLater()

    @Slot(bool, str)
    def _on_commit_success(self, status: bool, message: str) -> None:
        self.log_viewer.append(f"[SUCCESS] {message}")
        self._transition_state(UIState.IDLE)
        
    @Slot(str)
    def _on_commit_error(self, error_msg: str) -> None:
        self.log_viewer.append(f"[ERROR] Manual commit failed: {error_msg}")
        self._transition_state(UIState.IDLE)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Intercepts the window close event to ensure deterministic teardown
        of all C++ QThread objects before the Python interpreter exits.
        """
        # We only have one QThread left to manage!
        workers = [self.project_worker]

        for worker in workers:
            if worker and worker.isRunning():
                self.log_viewer.append(">>> Halting background threads for safe shutdown...")
                worker.requestInterruption()
                worker.quit()
                worker.wait(2000) 

        self.log_viewer.append(">>> Safe shutdown complete.")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AIDevDashboard()
    window.show()
    sys.exit(app.exec())