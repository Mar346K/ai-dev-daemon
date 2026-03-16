# AI Dev Daemon - Control Center

[![CI Pipeline](https://github.com/Mar346K/ai-dev-daemon/actions/workflows/ci.yml/badge.svg)](https://github.com/Mar346K/ai-dev-daemon/actions)


An enterprise-grade, local DevSecOps daemon designed to actively monitor Python processes, intercept system crashes, and utilize a local LLM to generate real-time root-cause analysis and actionable hotfixes—all within a completely air-gapped, offline environment.

📖 **For a deep dive into the system design, memory management, and zero-trust security boundaries, please read the [ARCHITECTURE.md](./ARCHITECTURE.md).**

## 🏗️ Architecture Overview

The system is split into a highly optimized PySide6 C++ UI and a high-performance asynchronous FastAPI backend, connected via strict IPC bearer-token authentication.

### Frontend: The Operator Dashboard (`/frontend`)
* **Strict C++ Boundary Typing:** PySide6 signals and slots are strictly typed with C++ primitives (`bool`, `str`) to prevent Python memory objects from corrupting the Qt event loop.
* **Deterministic State Machine:** A mathematically locked `UIState` enum (IDLE, BUSY_COMPILING, etc.) prevents race conditions and multi-click thread collisions.
* **Native Async Event Loop:** Bypasses heavy OS-level Python threads in favor of Qt's native `QNetworkAccessManager` for zero-blocking fire-and-forget telemetry.
* **Cryptographic Air-Gap Indicator:** Persistently hashes the target workspace directory via SHA-256 to provide real-time visual proof of local containment.
* **Structlog JSON Ingestion:** Features a 1000-block ring-buffer memory limit that dynamically parses JSON error logs and applies severity-based HTML rendering.
* **Zombie Process Prevention:** OS-level subprocess bindings ensure child processes die gracefully if the daemon experiences a hard crash.

### Backend: The AI Healer (`/backend`)
* **Asynchronous Telemetry Debouncer:** A custom `asyncio` 1.5-second buffer that catches rapid-fire, multi-line Python Tracebacks and merges them into a single, unified payload to prevent LLM hallucination.
* **Local AI Agentic Workflow:** Leverages `BackgroundTasks` to asynchronously spool up a local LLM for crash diagnosis without blocking the main FastAPI event loop.
* **Fire-and-Forget Security:** Catches unhandled exceptions, logs them securely to project-specific targets, and masks internal server errors from the client.

## 🖥️ Hardware Profile
This daemon is specifically optimized and tested for local AI inference with the following hardware specifications:
* **CPU:** Intel Core i7 (9th Gen)
* **RAM:** 128 GB
* **GPU:** Intel Arc A770 (16GB VRAM)
* **Model:** `llama3.1` (8B Parameters - fits entirely in VRAM for rapid response times)

## 🚀 Getting Started

### 1. Launch the Backend
Open a terminal, activate your backend virtual environment, and start the FastAPI server:
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

### 2. Launch the Frontend
Open a second terminal, activate the frontend virtual environment, and launch the Qt Dashboard:

```Bash
cd frontend
venv\Scripts\activate
python main.py
```
### 3. The DevSecOps Loop
Browse to your target project folder in the UI.

Ensure the bottom status bar reads 🟢 CONNECTED and displays the 🔒 Workspace Hash.

Run a target Python script.

If the script throws a critical exception, the daemon will instantly route the telemetry to the backend, trigger the local Ollama instance, and print an AI-generated hotfix (e.g., specific sed commands or code adjustments) directly to your backend console.
