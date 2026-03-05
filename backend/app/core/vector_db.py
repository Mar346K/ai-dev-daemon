import os
# Professional Standard: Hard-kill telemetry at the OS environment level before Chroma loads
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import httpx
import chromadb
from chromadb.config import Settings
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

class OllamaEmbeddingAdapter(EmbeddingFunction):
    """
    Custom Adapter Pattern to interface with local Ollama embeddings.
    """
    def __init__(self, url: str = "http://localhost:11434/api/embeddings", model_name: str = "nomic-embed-text"):
        self.url = url
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        """
        Required protocol method for ChromaDB. 
        """
        embeddings = []
        with httpx.Client(timeout=30.0) as client:
            for text in input:
                response = client.post(
                    self.url,
                    json={"model": self.model_name, "prompt": text}
                )
                response.raise_for_status()
                embeddings.append(response.json()["embedding"])
        return embeddings

class DualBrainDB:
    """
    Manages the Ephemeral (In-Memory) and Persistent ChromaDB instances.
    Enforces the debugging loop detection logic using local Ollama embeddings.
    """
    def __init__(self, persist_directory: str = "./chroma_data"):
        self.ef = OllamaEmbeddingAdapter(
            url="http://localhost:11434/api/embeddings",
            model_name="nomic-embed-text",
        )
        
        self.session_client = chromadb.Client(Settings(anonymized_telemetry=False))
        
        # Professional Standard: Force a clean state to prevent State Leakage
        try:
            self.session_client.delete_collection("active_session")
        except Exception:
            pass # Collection doesn't exist yet, which is fine
            
        self.session_collection = self.session_client.create_collection(
            name="active_session",
            embedding_function=self.ef
        )
        
        os.makedirs(persist_directory, exist_ok=True)
        self.persistent_client = chromadb.PersistentClient(
            path=persist_directory, 
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.architecture_collection = self.persistent_client.get_or_create_collection(
            name="project_architecture",
            embedding_function=self.ef
        )

    def log_diff(self, commit_hash: str, diff_text: str) -> None:
        """
        Logs a code change to the ephemeral session database for loop tracking.
        """
        self.session_collection.add(
            ids=[commit_hash],
            documents=[diff_text],
            metadatas=[{"type": "diff"}]
        )

    # UPDATED THRESHOLD: 120.0 based on diagnostic measurements
    def detect_debugging_loop(self, current_diff: str, threshold: float = 120.0, match_limit: int = 3) -> bool:
        """
        Queries the in-memory database to determine if the developer is making
        highly similar logic changes repeatedly.
        """
        if self.session_collection.count() < match_limit:
            return False
            
        results = self.session_collection.query(
            query_texts=[current_diff],
            n_results=match_limit
        )
        
        if not results["distances"] or not results["distances"][0]:
            return False
            
        close_matches = [dist for dist in results["distances"][0] if dist < threshold]
        
        return len(close_matches) >= match_limit