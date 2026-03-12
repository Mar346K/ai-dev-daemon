import git
from pathlib import Path
from app.core.security import scan_file_for_secrets # <-- Updated import
from app.core.ai_router import AIRouter

class GitManager:
    """
    Handles Git operations, diff extraction, pre-staging DevSecOps checks,
    and AI-powered commit generation.
    """
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        try:
            self.repo = git.Repo(self.repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            self.repo = git.Repo.init(self.repo_path)
            
        self.ai_router = AIRouter()

    async def process_and_stage_changes(self) -> bool:
        # ...
        for file_str in all_files_to_process:
            file_path = self.repo_path / file_str
            if file_path.is_file():
                # MUST AWAIT the new async scanner
                await scan_file_for_secrets(file_path)
                self.repo.git.add(file_str)
                
        return True

    async def force_ai_commit(self) -> str:
        # ...
        # MUST AWAIT the staged changes function
        await self.process_and_stage_changes()
        # ... rest remains the same
        
        # Extract the exact code changes that are currently staged
        diff_text = self.repo.git.diff('--cached')
        
        if not diff_text.strip():
            return "No changes detected to commit."
            
        # Route the diff to the local 8B model for summarization
        commit_message = self.ai_router.generate_commit_message(diff_text)
        
        # Professional Standard: Sanitize AI output to prevent trailing quotes or markdown blocks
        commit_message = commit_message.strip().strip('"').strip("'")
        
        # Failsafe in case the model times out or returns empty
        if not commit_message:
            commit_message = "Auto-commit: System architecture updates."
            
        self.repo.index.commit(commit_message)
        return commit_message