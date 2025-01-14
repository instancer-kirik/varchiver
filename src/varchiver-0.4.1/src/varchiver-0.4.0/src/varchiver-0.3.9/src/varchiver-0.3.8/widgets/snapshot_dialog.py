from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                            QLabel, QLineEdit, QTextEdit, QComboBox,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QMessageBox, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from datetime import datetime
import os
from ..utils.snapshot_manager import SnapshotManager, SnapshotInfo

class SnapshotDialog(QDialog):
    """Dialog for managing archive snapshots"""
    
    snapshot_selected = pyqtSignal(SnapshotInfo)
    
    def __init__(self, snapshot_manager: SnapshotManager, parent=None):
        super().__init__(parent)
        self.snapshot_manager = snapshot_manager
        self.selected_snapshot = None
        
        self.setWindowTitle('Snapshot Manager')
        self.setMinimumSize(1000, 600)
        self.setSizeGripEnabled(True)
        
        self._init_ui()
        self._load_snapshots()
    
    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Controls
        controls = QHBoxLayout()
        
        # Sort options
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(['Date', 'Name', 'Size'])
        self.sort_combo.currentTextChanged.connect(self._load_snapshots)
        controls.addWidget(QLabel('Sort by:'))
        controls.addWidget(self.sort_combo)
        
        # Filter by tag
        self.tag_filter = QLineEdit()
        self.tag_filter.setPlaceholderText('Filter by tag...')
        self.tag_filter.textChanged.connect(self._load_snapshots)
        controls.addWidget(QLabel('Tag:'))
        controls.addWidget(self.tag_filter)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        # Snapshots table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['Name', 'Date', 'Size', 'Tags', 'Description'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)
        
        # Buttons
        buttons = QHBoxLayout()
        
        self.select_button = QPushButton('Select')
        self.select_button.clicked.connect(self.accept)
        self.select_button.setEnabled(False)
        buttons.addWidget(self.select_button)
        
        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)
        
        layout.addLayout(buttons)
    
    def _format_size(self, size: int) -> str:
        """Format size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def _load_snapshots(self):
        """Load snapshots into the table"""
        # Get sort option
        sort_by = self.sort_combo.currentText().lower()
        if sort_by == 'date':
            sort_by = 'timestamp'
        
        # Get tag filter
        tag = self.tag_filter.text().strip()
        if not tag:
            tag = None
        
        # Get snapshots
        snapshots = self.snapshot_manager.list_snapshots(
            tag=tag,
            sort_by=sort_by,
            reverse=True
        )
        
        # Update table
        self.table.setRowCount(len(snapshots))
        for i, snap in enumerate(snapshots):
            # Name
            name_item = QTableWidgetItem(snap.name)
            name_item.setData(Qt.ItemDataRole.UserRole, snap)
            self.table.setItem(i, 0, name_item)
            
            # Date
            date = datetime.fromtimestamp(snap.timestamp)
            date_item = QTableWidgetItem(date.strftime('%Y-%m-%d %H:%M:%S'))
            self.table.setItem(i, 1, date_item)
            
            # Size
            size_item = QTableWidgetItem(self._format_size(snap.size))
            self.table.setItem(i, 2, size_item)
            
            # Tags
            tags_item = QTableWidgetItem(', '.join(snap.tags) if snap.tags else '')
            self.table.setItem(i, 3, tags_item)
            
            # Description
            desc_item = QTableWidgetItem(snap.description or '')
            self.table.setItem(i, 4, desc_item)
    
    def _show_context_menu(self, pos):
        """Show context menu for snapshot actions"""
        if not self.table.selectedItems():
            return
        
        menu = QMenu(self)
        
        # Add actions
        select_action = QAction('Select', self)
        select_action.triggered.connect(self.accept)
        menu.addAction(select_action)
        
        delete_action = QAction('Delete', self)
        delete_action.triggered.connect(self._delete_selected)
        menu.addAction(delete_action)
        
        edit_action = QAction('Edit...', self)
        edit_action.triggered.connect(self._edit_selected)
        menu.addAction(edit_action)
        
        # Show menu
        menu.exec(self.table.viewport().mapToGlobal(pos))
    
    def _on_selection_changed(self):
        """Handle selection changes"""
        items = self.table.selectedItems()
        if items:
            row = items[0].row()
            self.selected_snapshot = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.select_button.setEnabled(True)
        else:
            self.selected_snapshot = None
            self.select_button.setEnabled(False)
    
    def _delete_selected(self):
        """Delete selected snapshot"""
        if not self.selected_snapshot:
            return
        
        reply = QMessageBox.question(
            self,
            'Delete Snapshot',
            f'Are you sure you want to delete snapshot "{self.selected_snapshot.name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.snapshot_manager.delete_snapshot(self.selected_snapshot.id):
                self._load_snapshots()
            else:
                QMessageBox.warning(self, 'Error', 'Failed to delete snapshot')
    
    def _edit_selected(self):
        """Edit selected snapshot"""
        if not self.selected_snapshot:
            return
        
        dialog = SnapshotEditDialog(self.selected_snapshot, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update snapshot
            if self.snapshot_manager.update_snapshot(
                self.selected_snapshot.id,
                name=dialog.name_edit.text(),
                description=dialog.description_edit.toPlainText(),
                tags=[t.strip() for t in dialog.tags_edit.text().split(',') if t.strip()]
            ):
                self._load_snapshots()
            else:
                QMessageBox.warning(self, 'Error', 'Failed to update snapshot')
    
    def accept(self):
        """Accept dialog and emit selected snapshot"""
        if self.selected_snapshot:
            self.snapshot_selected.emit(self.selected_snapshot)
        super().accept()

class SnapshotEditDialog(QDialog):
    """Dialog for editing snapshot metadata"""
    
    def __init__(self, snapshot: SnapshotInfo, parent=None):
        super().__init__(parent)
        self.snapshot = snapshot
        
        self.setWindowTitle('Edit Snapshot')
        self.setMinimumSize(600, 400)
        self.setSizeGripEnabled(True)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Name
        layout.addWidget(QLabel('Name:'))
        self.name_edit = QLineEdit(snapshot.name)
        layout.addWidget(self.name_edit)
        
        # Tags
        layout.addWidget(QLabel('Tags (comma-separated):'))
        self.tags_edit = QLineEdit()
        if snapshot.tags:
            self.tags_edit.setText(', '.join(snapshot.tags))
        layout.addWidget(self.tags_edit)
        
        # Description
        layout.addWidget(QLabel('Description:'))
        self.description_edit = QTextEdit()
        self.description_edit.setMinimumHeight(150)  # Ensure enough space for description
        if snapshot.description:
            self.description_edit.setPlainText(snapshot.description)
        layout.addWidget(self.description_edit)
        
        # Buttons
        buttons = QHBoxLayout()
        
        save_button = QPushButton('Save')
        save_button.clicked.connect(self.accept)
        buttons.addWidget(save_button)
        
        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)
        
        layout.addLayout(buttons)
        
        # Adjust size to content
        self.adjustSize()
