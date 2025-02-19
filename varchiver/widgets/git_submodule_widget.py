"""Git submodule management widget."""

from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTreeWidget, QTreeWidgetItem, QMessageBox,
                            QDialog, QLineEdit, QFormLayout, QDialogButtonBox,
                            QMenu, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from ..utils.git_submodule_manager import GitSubmoduleManager

class AddSubmoduleDialog(QDialog):
    """Dialog for adding a new submodule."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Submodule")
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QFormLayout(self)
        
        # URL input
        self.url_input = QLineEdit()
        layout.addRow("Repository URL:", self.url_input)
        
        # Path input
        self.path_input = QLineEdit()
        layout.addRow("Local Path:", self.path_input)
        
        # Branch input (optional)
        self.branch_input = QLineEdit()
        self.branch_input.setPlaceholderText("Optional")
        layout.addRow("Branch:", self.branch_input)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
    def get_values(self) -> tuple[str, str, str]:
        """Get the entered values."""
        return (
            self.url_input.text().strip(),
            self.path_input.text().strip(),
            self.branch_input.text().strip() or None
        )

class GitSubmoduleWidget(QWidget):
    """Widget for managing Git submodules."""
    
    # Signals
    submodule_changed = pyqtSignal()  # Emitted when submodules are modified
    
    def __init__(self, repo_path: Path | str, parent=None):
        super().__init__(parent)
        self.repo_path = Path(repo_path)
        self.submodule_manager = GitSubmoduleManager(repo_path)
        
        # Connect signals
        self.submodule_manager.error_occurred.connect(self.show_error)
        self.submodule_manager.submodule_added.connect(lambda _: self.refresh_submodules())
        self.submodule_manager.submodule_removed.connect(lambda _: self.refresh_submodules())
        self.submodule_manager.submodule_updated.connect(lambda _: self.refresh_submodules())
        
        self.init_ui()
        self.refresh_submodules()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Description
        desc = QLabel(
            "Manage Git submodules. Add, remove, update, and configure nested repositories."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Submodule")
        add_btn.clicked.connect(self.add_submodule)
        button_layout.addWidget(add_btn)
        
        update_btn = QPushButton("Update All")
        update_btn.clicked.connect(self.update_submodules)
        button_layout.addWidget(update_btn)
        
        sync_btn = QPushButton("Sync URLs")
        sync_btn.clicked.connect(self.sync_submodules)
        button_layout.addWidget(sync_btn)
        
        layout.addLayout(button_layout)
        
        # Submodule tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            "Path", "URL", "Branch", "Commit", "Status"
        ])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree)
        
    def refresh_submodules(self):
        """Refresh the submodule list."""
        self.tree.clear()
        
        submodules = self.submodule_manager.get_submodules()
        for submodule in submodules:
            item = QTreeWidgetItem([
                submodule['path'],
                submodule['url'],
                submodule['branch'],
                submodule['commit'][:8],  # Short commit hash
                submodule['status']
            ])
            self.tree.addTopLevelItem(item)
            
        # Resize columns to content
        for i in range(self.tree.columnCount()):
            self.tree.resizeColumnToContents(i)
            
        self.submodule_changed.emit()
        
    def add_submodule(self):
        """Show dialog to add a new submodule."""
        dialog = AddSubmoduleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            url, path, branch = dialog.get_values()
            if url and path:
                if self.submodule_manager.add_submodule(url, path, branch):
                    self.refresh_submodules()
                    
    def update_submodules(self):
        """Update all submodules."""
        if self.submodule_manager.update_submodules():
            self.refresh_submodules()
            
    def sync_submodules(self):
        """Sync submodule URLs."""
        if self.submodule_manager.sync_submodules():
            self.refresh_submodules()
            
    def show_context_menu(self, position):
        """Show context menu for submodule item."""
        item = self.tree.itemAt(position)
        if not item:
            return
            
        path = item.text(0)  # Submodule path is in first column
        
        menu = QMenu()
        
        # URL actions
        change_url = menu.addAction("Change URL")
        change_url.triggered.connect(lambda: self.change_submodule_url(path))
        
        # Branch actions
        change_branch = menu.addAction("Change Branch")
        change_branch.triggered.connect(lambda: self.change_submodule_branch(path))
        
        menu.addSeparator()
        
        # Update action
        update = menu.addAction("Update")
        update.triggered.connect(lambda: self.update_single_submodule(path))
        
        menu.addSeparator()
        
        # Remove action
        remove = menu.addAction("Remove")
        remove.triggered.connect(lambda: self.remove_submodule(path))
        
        menu.exec(self.tree.viewport().mapToGlobal(position))
        
    def change_submodule_url(self, path: str):
        """Change URL for a submodule."""
        current_url = ""
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.text(0) == path:
                current_url = item.text(1)
                break
                
        new_url, ok = QInputDialog.getText(
            self,
            "Change Submodule URL",
            f"Enter new URL for {path}:",
            text=current_url
        )
        
        if ok and new_url and new_url != current_url:
            if self.submodule_manager.set_submodule_url(path, new_url):
                self.refresh_submodules()
                
    def change_submodule_branch(self, path: str):
        """Change branch for a submodule."""
        current_branch = ""
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.text(0) == path:
                current_branch = item.text(2)
                break
                
        new_branch, ok = QInputDialog.getText(
            self,
            "Change Submodule Branch",
            f"Enter new branch for {path}:",
            text=current_branch
        )
        
        if ok and new_branch and new_branch != current_branch:
            if self.submodule_manager.set_submodule_branch(path, new_branch):
                self.refresh_submodules()
                
    def update_single_submodule(self, path: str):
        """Update a single submodule."""
        if self.submodule_manager.update_submodules(recursive=True, init=True):
            self.refresh_submodules()
            
    def remove_submodule(self, path: str):
        """Remove a submodule."""
        reply = QMessageBox.question(
            self,
            "Remove Submodule",
            f"Are you sure you want to remove the submodule at {path}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.submodule_manager.remove_submodule(path):
                self.refresh_submodules()
                
    def show_error(self, message: str):
        """Show error message."""
        QMessageBox.critical(self, "Error", message) 