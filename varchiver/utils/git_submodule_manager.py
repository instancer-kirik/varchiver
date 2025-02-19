"""Git submodule management functionality."""

from pathlib import Path
import subprocess
import json
from typing import Dict, List, Tuple, Optional
from PyQt6.QtCore import QObject, pyqtSignal

class GitSubmoduleManager(QObject):
    """Manages Git submodule operations."""
    
    # Signals
    submodule_added = pyqtSignal(str)  # path
    submodule_removed = pyqtSignal(str)  # path
    submodule_updated = pyqtSignal(str)  # path
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, repo_path: Path | str):
        super().__init__()
        self.repo_path = Path(repo_path)
        
    def get_submodules(self) -> List[Dict[str, str]]:
        """Get list of all submodules with their details."""
        try:
            # Get submodule status
            result = subprocess.run(
                ['git', 'submodule', 'status', '--recursive'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            submodules = []
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                    
                # Parse status line
                # Format: [+-U][commit-sha] path (branch)
                status = line[0]
                parts = line[1:].strip().split()
                commit = parts[0]
                path = parts[1]
                branch = parts[2][1:-1] if len(parts) > 2 else "master"
                
                # Get URL
                url_result = subprocess.run(
                    ['git', 'config', '--get', f'submodule.{path}.url'],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                submodules.append({
                    'path': path,
                    'url': url_result.stdout.strip(),
                    'commit': commit,
                    'branch': branch,
                    'status': self._parse_status(status)
                })
                
            return submodules
        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(f"Failed to get submodules: {e.stderr}")
            return []
            
    def add_submodule(self, url: str, path: str, branch: Optional[str] = None) -> bool:
        """Add a new submodule."""
        try:
            cmd = ['git', 'submodule', 'add']
            if branch:
                cmd.extend(['-b', branch])
            cmd.extend(['--', url, path])
            
            subprocess.run(cmd, cwd=self.repo_path, check=True)
            
            # Initialize and update the submodule
            subprocess.run(
                ['git', 'submodule', 'update', '--init', '--recursive', path],
                cwd=self.repo_path,
                check=True
            )
            
            self.submodule_added.emit(path)
            return True
        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(f"Failed to add submodule: {e.stderr}")
            return False
            
    def remove_submodule(self, path: str) -> bool:
        """Remove a submodule."""
        try:
            # 1. Deinit the submodule
            subprocess.run(
                ['git', 'submodule', 'deinit', '-f', path],
                cwd=self.repo_path,
                check=True
            )
            
            # 2. Remove from .git/modules
            modules_path = self.repo_path / '.git' / 'modules' / path
            if modules_path.exists():
                import shutil
                shutil.rmtree(modules_path)
            
            # 3. Remove from index
            subprocess.run(
                ['git', 'rm', '-f', path],
                cwd=self.repo_path,
                check=True
            )
            
            self.submodule_removed.emit(path)
            return True
        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(f"Failed to remove submodule: {e.stderr}")
            return False
            
    def update_submodules(self, recursive: bool = True, init: bool = True) -> bool:
        """Update all submodules."""
        try:
            cmd = ['git', 'submodule', 'update']
            if init:
                cmd.append('--init')
            if recursive:
                cmd.append('--recursive')
                
            subprocess.run(cmd, cwd=self.repo_path, check=True)
            return True
        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(f"Failed to update submodules: {e.stderr}")
            return False
            
    def sync_submodules(self) -> bool:
        """Sync submodule URLs with .gitmodules file."""
        try:
            subprocess.run(
                ['git', 'submodule', 'sync', '--recursive'],
                cwd=self.repo_path,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(f"Failed to sync submodules: {e.stderr}")
            return False
            
    def set_submodule_url(self, path: str, url: str) -> bool:
        """Set a new URL for a submodule."""
        try:
            # Update URL in .gitmodules
            subprocess.run(
                ['git', 'config', '--file=.gitmodules', f'submodule.{path}.url', url],
                cwd=self.repo_path,
                check=True
            )
            
            # Sync and update
            self.sync_submodules()
            self.update_submodules()
            
            return True
        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(f"Failed to set submodule URL: {e.stderr}")
            return False
            
    def set_submodule_branch(self, path: str, branch: str) -> bool:
        """Set the branch for a submodule."""
        try:
            # Set branch in .gitmodules
            subprocess.run(
                ['git', 'config', '--file=.gitmodules', f'submodule.{path}.branch', branch],
                cwd=self.repo_path,
                check=True
            )
            
            # Update the submodule to use the new branch
            subprocess.run(
                ['git', 'submodule', 'update', '--init', '--recursive', '--remote', path],
                cwd=self.repo_path,
                check=True
            )
            
            return True
        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(f"Failed to set submodule branch: {e.stderr}")
            return False
            
    def foreach_submodule(self, command: str) -> bool:
        """Run a command in each submodule."""
        try:
            subprocess.run(
                ['git', 'submodule', 'foreach', command],
                cwd=self.repo_path,
                check=True,
                shell=True
            )
            return True
        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(f"Failed to run command in submodules: {e.stderr}")
            return False
            
    @staticmethod
    def _parse_status(status: str) -> str:
        """Parse submodule status indicator."""
        if status == '+':
            return "modified"
        elif status == '-':
            return "uninitialized"
        elif status == 'U':
            return "merge conflicts"
        else:
            return "normal" 