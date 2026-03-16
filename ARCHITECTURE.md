# Architectural Overview: AI Dev Daemon

The AI Dev Daemon is a local, zero-trust DevSecOps control center. It is designed to physically isolate telemetry, prevent user-data leakage to cloud LLMs, and provide real-time, self-healing crash analysis through an asynchronous local architecture.

This document details the system design, memory management, and security boundaries that enable the daemon to operate as a completely "ghosted" observer over target workflows.

---

## 1. System Topology & Zero-Trust IPC

The daemon operates via a decoupled architecture: a strictly typed PySide6 C++ UI frontend and a high-performance Python FastAPI backend.

* **Loopback Isolation:** The frontend and backend communicate exclusively over `localhost`. 
* **Bearer-Token Authentication:** To prevent unauthorized scripts or malicious local actors from hijacking the backend API, all IPC requests require a cryptographic bearer token generated at runtime.
* **Cryptographic Air-Gap Indicator:** The UI continuously hashes (SHA-256) the active target workspace directory. This mathematically proves to the operator that the daemon is correctly isolated and aligned with the designated environment.

---

## 2. Frontend: The PySide6 Control Center

The UI is built to survive hostile process crashes and heavy GPU spooling without dropping frames or leaking memory.

* **Deterministic State Machine (`UIState`):** The application relies on a strict `Enum` state machine (`IDLE`, `BUSY_COMPILING`, `BUSY_RUNNING`). This centralized mutator locks UI components to definitively prevent multi-thread race conditions.
* **Native Async Networking:** Heavy Python `QThread` network calls were deprecated in favor of Qt's native C++ `QNetworkAccessManager`. This allows for zero-blocking, fire-and-forget telemetry routing directly to the backend.
* **Subprocess Zombie Prevention:** Target Python scripts are executed in isolated OS-level process groups (`CREATE_NEW_PROCESS_GROUP` on Windows). If the daemon experiences a hard crash, the child processes are forcefully dragged down with it, preventing silent memory leaks.
* **Dual-Pane Analytics:** The UI is split via `QTabWidget`:
    * *Operator Console:* Handles real-time subprocess stdout/stderr, utilizing a 1000-block ring-buffer to prevent RAM overflow during infinite loops.
    * *Context & Audit:* A dedicated, read-only viewer for securely reviewing the compiled LLM context payloads and tracking active security intercept metrics.

---

## 3. Backend: Telemetry & The AI Healer

The FastAPI backend acts as the secure router between the local file system, the crash telemetry, and the local `llama3.1` (8B) model.

* **Asynchronous Telemetry Debouncer:** A custom `asyncio` buffer intercepts multi-line Tracebacks from the frontend. It holds the lines in memory for 1.5 seconds, gluing the Traceback into a single, unified payload before dispatching it to the LLM. This prevents the LLM from hallucinating on fragmented error logs.
* **Segmented Telemetry Routing:** Utilizing `structlog`, all project crashes and context dumps are dynamically routed to isolated directories (`logs/{project_name}/`). The daemon leaves absolutely zero footprint (no hidden files or folders) inside the target user's workspace.
* **Dynamic `.gitignore` Inheritance:** The Context Compiler leverages the `pathspec` library to dynamically read and adopt the target project's `.gitignore` rules (using native `gitignore` syntax matching). This mathematically guarantees that developer secrets, `.env` files, and heavy binaries are never scraped into the AI context window.
* **Real-Time Security Metrics:** A global `SECURITY_INTERCEPT_COUNT` continuously tracks how many times the backend successfully scrubs an API key or secret from the context pipeline, exposing this metric to the frontend via a dedicated `/metrics` endpoint.