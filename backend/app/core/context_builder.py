import os
from pathlib import Path
from datetime import datetime, timezone
import pathspec

class ContextCompiler:
    """
    Scans the repository and aggregates all relevant code and directory structures
    into a single Markdown file optimized for LLM context ingestion.
    """
    def __init__(self, root_path: str = ".."):
        self.root_path = Path(root_path).resolve()
        
        self.exclude_dirs = {
            ".venv", "venv", "env", "__pycache__", ".git", 
            "chroma_data", ".pytest_cache", "node_modules"
        }
        self.exclude_exts = {
            ".pyc", ".db", ".sqlite3", ".exe", ".dll", ".so", ".md", ".log"
        }
        
        # === V2 UPGRADE: Dynamic .gitignore parsing ===
        self.gitignore_spec = self._load_gitignore()

    def _load_gitignore(self) -> pathspec.PathSpec:
        """Reads the target project's .gitignore to inherit its rules."""
        gitignore_path = self.root_path / ".gitignore"
        if gitignore_path.exists():
            lines = gitignore_path.read_text(encoding="utf-8").splitlines()
            # === V2 FIX: Updated from deprecated 'gitwildmatch' to 'gitignore' ===
            return pathspec.PathSpec.from_lines('gitignore', lines)
        return pathspec.PathSpec.from_lines('gitignore', [])

    def _is_ignored(self, path: Path) -> bool:
        """Checks if a given path matches the dynamic .gitignore rules."""
        try:
            rel_path = str(path.relative_to(self.root_path)).replace("\\", "/")
        except ValueError:
            return False
            
        # pathspec relies on trailing slashes to correctly identify ignored directories
        if path.is_dir() and not rel_path.endswith('/'):
            rel_path += '/'
            
        return self.gitignore_spec.match_file(rel_path)

    def _generate_tree(self, directory: Path, prefix: str = "") -> str:
        """Recursively builds a string representation of the directory tree."""
        tree_str = ""
        try:
            items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name))
        except PermissionError:
            return ""

        # Filter out hardcoded excluded directories AND dynamically gitignored paths
        valid_items = []
        for item in items:
            if item.is_dir() and item.name in self.exclude_dirs:
                continue
            if item.is_file() and item.suffix in self.exclude_exts:
                continue
            if self._is_ignored(item):
                continue
            valid_items.append(item)

        for index, item in enumerate(valid_items):
            connector = "└── " if index == len(valid_items) - 1 else "├── "
            tree_str += f"{prefix}{connector}{item.name}\n"
            
            if item.is_dir():
                extension = "    " if index == len(valid_items) - 1 else "│   "
                tree_str += self._generate_tree(item, prefix=prefix + extension)
                
        return tree_str

    def _gather_code_contents(self) -> str:
        """Reads all valid files and formats them into Markdown code blocks."""
        code_str = ""
        for root, dirs, files in os.walk(self.root_path):
            root_path_obj = Path(root)
            
            # Modify dirs in-place to skip excluded/ignored directories early
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs and not self._is_ignored(root_path_obj / d)]
            
            for file in files:
                file_path = root_path_obj / file
                if file_path.suffix in self.exclude_exts:
                    continue
                if self._is_ignored(file_path):
                    continue
                    
                rel_path = file_path.relative_to(self.root_path)
                
                try:
                    content = file_path.read_text(encoding="utf-8")
                    code_str += f"\n### File: `{rel_path}`\n"
                    lang = "python" if file_path.suffix == ".py" else ""
                    code_str += f"```{lang}\n{content}\n```\n"
                except Exception as e:
                    code_str += f"\n### File: `{rel_path}`\n*Error reading file: {e}*\n"
                    
        return code_str

    def compile(self) -> Path:
        """Executes the build process and writes the context dump."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        header = f"# AI Developer Context Dump\n*Generated: {timestamp}*\n\n"
        
        tree_section = "## Directory Tree\n```text\n"
        tree_section += f"{self.root_path.name}/\n"
        tree_section += self._generate_tree(self.root_path)
        tree_section += "```\n\n"
        
        code_section = "## Source Code\n"
        code_section += self._gather_code_contents()
        
        full_markdown = header + tree_section + code_section
        output_file = self.root_path / "llm_context_dump.md"
        output_file.write_text(full_markdown, encoding="utf-8")
        
        return output_file