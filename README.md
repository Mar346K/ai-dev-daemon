# AI Dev Daemon 🧠⚙️

A local, AI-powered developer dashboard and autonomous version control daemon. Designed to eliminate context-switching by automating Git commits, compiling repository context, and managing isolated crash telemetry through a hardware-aware native UI.

## 🏗️ System Architecture & Features

This system is built with an API-first client-server architecture, strictly separating the native desktop frontend from the heavy backend AI processing.

* **Hardware-Aware Native UI (PySide6):** A multi-threaded, asynchronous dashboard running entirely on software rendering. This explicitly decouples the UI from the GPU, preventing OS-level graphics driver crashes (TDR) when local LLMs max out VRAM.
* **Autonomous Version Control:** A background agent that extracts `git diffs`, scrubs them for hardcoded secrets, and leverages a local Llama 3.1 8B model to generate professional, one-line commit messages and stage files automatically.
* **Smart Telemetry & Crash Routing:** Executes target Python scripts in isolated subprocesses. It filters standard terminal noise using Regex, deduplicates rapid-fire exception tracebacks, and dynamically routes critical errors to isolated, project-specific log files.
* **Zero-Cost Context Compiler:** Instantly packages entire repository architectures into a sanitized, LLM-ready Markdown payload while actively blocking heavy virtual environments, `.git` folders, and binary databases.
* **API-First Backend (FastAPI):** A robust backend utilizing Pydantic for strict payload validation and lifespan context managers for memory-safe startup and shutdown sequences.

## 🛠️ Tech Stack

* **Frontend:** PySide6 (Qt for Python)
* **Backend:** FastAPI, Uvicorn, Pydantic
* **AI Engine:** Ollama (Llama 3.1 8B)
* **Version Control:** GitPython
* **Concurrency:** QThread (UI), Subprocess (Telemetry), Asyncio (API)

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* [Ollama](https://ollama.com/) installed and running locally.
* The `llama3.1` model pulled via Ollama (`ollama pull llama3.1`).

### Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Mar346k/ai-dev-daemon.git](https://github.com/Mar346k/ai-dev-daemon.git)
   cd ai-dev-daemon
   ```
   
2. Set up the environment:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   pip install -r frontend/requirements.txt
   ```

Execution
The system requires both the backend API and the frontend UI to be running simultaneously.

1. Start the AI Backend:
   Open a terminal, activate your environment, and run:

   ```Bash
   cd backend
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. Launch the Control Center:
   Open a second terminal, activate your environment, and run:

   ```Bash
   cd frontend
   python main.py
   ```
   
🔒 Security Note
This system performs automated pre-staging DevSecOps checks. It actively scans diffs using regex patterns to redact potential API keys and secrets before they are ever processed by the AI or committed to local history.
