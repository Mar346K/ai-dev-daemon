import time
from threading import Timer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from app.core.git_manager import GitManager

class DebouncedCodeWatcher(FileSystemEventHandler):
    """
    Monitors file changes and triggers a Git commit pipeline after a set period of inactivity.
    """
    def __init__(self, debounce_seconds: int = 900):
        self.debounce_seconds = debounce_seconds
        self.timer: Timer | None = None
        self.git_manager = GitManager()

    def on_modified(self, event: FileModifiedEvent) -> None:
        """
        Triggered by watchdog when a file is modified. Resets the countdown timer.
        """
        if event.is_directory:
            return

        # Professional Standard: Debounce logic
        if self.timer is not None:
            self.timer.cancel()
            
        self.timer = Timer(self.debounce_seconds, self._execute_pipeline)
        self.timer.start()
        print(f"File saved: {event.src_path}. Timer reset to {self.debounce_seconds}s.")

    def _execute_pipeline(self) -> None:
        """
        Fires when the timer reaches zero. Runs security checks and stages files.
        """
        print("Idle time reached. Processing Git Diff and staging changes...")
        self.git_manager.process_and_stage_changes()