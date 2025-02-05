"""Git functionality manager."""

from pathlib import Path
import os
import subprocess
import json
import shutil
from typing import Optional, Dict, List, Tuple
from datetime import datetime

class GitManager:
    """Manages Git-related functionality."""
    
    def __init__(self):
        self.repo_path: Optional[Path] = None
        self.output_path: Optional[Path] = None
        
    def set_repository(self, repo_path: str | Path) -> bool:
        """Set the current Git repository."""
        repo_path = Path(repo_path)
        if not repo_path.exists():
            return False
            
        git_dir = repo_path / '.git'
        if not git_dir.is_dir():
            return False
            
        self.repo_path = repo_path
        return True
        
    def set_output_path(self, output_path: str | Path) -> bool:
        """Set the output path for Git operations."""
        output_path = Path(output_path)
        if not output_path.exists():
            return False
            
        self.output_path = output_path
        return True
        
    def backup_repository(self) -> Tuple[bool, str]:
        """
        Backup Git repository files.
        Returns (success, message).
        """
        if not self.repo_path or not self.output_path:
            return False, "Repository or output path not set"
            
        try:
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.output_path / f"git_backup_{timestamp}.json"
            
            # Get repository info
            repo_info = self.get_repository_info()
            
            # Save backup
            with open(backup_file, 'w') as f:
                json.dump(repo_info, f, indent=2)
                
            return True, f"Backup completed: {backup_file}"
        except Exception as e:
            return False, f"Backup failed: {str(e)}"
            
    def restore_repository(self, backup_file: str | Path) -> Tuple[bool, str]:
        """
        Restore Git repository from backup.
        Returns (success, message).
        """
        if not self.repo_path:
            return False, "Repository path not set"
            
        try:
            # Load backup data
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
                
            # Restore git config
            config_file = self.repo_path / '.git' / 'config'
            with open(config_file, 'w') as f:
                f.write(backup_data['config'])
                
            return True, "Repository restored successfully"
        except Exception as e:
            return False, f"Restore failed: {str(e)}"
            
    def get_repository_info(self) -> Dict:
        """Get information about the current repository."""
        if not self.repo_path:
            return {}
            
        try:
            info = {}
            
            # Get git config
            config_file = self.repo_path / '.git' / 'config'
            if config_file.exists():
                with open(config_file, 'r') as f:
                    info['config'] = f.read()
                    
            # Get current branch
            try:
                branch = subprocess.check_output(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    cwd=self.repo_path,
                    text=True
                ).strip()
                info['current_branch'] = branch
            except subprocess.CalledProcessError:
                info['current_branch'] = None
                
            # Get remotes
            try:
                remotes = subprocess.check_output(
                    ['git', 'remote', '-v'],
                    cwd=self.repo_path,
                    text=True
                ).strip()
                info['remotes'] = remotes
            except subprocess.CalledProcessError:
                info['remotes'] = None
                
            return info
        except Exception:
            return {}
            
    def copy_config(self, source_dir: str, target_dir: str) -> bool:
        """Copy Git configuration from source to target repository."""
        source_config = Path(source_dir) / '.git' / 'config'
        target_config = Path(target_dir) / '.git' / 'config'
        
        if not source_config.exists() or not Path(target_dir).exists():
            return False
            
        try:
            shutil.copy2(source_config, target_config)
            return True
        except Exception:
            return False
            
    def archive_state(self) -> bool:
        """Archive current Git state."""
        if not self.repo_path:
            return False
            
        try:
            # Create archive of current state
            archive_name = f"git_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            subprocess.run(
                ['git', 'archive', '-o', f"{archive_name}.zip", 'HEAD'],
                cwd=self.repo_path,
                check=True
            )
            return True
        except Exception:
            return False
            
    def restore_state(self) -> bool:
        """Restore Git state from archive."""
        if not self.repo_path:
            return False
            
        try:
            # Implementation would go here
            # This is a placeholder as the actual implementation would depend on specific requirements
            return True
        except Exception:
            return False 