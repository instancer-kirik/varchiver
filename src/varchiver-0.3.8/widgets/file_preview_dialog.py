from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTreeWidget, QTreeWidgetItem, QLabel, QLineEdit,
                             QCheckBox, QComboBox, QMessageBox, QSplitter,
                             QTabWidget, QToolBar, QToolButton, QMenu,
                             QFileIconProvider, QProgressBar, QSpacerItem,
                             QSizePolicy, QTextEdit, QStatusBar, QDialogButtonBox)
from PyQt6.QtCore import Qt, pyqtSignal, QFileInfo, QSize
from PyQt6.QtGui import QIcon
import os
import zipfile
import tarfile
import rarfile
from pathlib import Path
from typing import List, Optional
from ..utils.archive_utils import get_archive_type
import tempfile
import shutil

class FilePreviewDialog(QDialog):
    """Enhanced file preview dialog with advanced browsing capabilities"""
    
    files_selected = pyqtSignal(list)
    
    def __init__(self, files, mode="create", parent=None):
        super().__init__(parent)
        self.files = files
        self.mode = mode
        self.selected_files = set()
        self.temp_dir = None
        self.current_archive = None
        self.setup_ui()
        self.populate_tree()
        
    def setup_ui(self):
        """Set up the enhanced UI"""
        self.setWindowTitle("Advanced File Browser")
        self.setMinimumSize(1000, 700)
        
        layout = QVBoxLayout(self)
        
        # Add toolbar
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)
        
        # Create main splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: File tree
        tree_widget = QWidget()
        tree_layout = QVBoxLayout(tree_widget)
        
        # Search and filter controls
        filter_layout = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter files...")
        self.filter_input.textChanged.connect(self.apply_filter)
        
        self.filter_type = QComboBox()
        self.filter_type.addItems([
            "All Files", "Archives", "Documents", "Images", 
            "Source Code", "Media", "Compressed"
        ])
        self.filter_type.currentTextChanged.connect(self.apply_filter_type)
        
        filter_layout.addWidget(self.filter_input)
        filter_layout.addWidget(self.filter_type)
        tree_layout.addLayout(filter_layout)
        
        # File tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Size", "Type", "Modified"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.itemChanged.connect(self.on_item_changed)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        tree_layout.addWidget(self.tree)
        
        self.splitter.addWidget(tree_widget)
        
        # Right side: Preview tabs
        self.preview_tabs = QTabWidget()
        self.preview_tabs.setTabsClosable(True)
        self.preview_tabs.tabCloseRequested.connect(self.close_preview_tab)
        
        # Add default preview tab
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.preview_tabs.addTab(self.text_preview, "Preview")
        
        self.splitter.addWidget(self.preview_tabs)
        
        # Set initial splitter sizes
        self.splitter.setSizes([400, 600])
        layout.addWidget(self.splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        layout.addWidget(self.status_bar)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def create_toolbar(self):
        """Create the toolbar with actions"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        
        # Navigation actions
        self.back_btn = QToolButton()
        self.back_btn.setText("←")
        self.back_btn.clicked.connect(self.navigate_back)
        toolbar.addWidget(self.back_btn)
        
        self.forward_btn = QToolButton()
        self.forward_btn.setText("→")
        self.forward_btn.clicked.connect(self.navigate_forward)
        toolbar.addWidget(self.forward_btn)
        
        toolbar.addSeparator()
        
        # View actions
        view_btn = QToolButton()
        view_btn.setText("View")
        view_menu = QMenu()
        view_menu.addAction("Icons", lambda: self.change_view("icons"))
        view_menu.addAction("Details", lambda: self.change_view("details"))
        view_menu.addAction("Tree", lambda: self.change_view("tree"))
        view_btn.setMenu(view_menu)
        view_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(view_btn)
        
        # Group actions
        group_btn = QToolButton()
        group_btn.setText("Group")
        group_menu = QMenu()
        group_menu.addAction("By Type", lambda: self.group_by("type"))
        group_menu.addAction("By Date", lambda: self.group_by("date"))
        group_menu.addAction("By Size", lambda: self.group_by("size"))
        group_btn.setMenu(group_menu)
        group_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(group_btn)
        
        toolbar.addSeparator()
        
        # Archive actions
        if self.mode == "browse":
            extract_btn = QToolButton()
            extract_btn.setText("Extract")
            extract_menu = QMenu()
            extract_menu.addAction("Extract Selected", self.extract_selected)
            extract_menu.addAction("Extract All", self.extract_all)
            extract_btn.setMenu(extract_menu)
            extract_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            toolbar.addWidget(extract_btn)
        
        return toolbar

    def on_item_double_clicked(self, item, column):
        """Handle double-click on items"""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if self.is_archive(path):
            # Preview archive contents
            self.preview_archive(path)
        elif self.is_text_file(path):
            # Preview text content
            self.preview_text_file(path)
        elif self.is_image_file(path):
            # Preview image
            self.preview_image(path)
        else:
            # Try to open with system default application
            self.open_with_default_app(path)

    def preview_archive(self, path):
        """Preview archive contents in a new tab"""
        try:
            # Create archive browser tab
            browser = QTreeWidget()
            browser.setHeaderLabels(["Name", "Size", "Modified"])
            
            archive_type = get_archive_type(path)
            if archive_type == "zip":
                with zipfile.ZipFile(path) as zf:
                    for info in zf.infolist():
                        item = QTreeWidgetItem([
                            info.filename,
                            self.format_size(info.file_size),
                            datetime.fromtimestamp(info.date_time).strftime('%Y-%m-%d %H:%M')
                        ])
                        browser.addTopLevelItem(item)
            
            tab_name = os.path.basename(path)
            self.preview_tabs.addTab(browser, f"📦 {tab_name}")
            self.preview_tabs.setCurrentIndex(self.preview_tabs.count() - 1)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to preview archive: {e}")

    def preview_text_file(self, path):
        """Preview text file content"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            editor = QTextEdit()
            editor.setReadOnly(True)
            editor.setPlainText(content)
            
            # Apply syntax highlighting if possible
            self.apply_syntax_highlighting(editor, path)
            
            tab_name = os.path.basename(path)
            self.preview_tabs.addTab(editor, f"📄 {tab_name}")
            self.preview_tabs.setCurrentIndex(self.preview_tabs.count() - 1)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to preview file: {e}")

    def apply_syntax_highlighting(self, editor, path):
        """Apply syntax highlighting based on file type"""
        ext = os.path.splitext(path)[1].lower()
        
        # Add syntax highlighting logic here
        # You can use QSyntaxHighlighter for different file types
        pass

    def show_context_menu(self, position):
        """Show context menu for items"""
        items = self.tree.selectedItems()
        if not items:
            return
            
        menu = QMenu(self)
        
        # Add basic actions
        menu.addAction("Open", lambda: self.open_selected())
        menu.addAction("Preview", lambda: self.preview_selected())
        
        # Add archive-specific actions if viewing an archive
        if self.current_archive:
            menu.addSeparator()
            menu.addAction("Extract Selected", self.extract_selected)
            menu.addAction("Extract All", self.extract_all)
        
        # Add grouping submenu
        group_menu = menu.addMenu("Group Selected")
        group_menu.addAction("New Group", lambda: self.create_group(items))
        
        if self.has_existing_groups():
            add_to_menu = group_menu.addMenu("Add to Group")
            self.populate_group_menu(add_to_menu, items)
        
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def create_group(self, items):
        """Create a new group from selected items"""
        name, ok = QInputDialog.getText(self, "New Group", "Enter group name:")
        if ok and name:
            group_id = self.next_group_id()
            self.groups[group_id] = {
                'name': name,
                'items': [item.data(0, Qt.ItemDataRole.UserRole) for item in items]
            }
            self.update_group_visuals()

    def update_group_visuals(self):
        """Update visual representation of groups"""
        # Similar to the tab grouping logic from advanced_tab_widget.py
        for group_id, group_data in self.groups.items():
            color = self.get_group_color(group_id)
            for path in group_data['items']:
                items = self.tree.findItems(
                    os.path.basename(path),
                    Qt.MatchFlag.MatchExactly,
                    0
                )
                for item in items:
                    item.setBackground(0, color)

    def extract_selected(self):
        """Extract selected items from archive"""
        items = self.tree.selectedItems()
        if not items:
            return
            
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        if not output_dir:
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(items))
        self.progress_bar.setValue(0)
        
        try:
            for i, item in enumerate(items):
                path = item.data(0, Qt.ItemDataRole.UserRole)
                self.extract_item(path, output_dir)
                self.progress_bar.setValue(i + 1)
                
            QMessageBox.information(
                self, "Success", 
                f"Successfully extracted {len(items)} items"
            )
            
        except Exception as e:
            QMessageBox.warning(
                self, "Error",
                f"Failed to extract some items: {e}"
            )
        finally:
            self.progress_bar.setVisible(False)

    def setup_preview_panel(self):
        """Setup the preview panel with tabs"""
        preview_tabs = QTabWidget()
        preview_tabs.setTabsClosable(True)
        preview_tabs.tabCloseRequested.connect(self.close_preview_tab)
        
        # Add default text preview
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        preview_tabs.addTab(self.text_preview, "Preview")
        
        return preview_tabs

    def apply_filter_type(self, filter_type):
        """Apply filter based on file type"""
        type_filters = {
            "Archives": ['.zip', '.tar', '.gz', '.bz2', '.rar'],
            "Documents": ['.txt', '.md', '.pdf', '.doc', '.docx'],
            "Images": ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
            "Source Code": ['.py', '.e', '.ie', '.oe', '.ey', '.ec', '.cpp', '.h'],
            "Media": ['.mp3', '.mp4', '.wav', '.avi'],
            "Compressed": ['.zip', '.gz', '.bz2', '.xz', '.7z']
        }
        
        selected_extensions = type_filters.get(filter_type, [])
        
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            path = item.data(0, Qt.ItemDataRole.UserRole)
            
            if filter_type == "All Files":
                item.setHidden(False)
            else:
                matches = any(path.lower().endswith(ext) for ext in selected_extensions)
                item.setHidden(not matches)

    def preview_default(self, path):
        """Default preview for unknown file types"""
        try:
            # Show basic file info
            info = QFileInfo(path)
            details = [
                f"File: {info.fileName()}",
                f"Size: {self._format_size(info.size())}",
                f"Type: {info.suffix().upper() if info.suffix() else 'Unknown'}",
                f"Modified: {info.lastModified().toString()}",
                f"Permissions: {self.format_permissions(info.permissions())}"
            ]
            
            self.text_preview.setPlainText("\n".join(details))
            
        except Exception as e:
            self.show_error(f"Failed to show file info: {e}")

    def preview_image(self, path):
        """Preview image files"""
        try:
            from PyQt6.QtGui import QPixmap
            from PyQt6.QtWidgets import QLabel, QScrollArea
            
            # Create image viewer
            scroll = QScrollArea()
            label = QLabel()
            pixmap = QPixmap(path)
            
            # Scale if too large
            if pixmap.width() > 800 or pixmap.height() > 600:
                pixmap = pixmap.scaled(800, 600, Qt.AspectRatioMode.KeepAspectRatio)
                
            label.setPixmap(pixmap)
            scroll.setWidget(label)
            
            tab_name = os.path.basename(path)
            self.preview_tabs.addTab(scroll, f"🖼️ {tab_name}")
            self.preview_tabs.setCurrentIndex(self.preview_tabs.count() - 1)
            
        except Exception as e:
            self.show_error(f"Failed to preview image: {e}")

    def format_permissions(self, permissions):
        """Format file permissions string"""
        perms = []
        if permissions & QFileInfo.Permission.ReadUser:
            perms.append("read")
        if permissions & QFileInfo.Permission.WriteUser:
            perms.append("write")
        if permissions & QFileInfo.Permission.ExeUser:
            perms.append("execute")
        return ", ".join(perms)

    def navigate_back(self):
        """Navigate to previous directory"""
        if hasattr(self, 'history') and self.history:
            path = self.history.pop()
            self.current_path = path
            self.populate_tree()

    def navigate_forward(self):
        """Navigate to next directory"""
        if hasattr(self, 'forward_history') and self.forward_history:
            path = self.forward_history.pop()
            self.current_path = path
            self.populate_tree()
    def navigate_to_path(self, path):
        """Navigate to a specific path"""
        self.current_path = path
        self.populate_tree()
    def navigate_up(self):
        """Navigate up one level in the directory tree"""
        if self.current_path:
            self.current_path = os.path.dirname(self.current_path)
            self.populate_tree()
    def change_view(self, view_type):
        """Change view mode"""
        if view_type == "icons":
            self.tree.setViewMode(QTreeWidget.ViewMode.IconMode)
        elif view_type == "details":
            self.tree.setViewMode(QTreeWidget.ViewMode.TreeMode)
        elif view_type == "tree":
            self.tree.setViewMode(QTreeWidget.ViewMode.TreeMode)
            self.tree.setIndentation(20)

    def group_by(self, criteria):
        """Group items by criteria"""
        self.tree.clear()
        
        if criteria == "type":
            self.group_by_type()
        elif criteria == "date":
            self.group_by_date()
        elif criteria == "size":
            self.group_by_size()

    def group_by_type(self):
        """Group files by type"""
        groups = {}
        
        for path in self.files:
            if os.path.exists(path):
                ext = os.path.splitext(path)[1].lower() or "No Extension"
                if ext not in groups:
                    groups[ext] = []
                groups[ext].append(path)
        
        for ext, files in sorted(groups.items()):
            group_item = QTreeWidgetItem([ext, "", "Group"])
            self.tree.addTopLevelItem(group_item)
            
            for file_path in files:
                self._add_file_item(file_path, group_item)

    def extract_all(self):
        """Extract all files from archive"""
        if not self.current_archive:
            return
        
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        if not output_dir:
            return
        
        try:
            archive_type = self.get_archive_type(self.current_archive)
            if archive_type == "zip":
                with zipfile.ZipFile(self.current_archive) as zf:
                    zf.extractall(output_dir)
                
            QMessageBox.information(
                self, "Success",
                "Archive extracted successfully"
            )
            
        except Exception as e:
            self.show_error(f"Failed to extract archive: {e}")

    def has_existing_groups(self):
        """Check if there are existing groups"""
        return hasattr(self, 'groups') and bool(self.groups)

    def next_group_id(self):
        """Get next available group ID"""
        if not hasattr(self, 'groups'):
            self.groups = {}
        return max(self.groups.keys(), default=0) + 1

    def get_group_color(self, group_id):
        """Get color for group"""
        colors = [
            QColor("#5E81AC"),  # Blue
            QColor("#A3BE8C"),  # Green
            QColor("#B48EAD"),  # Purple
            QColor("#D08770"),  # Orange
            QColor("#BF616A"),  # Red
        ]
        return colors[group_id % len(colors)]

    def populate_group_menu(self, menu, items):
        """Populate group menu with existing groups"""
        for group_id, group_data in self.groups.items():
            action = QAction(group_data['name'], self)
            action.triggered.connect(
                lambda checked, gid=group_id: self.add_to_group(items, gid)
            )
            menu.addAction(action)

    def add_to_group(self, items, group_id):
        """Add items to existing group"""
        if group_id in self.groups:
            for item in items:
                path = item.data(0, Qt.ItemDataRole.UserRole)
                if path not in self.groups[group_id]['items']:
                    self.groups[group_id]['items'].append(path)
            self.update_group_visuals()

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