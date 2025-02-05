"""Git file sequestration tool for temporarily removing Git files."""

from pathlib import Path
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTextEdit, QMessageBox, QListWidget)
from PyQt6.QtCore import Qt

class GitSequester(QWidget):
    """Widget for managing Git file sequestration."""
    
    def __init__(self, repo_path: str, parent=None):
        super().__init__(parent)
        self.repo_path = Path(repo_path)
        self.storage_path = None  # Will be set via set_storage_path
        self.init_ui()
        self.refresh_untracked_files()
        
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
        
        # Description
        desc = QLabel(
            "Manage untracked Git files. Select files to temporarily remove or restore."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Untracked files list
        self.untracked_list = QListWidget()
        self.untracked_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        layout.addWidget(self.untracked_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_untracked_files)
        button_layout.addWidget(refresh_btn)
        
        sequester_btn = QPushButton("Sequester Selected")
        sequester_btn.clicked.connect(self.sequester_selected)
        button_layout.addWidget(sequester_btn)
        
        restore_btn = QPushButton("Restore Selected")
        restore_btn.clicked.connect(self.restore_selected)
        button_layout.addWidget(restore_btn)
        
        layout.addLayout(button_layout)
        
        # Status
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
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
            manifest_file = sequester_dir / "manifest.json"
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
            manifest_file = sequester_dir / "manifest.json"
            
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