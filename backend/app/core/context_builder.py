import os
from pathlib import Path
from datetime import datetime, timezone

class ContextCompiler:
    """
    Scans the repository and aggregates all relevant code and directory structures
    into a single Markdown file optimized for LLM context ingestion.
    """
    def __init__(self, root_path: str = ".."):
        # We set root to ".." assuming the daemon runs from inside /backend
        self.root_path = Path(root_path).resolve()
        
        # Professional Standard: Strict exclusion lists to prevent massive payload bloat
        self.exclude_dirs = {
            ".venv", "venv", "env", "__pycache__", ".git", 
            "chroma_data", ".pytest_cache", "node_modules"
        }
        self.exclude_exts = {
            ".pyc", ".db", ".exe", ".dll", ".so", ".md", ".log"
        }

    def _generate_tree(self, directory: Path, prefix: str = "") -> str:
        """Recursively builds a string representation of the directory tree."""
        tree_str = ""
        try:
            items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name))
        except PermissionError:
            return ""

        # Filter out excluded directories
        valid_items = [
            item for item in items 
            if not (item.is_dir() and item.name in self.exclude_dirs)
            and not (item.is_file() and item.suffix in self.exclude_exts)
        ]

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
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix in self.exclude_exts:
                    continue
                    
                # Calculate relative path for clean headers
                rel_path = file_path.relative_to(self.root_path)
                
                try:
                    content = file_path.read_text(encoding="utf-8")
                    code_str += f"\n### File: `{rel_path}`\n"
                    # Use Python syntax highlighting if it's a .py file
                    lang = "python" if file_path.suffix == ".py" else ""
                    code_str += f"```{lang}\n{content}\n```\n"
                except Exception as e:
                    code_str += f"\n### File: `{rel_path}`\n*Error reading file: {e}*\n"
                    
        return code_str

    def compile(self) -> Path:
        """
        Executes the build process and writes the llm_context_dump.md file
        to the root of the project.
        """
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