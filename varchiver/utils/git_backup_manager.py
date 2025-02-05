from pathlib import Path
import os
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal
from .git_utils import GitConfigHandler

class GitBackupManager(QObject):
    """Manages Git backup operations."""
    
    # Signals
    backup_started = pyqtSignal()
    backup_completed = pyqtSignal(str)  # Emits backup file path
    backup_failed = pyqtSignal(str)  # Emits error message
    restore_started = pyqtSignal()
    restore_completed = pyqtSignal()
    restore_failed = pyqtSignal(str)  # Emits error message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def backup_repository(self, repo_path: Path, output_path: Path) -> bool:
        """
        Backup Git repository files.
        
        Args:
            repo_path: Path to Git repository
            output_path: Path to backup directory
            
        Returns:
            True if backup successful, False otherwise
        """
        if not repo_path or not output_path:
            self.backup_failed.emit("Repository or output path not specified")
            return False
            
        try:
            self.backup_started.emit()
            
            # Generate backup filename
            repo_name = repo_path.name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = output_path / f"git_backup_{repo_name}_{timestamp}.json"
            
            # Perform backup
            handler = GitConfigHandler(str(repo_path))
            if handler.remove_git_files(backup_path=str(backup_file)):
                self.backup_completed.emit(str(backup_file))
                return True
            else:
                self.backup_failed.emit("Failed to backup and remove git files")
                return False
                
        except Exception as e:
            self.backup_failed.emit(str(e))
            return False
            
    def restore_repository(self, backup_file: Path, target_path: Path) -> bool:
        """
        Restore Git repository from backup.
        
        Args:
            backup_file: Path to backup file
            target_path: Path to restore repository to
            
        Returns:
            True if restore successful, False otherwise
        """
        if not backup_file or not target_path:
            self.restore_failed.emit("Backup file or target path not specified")
            return False
            
        try:
            self.restore_started.emit()
            
            handler = GitConfigHandler(str(target_path))
            if handler.restore_git_files(str(backup_file)):
                self.restore_completed.emit()
                return True
            else:
                self.restore_failed.emit("Failed to restore git files")
                return False
                
        except Exception as e:
            self.restore_failed.emit(str(e))
            return False 