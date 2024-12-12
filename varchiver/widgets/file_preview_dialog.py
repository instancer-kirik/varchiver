from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTreeWidget, QTreeWidgetItem, QLabel, QLineEdit,
                             QCheckBox, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
import os
import zipfile
import tarfile
import rarfile
from pathlib import Path
from typing import List, Optional

class FilePreviewDialog(QDialog):
    """Dialog for previewing and selecting files"""
    
    files_selected = pyqtSignal(list)  # Emitted when files are selected
    
    def __init__(self, files: List[str], mode: str = "create", parent=None):
        super().__init__(parent)
        self.files = files
        self.mode = mode  # can be "create", "extract", "move", or "git"
        self.selected_files = set()
        self.setup_ui()
        self.populate_tree()
    
    def setup_ui(self):
        """Set up the dialog UI"""
        if self.mode == "move":
            self.setWindowTitle("Select Files to Move")
        elif self.mode == "extract":
            self.setWindowTitle("Select Files to Extract")
        elif self.mode == "git":
            self.setWindowTitle("Git Configuration Preview")
        else:
            self.setWindowTitle("Select Files to Archive")
            
        # Set minimum size and make resizable
        self.setMinimumSize(800, 600)
        self.setSizeGripEnabled(True)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add filter controls
        filter_layout = QHBoxLayout()
        
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter pattern (e.g. *.py)")
        self.filter_input.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_input)
        
        self.filter_type = QComboBox()
        if self.mode == "git":
            self.filter_type.addItems(["All", "Remotes", "Branches", "Submodules", "Hooks"])
        else:
            self.filter_type.addItems(["Custom", "Source Code", "Documentation", "Git Files"])
        self.filter_type.currentTextChanged.connect(self.preset_filter_changed)
        filter_layout.addWidget(self.filter_type)
        
        layout.addLayout(filter_layout)
        
        # Create tree widget
        self.tree = QTreeWidget()
        if self.mode == "git":
            self.tree.setHeaderLabels(['Name', 'Type', 'Details'])
        else:
            self.tree.setHeaderLabels(["Name", "Size", "Type"])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.tree)
        
        # Create buttons
        button_layout = QHBoxLayout()
        
        # Select/deselect all checkbox
        self.select_all = QCheckBox("Select All")
        self.select_all.stateChanged.connect(lambda state: self.toggle_all(Qt.CheckState(state)))
        button_layout.addWidget(self.select_all)
        
        button_layout.addStretch()
        
        # Create buttons
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def populate_tree(self):
        """Populate tree with files or git info"""
        self.tree.clear()
        
        if self.mode == "git":
            # Add git repository information
            for repo_path in self.files:
                try:
                    handler = GitConfigHandler(repo_path)
                    config = handler.get_git_config()
                    
                    # Add remotes
                    remotes_item = QTreeWidgetItem(self.tree, ["Remotes", "Category", ""])
                    remotes_item.setFlags(remotes_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    remotes_item.setCheckState(0, Qt.CheckState.Checked)
                    
                    for name, url in config.get('remotes', {}).items():
                        remote_item = QTreeWidgetItem(remotes_item, [name, "Remote", url])
                        remote_item.setFlags(remote_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        remote_item.setCheckState(0, Qt.CheckState.Checked)
                    
                    # Add branches
                    branches_item = QTreeWidgetItem(self.tree, ["Branches", "Category", ""])
                    branches_item.setFlags(branches_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    branches_item.setCheckState(0, Qt.CheckState.Checked)
                    
                    for name, commit in config.get('branches', {}).items():
                        branch_item = QTreeWidgetItem(branches_item, [name, "Branch", commit])
                        branch_item.setFlags(branch_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        branch_item.setCheckState(0, Qt.CheckState.Checked)
                    
                    # Add submodules
                    if config.get('submodules'):
                        submodules_item = QTreeWidgetItem(self.tree, ["Submodules", "Category", ""])
                        submodules_item.setFlags(submodules_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        submodules_item.setCheckState(0, Qt.CheckState.Checked)
                        
                        for name, details in config.get('submodules', {}).items():
                            submodule_item = QTreeWidgetItem(submodules_item, [name, "Submodule", details.get('url', '')])
                            submodule_item.setFlags(submodule_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                            submodule_item.setCheckState(0, Qt.CheckState.Checked)
                    
                    # Add hooks
                    if config.get('hooks'):
                        hooks_item = QTreeWidgetItem(self.tree, ["Hooks", "Category", ""])
                        hooks_item.setFlags(hooks_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        hooks_item.setCheckState(0, Qt.CheckState.Checked)
                        
                        for name, content in config.get('hooks', {}).items():
                            hook_item = QTreeWidgetItem(hooks_item, [name, "Hook", "Executable" if content.get('executable') else "Script"])
                            hook_item.setFlags(hook_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                            hook_item.setCheckState(0, Qt.CheckState.Checked)
                    
                    # Add .gitignore patterns
                    if config.get('gitignore'):
                        gitignore_item = QTreeWidgetItem(self.tree, [".gitignore", "Category", ""])
                        gitignore_item.setFlags(gitignore_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        gitignore_item.setCheckState(0, Qt.CheckState.Checked)
                        
                        for pattern in config.get('gitignore', []):
                            pattern_item = QTreeWidgetItem(gitignore_item, [pattern, "Pattern", ""])
                            pattern_item.setFlags(pattern_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                            pattern_item.setCheckState(0, Qt.CheckState.Checked)
                    
                except Exception as e:
                    QMessageBox.warning(self, "Warning", f"Error loading Git repository: {str(e)}")
        else:
            # Regular file preview
            for path in self.files:
                if os.path.exists(path):
                    self._add_path_to_tree(path, self.tree)
        
        self.tree.expandAll()
    
    def _add_path_to_tree(self, path: str, parent: QTreeWidget):
        """Add a path to the tree"""
        if os.path.isfile(path):
            self._add_file_item(path, parent)
        elif os.path.isdir(path):
            self._add_directory_items(path, parent)
    
    def _add_file_item(self, file_path: str, parent: QTreeWidget):
        """Add a file item to the tree"""
        name = os.path.basename(file_path)
        size = os.path.getsize(file_path)
        item = QTreeWidgetItem(parent, [name, self._format_size(size), "File"])
        item.setData(0, Qt.ItemDataRole.UserRole, file_path)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Unchecked)
    
    def _add_directory_items(self, dir_path: str, parent: QTreeWidget):
        """Add directory items to the tree"""
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, dir_path)
                self._add_file_item(file_path, parent)
    
    def _format_size(self, size: int) -> str:
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item check state changes"""
        if column == 0:
            path = item.data(0, Qt.ItemDataRole.UserRole)
            if item.checkState(0) == Qt.CheckState.Checked:
                self.selected_files.add(path)
            else:
                self.selected_files.discard(path)
    
    def toggle_all(self, state: Qt.CheckState):
        """Toggle all items"""
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setCheckState(0, state)
    
    def apply_filter(self):
        """Apply the current filter"""
        filter_text = self.filter_input.text().lower()
        
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            name = item.text(0).lower()
            
            # Show item if it matches the filter
            matches = True
            if filter_text:
                if '*' in filter_text:
                    pattern = filter_text.replace('*', '')
                    matches = pattern in name
                else:
                    matches = filter_text in name
            
            item.setHidden(not matches)
    
    def preset_filter_changed(self, preset: str):
        """Handle preset filter changes"""
        filter_map = {
            "Source Code": "*.py,*.cpp,*.h,*.java,*.js,*.ts",
            "Documentation": "*.md,*.txt,*.rst,*.pdf",
            "Git Files": ".git*,*.git"
        }
        
        if preset in filter_map:
            self.filter_input.setText(filter_map[preset])
        else:
            self.filter_input.clear()
    
    def accept(self):
        """Handle dialog acceptance"""
        if not self.selected_files:
            action = "move" if self.mode == "move" else "extract" if self.mode == "extract" else "archive"
            QMessageBox.warning(
                self,
                "No Files Selected",
                f"Please select at least one file to {action}."
            )
            return
        
        self.files_selected.emit(list(self.selected_files))
        super().accept()
