from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QProgressBar,
                            QTreeWidget, QTreeWidgetItem, QHeaderView, QApplication,
                            QPushButton, QHBoxLayout)
from PyQt6.QtCore import Qt

class ArchiveTreeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Archive Contents")
        self.setMinimumSize(800, 600)
        self.setSizeGripEnabled(True)
        
        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Info label
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Create tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Name', 'Size', 'Compressed', 'Ratio'])
        self.tree.setAlternatingRowColors(True)
        self.tree.setSortingEnabled(True)
        layout.addWidget(self.tree)
        
        # Create buttons
        button_layout = QHBoxLayout()
        
        expand_button = QPushButton("Expand All")
        expand_button.clicked.connect(self.tree.expandAll)
        button_layout.addWidget(expand_button)
        
        collapse_button = QPushButton("Collapse All")
        collapse_button.clicked.connect(self.tree.collapseAll)
        button_layout.addWidget(collapse_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)

    def prepare_for_loading(self):
        """Prepare dialog for loading new content"""
        self.tree.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.info_label.setText("Loading archive contents...")

    def update_progress(self, current, total):
        """Update progress bar"""
        if total > 0:
            self.progress_bar.setValue(current * 100 // total)

    def loading_finished(self):
        """Hide progress bar when loading is complete"""
        self.progress_bar.setVisible(False)
        
    def show_contents(self, contents):
        """Display archive contents in tree dialog"""
        if not contents:
            self.info_label.setText("No files found in archive")
            self.progress_bar.setVisible(False)
            return

        # Clear tree
        self.tree.clear()
        self.progress_bar.setVisible(True)

        # Create a dictionary to store directory items
        dir_items = {}
        
        # Process each file
        total_size = 0
        total_compressed = 0
        total_files = 0
        
        # Sort contents by path to ensure parent directories are created first
        contents = sorted(contents, key=lambda x: x['path'])
        
        # First pass: create all directories
        for file_info in contents:
            if file_info.get('is_dir', False):
                path = file_info.get('path', '')
                parent_path = file_info.get('parent_path', '')
                name = file_info.get('name', '')
                
                if not path or not name:
                    continue
                    
                # Get parent item
                parent_item = None
                if parent_path:
                    parent_info = dir_items.get(parent_path)
                    if parent_info:
                        parent_item = parent_info['item']
                
                # Create directory item
                item = QTreeWidgetItem()
                item.setText(0, name)
                
                # Store name and path for sorting
                item.setData(0, Qt.ItemDataRole.UserRole, name.lower())
                item.setData(0, Qt.ItemDataRole.UserRole + 1, path)
                
                # Add to parent or root
                if parent_item:
                    parent_item.addChild(item)
                else:
                    self.tree.addTopLevelItem(item)
                
                # Store directory item
                dir_items[path] = {
                    'item': item,
                    'size': 0,
                    'compressed': 0
                }
        
        # Second pass: add files
        batch_size = 100
        for i in range(0, len(contents), batch_size):
            batch = contents[i:i + batch_size]
            
            for file_info in batch:
                if file_info.get('is_dir', False):
                    continue
                    
                path = file_info.get('path', '')
                parent_path = file_info.get('parent_path', '')
                name = file_info.get('name', '')
                size = file_info.get('size', 0)
                compressed = file_info.get('compressed', size)
                
                if not path or not name:
                    continue
                
                # Update totals
                total_size += size
                total_compressed += compressed
                total_files += 1
                
                # Get parent item
                parent_item = None
                if parent_path:
                    parent_info = dir_items.get(parent_path)
                    if parent_info:
                        parent_item = parent_info['item']
                
                # Create file item
                item = QTreeWidgetItem()
                item.setText(0, name)
                item.setText(1, self._format_size(size))
                item.setText(2, self._format_size(compressed))
                
                # Calculate and format compression ratio
                if size > 0:
                    ratio = (1 - compressed / size)
                    item.setText(3, f"{ratio:.3f}")
                else:
                    item.setText(3, "0.000")
                
                # Store raw values for sorting
                item.setData(0, Qt.ItemDataRole.UserRole, name.lower())
                item.setData(0, Qt.ItemDataRole.UserRole + 1, path)
                item.setData(1, Qt.ItemDataRole.UserRole, size)
                item.setData(2, Qt.ItemDataRole.UserRole, compressed)
                item.setData(3, Qt.ItemDataRole.UserRole, ratio if size > 0 else 0)
                
                # Add to parent or root
                if parent_item:
                    parent_item.addChild(item)
                else:
                    self.tree.addTopLevelItem(item)
                
                # Update parent directory sizes
                current_path = parent_path
                while current_path:
                    if current_path in dir_items:
                        dir_info = dir_items[current_path]
                        dir_info['size'] += size
                        dir_info['compressed'] += compressed
                    parent_parts = [p for p in current_path.split('/') if p]
                    if len(parent_parts) > 1:
                        current_path = '/'.join(parent_parts[:-1]) + '/'
                    else:
                        break
            
            # Update progress
            self.progress_bar.setValue((i + len(batch)) * 100 // len(contents))
            QApplication.processEvents()

        # Update directory items
        for path, dir_info in dir_items.items():
            item = dir_info['item']
            size = dir_info['size']
            compressed = dir_info['compressed']
            
            if size > 0:
                item.setText(1, self._format_size(size))
                item.setText(2, self._format_size(compressed))
                ratio = (1 - compressed / size)
                item.setText(3, f"{ratio:.3f}")
                
                # Store raw values
                item.setData(1, Qt.ItemDataRole.UserRole, size)
                item.setData(2, Qt.ItemDataRole.UserRole, compressed)
                item.setData(3, Qt.ItemDataRole.UserRole, ratio)

        # Update column widths
        for i in range(4):
            self.tree.resizeColumnToContents(i)
        
        # Update info label
        if total_size > 0:
            ratio = (1 - total_compressed / total_size)
            self.info_label.setText(
                f"Total: {total_files} files, "
                f"{self._format_size(total_size)} "
                f"({self._format_size(total_compressed)}, "
                f"ratio: {ratio:.3f})"
            )
        else:
            self.info_label.setText(f"Total: {total_files} files")
            
        self.progress_bar.setVisible(False)

    def _format_size(self, size):
        """Format size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
