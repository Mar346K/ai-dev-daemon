import git
from pathlib import Path
from app.core.security import redact_secrets_in_file
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

    def process_and_stage_changes(self) -> bool:
        """
        Iterates over untracked and modified files, runs the security redaction,
        and stages them. Returns True if files were staged.
        """
        changed_files = [item.a_path for item in self.repo.index.diff(None)]
        untracked_files = self.repo.untracked_files
        
        all_files_to_process = set(changed_files + untracked_files)
        
        if not all_files_to_process:
            return False

        for file_str in all_files_to_process:
            file_path = self.repo_path / file_str
            if file_path.is_file():
                redact_secrets_in_file(file_path)
                self.repo.git.add(file_str)
                
        return True

    def force_ai_commit(self) -> str:
        """
        Forces the pipeline to stage changes, generate an AI commit message 
        based on the diff, and commit the files.
        """
        self.process_and_stage_changes()
        
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