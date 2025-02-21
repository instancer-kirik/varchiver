"""Git file sequestration tool for temporarily removing Git files."""

from pathlib import Path
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTextEdit, QMessageBox, QListWidget,
                            QTabWidget, QGroupBox)
from PyQt6.QtCore import Qt
from ..utils.git_utils import GitConfigHandler

class GitSequester(QWidget):
    """Widget for managing Git file sequestration and untracked files."""
    
    def __init__(self, repo_path: str, parent=None):
        super().__init__(parent)
        self.repo_path = Path(repo_path)
        self.storage_path = None  # Will be set via set_storage_path
        self.git_handler = GitConfigHandler(str(self.repo_path))
        self.init_ui()
        
    def set_storage_path(self, path: str):
        """Set the storage path for sequestered files."""
        self.storage_path = Path(path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    def get_sequester_dir(self) -> Path:
        """Get the directory for sequestered files."""
        if self.storage_path:
            return self.storage_path
        # Fallback to default location in .git
        return self.repo_path / ".git" / "sequestered"
        
    def init_ui(self):
        """Initialize the UI elements."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Git Files Tab
        git_tab = QWidget()
        git_layout = QVBoxLayout()
        
        # Description
        git_desc = QLabel(
            "Extract Git-related files when working with environments that don't play well with Git. "
            "This will safely remove .git directories and related files, storing them for later restoration."
        )
        git_desc.setWordWrap(True)
        git_layout.addWidget(git_desc)
        
        # Status group
        status_group = QGroupBox("Git Status")
        status_layout = QVBoxLayout()
        self.git_status = QLabel()
        self.update_git_status()
        status_layout.addWidget(self.git_status)
        status_group.setLayout(status_layout)
        git_layout.addWidget(status_group)
        
        # Git action buttons
        git_buttons = QHBoxLayout()
        
        extract_btn = QPushButton("Extract Git Files")
        extract_btn.clicked.connect(self.extract_git_files)
        git_buttons.addWidget(extract_btn)
        
        restore_btn = QPushButton("Restore Git Files")
        restore_btn.clicked.connect(self.restore_git_files)
        git_buttons.addWidget(restore_btn)
        
        git_layout.addLayout(git_buttons)
        git_tab.setLayout(git_layout)
        
        # Untracked Files Tab
        untracked_tab = QWidget()
        untracked_layout = QVBoxLayout()
        
        # Description
        untracked_desc = QLabel(
            "Manage untracked files. Select files to temporarily remove or restore."
        )
        untracked_desc.setWordWrap(True)
        untracked_layout.addWidget(untracked_desc)
        
        # Untracked files list
        self.untracked_list = QListWidget()
        self.untracked_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        untracked_layout.addWidget(self.untracked_list)
        
        # Untracked file buttons
        untracked_buttons = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_untracked_files)
        untracked_buttons.addWidget(refresh_btn)
        
        sequester_btn = QPushButton("Sequester Selected")
        sequester_btn.clicked.connect(self.sequester_selected)
        untracked_buttons.addWidget(sequester_btn)
        
        restore_untracked_btn = QPushButton("Restore Selected")
        restore_untracked_btn.clicked.connect(self.restore_selected)
        untracked_buttons.addWidget(restore_untracked_btn)
        
        untracked_layout.addLayout(untracked_buttons)
        
        # Status
        self.status_label = QLabel()
        untracked_layout.addWidget(self.status_label)
        
        untracked_tab.setLayout(untracked_layout)
        
        # Add tabs
        tab_widget.addTab(git_tab, "Git Files")
        tab_widget.addTab(untracked_tab, "Untracked Files")
        
        layout.addWidget(tab_widget)
        
        # Initial refresh
        self.refresh_untracked_files()
        
    def update_git_status(self):
        """Update the Git status display."""
        if self.git_handler.is_git_repo():
            git_dir = self.repo_path / '.git'
            if git_dir.is_file():  # Submodule
                with open(git_dir, 'r') as f:
                    content = f.read().strip()
                    if content.startswith('gitdir:'):
                        git_dir = Path(content.split(':', 1)[1].strip())
            
            # Check if Git files are extracted
            backup_path = self.get_sequester_dir() / "git_backup.json"
            if backup_path.exists():
                self.git_status.setText("Git files are currently extracted")
                self.git_status.setStyleSheet("color: orange")
            else:
                self.git_status.setText("Git files are present")
                self.git_status.setStyleSheet("color: green")
        else:
            self.git_status.setText("No Git repository found")
            self.git_status.setStyleSheet("color: red")
            
    def extract_git_files(self):
        """Extract Git-related files from the repository."""
        try:
            if not self.git_handler.is_git_repo():
                QMessageBox.warning(self, "Warning", "No Git repository found")
                return
                
            # Confirm action
            reply = QMessageBox.question(
                self,
                "Extract Git Files",
                "This will extract all Git-related files from the repository. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                backup_path = self.get_sequester_dir() / "git_backup.json"
                self.git_handler.remove_git_files(str(backup_path))
                self.update_git_status()
                QMessageBox.information(self, "Success", "Git files extracted successfully")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to extract Git files: {str(e)}")
            
    def restore_git_files(self):
        """Restore previously extracted Git files."""
        try:
            backup_path = self.get_sequester_dir() / "git_backup.json"
            if not backup_path.exists():
                QMessageBox.warning(self, "Warning", "No extracted Git files found")
                return
                
            # Confirm action
            reply = QMessageBox.question(
                self,
                "Restore Git Files",
                "This will restore all Git-related files to the repository. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.git_handler.restore_git_files(str(backup_path))
                backup_path.unlink()  # Remove backup after successful restore
                self.update_git_status()
                QMessageBox.information(self, "Success", "Git files restored successfully")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore Git files: {str(e)}")
            
    def refresh_untracked_files(self):
        """Refresh the list of untracked files."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            self.untracked_list.clear()
            if result.stdout:
                files = result.stdout.strip().split('\n')
                self.untracked_list.addItems(files)
                self.status_label.setText(f"Found {len(files)} untracked files")
            else:
                self.status_label.setText("No untracked files found")
                
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to get untracked files: {e.stderr}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get untracked files: {str(e)}")
            
    def sequester_selected(self):
        """Temporarily remove selected files."""
        selected = self.untracked_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Warning", "No files selected")
            return
            
        try:
            import json
            sequester_dir = self.get_sequester_dir()
            sequester_dir.mkdir(exist_ok=True)
            
            # Create manifest
            manifest_file = sequester_dir / "untracked_manifest.json"  # Renamed to avoid conflict
            if manifest_file.exists():
                manifest = json.loads(manifest_file.read_text())
            else:
                manifest = {}
                
            # Move files
            for item in selected:
                file_path = self.repo_path / item.text()
                if file_path.exists():
                    # Add to manifest
                    manifest[item.text()] = str(file_path)
                    # Move file
                    target = sequester_dir / item.text()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    file_path.rename(target)
                    
            # Save manifest
            manifest_file.write_text(json.dumps(manifest, indent=2))
            
            self.refresh_untracked_files()
            QMessageBox.information(self, "Success", "Files sequestered successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to sequester files: {str(e)}")
            
    def restore_selected(self):
        """Restore selected sequestered files."""
        try:
            import json
            sequester_dir = self.get_sequester_dir()
            manifest_file = sequester_dir / "untracked_manifest.json"  # Renamed to avoid conflict
            
            if not manifest_file.exists():
                QMessageBox.warning(self, "Warning", "No sequestered files found")
                return
                
            manifest = json.loads(manifest_file.read_text())
            if not manifest:
                QMessageBox.warning(self, "Warning", "No sequestered files found")
                return
                
            # Show list of sequestered files
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox
            dialog = QDialog(self)
            dialog.setWindowTitle("Select Files to Restore")
            dialog_layout = QVBoxLayout()
            
            file_list = QListWidget()
            file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
            file_list.addItems(manifest.keys())
            dialog_layout.addWidget(file_list)
            
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | 
                QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            dialog_layout.addWidget(buttons)
            
            dialog.setLayout(dialog_layout)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected = file_list.selectedItems()
                if not selected:
                    return
                    
                # Restore files
                for item in selected:
                    file_name = item.text()
                    source = sequester_dir / file_name
                    if source.exists():
                        target = Path(manifest[file_name])
                        target.parent.mkdir(parents=True, exist_ok=True)
                        source.rename(target)
                        del manifest[file_name]
                        
                # Update manifest
                if manifest:
                    manifest_file.write_text(json.dumps(manifest, indent=2))
                else:
                    manifest_file.unlink()
                    
                self.refresh_untracked_files()
                QMessageBox.information(self, "Success", "Files restored successfully")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore files: {str(e)}") 