import httpx
from typing import Optional
from app.core.system_optimizer import ResourceOptimizer
from app.core.system_optimizer import check_hardware_capacity

class AIRouter:
    """
    Handles tiered intelligence routing between the rapid 8B model 
    and the heavy 70B architectural model via the local Ollama API.
    """
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self.fast_model = "llama3.1:latest"
        self.heavy_model = "llama3.3:70b"

    def generate_commit_message(self, diff_text: str) -> str:
        # FENCE: Ensure we have the hardware capacity to run this request
        check_hardware_capacity()
        # Professional Standard: Use a system-style instruction to limit verbosity
        prompt = (
            "You are a senior software engineer. Write a one-line Git commit message "
            "summarizing the following diff. Output ONLY the message. No explanations, "
            f"no quotes, no markdown:\n\n{diff_text}"
        )
        return self._query_ollama(self.fast_model, prompt)

    def architectural_review(self, diff_text: str) -> Optional[str]:
        """
        Uses the heavy 70B model for deep review. 
        Only triggers if the system is idle. Flushes memory immediately after.
        """
        if not ResourceOptimizer.is_system_idle():
            # Professional Standard: Fail gracefully if the system is busy
            return None 

        prompt = f"Perform a deep architectural review of these code changes. Identify anti-patterns or structural flaws:\n\n{diff_text}"
        review = self._query_ollama(self.heavy_model, prompt, timeout=120.0)
        
        # Explicit resource cleanup: Evict the 42GB model from RAM immediately
        self.flush_model(self.heavy_model)
        
        return review

    def _query_ollama(self, model: str, prompt: str, timeout: float = 90.0) -> str:
        """Internal helper to execute Ollama API calls."""
        with httpx.Client(timeout=timeout) as client:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            try:
                response = client.post(f"{self.host}/api/generate", json=payload)
                response.raise_for_status()
                return response.json().get("response", "")
            except Exception as e:
                return f"Error querying {model}: {e}"

    def flush_model(self, model: str) -> bool:
        """
        Forces Ollama to unload the model from memory using keep_alive: 0.
        """
        with httpx.Client(timeout=10.0) as client:
            payload = {
                "model": model,
                "keep_alive": 0
            }
            try:
                response = client.post(f"{self.host}/api/generate", json=payload)
                response.raise_for_status()
                return True
            except Exception:
                return False