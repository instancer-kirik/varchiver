from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                            QLabel, QTreeWidget, QTreeWidgetItem, QHeaderView,
                            QDialogButtonBox, QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
import os

class CollisionDialog(QDialog):
    """Dialog for handling file collisions during extraction"""
    
    collision_resolved = pyqtSignal(dict)  # Emits dict of {path: action}

    def __init__(self, collisions, parent=None):
        """Initialize dialog
        
        Args:
            collisions: List of (source_path, target_path, info) tuples
            info: Dict containing file info (size, mtime, etc)
        """
        super().__init__(parent)
        self.collisions = collisions
        self.resolutions = {}  # {path: action}
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI"""
        self.setWindowTitle("Resolve File Collisions")
        layout = QVBoxLayout(self)

        # Add description
        layout.addWidget(QLabel("The following files already exist in the target location:"))

        # Create tree widget for collisions
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['File', 'Location', 'Size', 'Modified', 'Action'])
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.tree)

        # Add collisions to tree
        self._populate_tree()

        # Add action buttons
        action_group = QGroupBox("Apply to All")
        action_layout = QHBoxLayout()
        
        self.skip_all = QPushButton("Skip All")
        self.skip_all.clicked.connect(lambda: self._apply_to_all('skip'))
        action_layout.addWidget(self.skip_all)

        self.overwrite_all = QPushButton("Overwrite All")
        self.overwrite_all.clicked.connect(lambda: self._apply_to_all('overwrite'))
        action_layout.addWidget(self.overwrite_all)

        self.rename_all = QPushButton("Rename All")
        self.rename_all.clicked.connect(lambda: self._apply_to_all('rename'))
        action_layout.addWidget(self.rename_all)

        action_group.setLayout(action_layout)
        layout.addWidget(action_group)

        # Add checkbox for remembering choice
        self.remember_choice = QCheckBox("Remember my choice for this session")
        layout.addWidget(self.remember_choice)

        # Add dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.resize(800, 400)

    def _populate_tree(self):
        """Add collisions to tree widget"""
        for source, target, info in self.collisions:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, os.path.basename(target))
            item.setText(1, os.path.dirname(target))
            
            # Set size
            size = info.get('size', 0)
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/(1024*1024):.1f} MB"
            item.setText(2, size_str)
            
            # Set modified time
            item.setText(3, info.get('modified', ''))
            
            # Add combo box for action
            item.setText(4, 'Skip')  # Default action
            
            # Store paths in item data
            item.setData(0, Qt.ItemDataRole.UserRole, {
                'source': source,
                'target': target,
                'info': info
            })

    def _apply_to_all(self, action):
        """Apply an action to all items"""
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            item.setText(4, action.title())
            data = item.data(0, Qt.ItemDataRole.UserRole)
            self.resolutions[data['target']] = action

    def get_resolutions(self):
        """Get resolution for each collision"""
        if self.result() == QDialog.DialogCode.Accepted:
            # Gather resolutions from tree
            root = self.tree.invisibleRootItem()
            for i in range(root.childCount()):
                item = root.child(i)
                data = item.data(0, Qt.ItemDataRole.UserRole)
                action = item.text(4).lower()
                self.resolutions[data['target']] = action
            
            return self.resolutions, self.remember_choice.isChecked()
        return {}, False
