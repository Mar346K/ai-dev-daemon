# AI Dev Daemon 🧠⚙️

A local, AI-powered developer dashboard and autonomous version control daemon. Designed to eliminate context-switching by automating Git commits, compiling repository context, tracking active debugging loops in memory, and enforcing strict DevSecOps security boundaries before any code reaches the LLM.

## 🏗️ System Architecture & Features

This system is built with an asynchronous, API-first client-server architecture, strictly separating the native desktop frontend from the heavy backend AI processing and state management.

* **Zero-Trust DevSecOps Pipeline:** Enforces cryptographic path jailing to prevent directory traversal, global HTTP error masking to prevent stack-trace leaks, and an aggressive **Halt-and-Catch-Fire (HCF)** secret scanner that instantly aborts operations if hardcoded credentials are detected.
* **Hardware-Aware Graceful Degradation:** Integrates OS-level `psutil` circuit breakers. If system RAM or compute pressure reaches critical thresholds, the API rejects AI routing requests with a 503, protecting the host machine from out-of-memory driver crashes.
* **RAM-Bound Ephemeral Vector State:** Utilizes a completely in-memory ChromaDB instance to track current debugging sessions. This prevents cross-session state leakage and eliminates disk I/O bottlenecks when the 70B architectural model detects logic loops.
* **Prompt Injection Fencing:** Untrusted user code and Git diffs are strictly wrapped in neutralized XML tags before being passed to local models, neutralizing injection escape attempts.
* **Zero-Cost Context Compiler:** Instantly packages entire repository architectures into a sanitized, LLM-ready Markdown payload while actively blocking heavy virtual environments, binary databases (`.sqlite3`), and `.git` folders.
* **Hardware-Decoupled Native UI (PySide6):** A multi-threaded dashboard running entirely on software rendering. This explicitly decouples the UI from the GPU, maintaining a fluid interface even when local LLMs max out hardware compute.

## 🛠️ Tech Stack

* **Frontend:** PySide6 (Qt for Python)
* **Backend:** FastAPI, Uvicorn, Pydantic-Settings
* **AI & State:** Ollama (Llama 3.1 8B, Llama 3.3 70B), ChromaDB Ephemeral
* **Concurrency & I/O:** AnyIO (Async Threading), QThread, Subprocess
* **Observability:** Structlog (JSON Structured Logging)
* **DevSecOps:** Docker (Least-Privilege Containerization), Pytest-Asyncio

## 🚀 Getting Started

### Prerequisites
* Python 3.13+
* [Ollama](https://ollama.com/) installed and running locally.
* Required Local Models: 
  * `ollama pull llama3.1` (Rapid commit generation)
  * `ollama pull llama3.3:70b` (Deep architectural review)
  * `ollama pull nomic-embed-text` (Vector embedding)

### 1. Installation

Clone the repository and set up your virtual environment:
```bash
git clone [https://github.com/Mar346k/ai-dev-daemon.git](https://github.com/Mar346k/ai-dev-daemon.git)
cd ai-dev-daemon

python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
```
Install both backend and frontend dependencies:

```Bash
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

### 2. Configuration & Security
The daemon utilizes strict path jailing. You must define your authorized workspace, or the API will block all file access.

Create a .env file inside the backend/ directory:

```Bash
# backend/.env
DAEMON_WORKSPACE=C:\Path\To\Your\Projects
```

### 3. Execution
The system requires both the backend API and the frontend UI to be running simultaneously.

* Start the AI Backend:
Open a terminal, activate your environment, and run the ASGI server:

```Bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

* Launch the Control Center:
Open a second terminal, activate your environment, and launch the PySide6 dashboard:

```Bash
cd frontend
python main.py
```

🔒 Security Posture
This system operates under a strict Halt-and-Catch-Fire security protocol. Unlike legacy tools that silently mutate or redact code, if this daemon detects a leaked API key or secret in your Git diff, the entire pipeline violently aborts, throws a 400 Bad Request, and refuses to stage the commit. This forces developers to utilize environment variables rather than relying on automated redaction safety nets.