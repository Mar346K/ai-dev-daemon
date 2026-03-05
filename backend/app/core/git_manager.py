import git
from pathlib import Path
from app.core.security import redact_secrets_in_file

class GitManager:
    """
    Handles Git operations, diff extraction, and pre-staging DevSecOps checks.
    """
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        try:
            self.repo = git.Repo(self.repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            self.repo = git.Repo.init(self.repo_path)

    def process_and_stage_changes(self) -> None:
        """
        Iterates over untracked and modified files, runs the security redaction,
        and stages them. Respects .gitignore automatically via GitPython.
        """
        changed_files = [item.a_path for item in self.repo.index.diff(None)]
        untracked_files = self.repo.untracked_files
        
        all_files_to_process = set(changed_files + untracked_files)

        for file_str in all_files_to_process:
            file_path = self.repo_path / file_str
            if file_path.is_file():
                redact_secrets_in_file(file_path)
                self.repo.git.add(file_str)