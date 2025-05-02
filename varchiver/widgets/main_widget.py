"""Main application widget."""

from pathlib import Path
import os
import signal
import sys
import subprocess
import tempfile
import shutil
import psutil
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QProgressBar, QTextEdit, QComboBox,
    QGroupBox, QCheckBox, QDialog, QGridLayout, QFrame,
    QInputDialog, QLineEdit, QMessageBox, QFileDialog, QFormLayout, QSlider,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QApplication, QStyle, QDialogButtonBox,
    QProgressDialog, QTreeView, QTabWidget, QMenu, QListWidget, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QDir, QUrl, QEvent, QSettings
from PyQt6.QtGui import QAction, QTextCursor

from ..threads.archive_thread import ArchiveThread
from ..threads.extraction_thread import ExtractionThread
from ..threads.browse_thread import BrowseThread
from ..threads.directory_update_thread import DirectoryUpdateThread
from ..utils.project_constants import DEFAULT_SKIP_PATTERNS, ARCHIVE_EXTENSIONS
from ..utils.archive_utils import get_archive_type, is_rar_available
from ..utils.theme_manager import ThemeManager
from ..utils.release_manager import ReleaseManager
from ..utils.git_manager import GitManager
from .file_preview_dialog import FilePreviewDialog
from .collision_dialog import CollisionDialog
from .git_widget import GitWidget
from .variable_calendar import VariableCalendarWidget
from .supabase_widget import SupabaseWidget
from .supabase_config_dialog import SupabaseConfigDialog

class MainWidget(QWidget):
    def __init__(self, parent=None):
        """Initialize the main widget"""
        super().__init__(parent)
        self.setWindowTitle('Varchiver')
        
        # Initialize instance variables
        self.archive_path = None  # Path to current archive
        self.current_archive_path = None  # Path to current archive for extraction
        self.current_contents = None  # Current archive contents
        self.current_thread = None  # Current operation thread
        self._browse_thread = None  # Browse thread for archives/directories
        self.password = None  # Current archive password 
        self.skip_checkboxes = {}  # Skip pattern checkboxes
        self.extraction_queue = []  # Queue for pending extractions
        
        # Initialize recent archives
        self.recent_archives = []
        self.recent_archives_file = os.path.expanduser('~/.config/varchiver/recent_archives.json')
        self.load_recent_archives()
        
        # Check RAR availability
        self.rar_available = is_rar_available()
        
        # Initialize theme manager
        self.theme_manager = ThemeManager()
        self.theme_manager.apply_theme()
        
        # Initialize Git widget and manager
        self.git_manager = GitManager()
        self.git_widget = GitWidget()
        self.git_widget.repo_changed.connect(self.on_repository_changed)
        self.git_widget.sequester_path_changed.connect(self.on_sequester_path_changed)
        self.git_widget.artifacts_path_changed.connect(self.on_artifacts_path_changed)
        self.git_widget.setVisible(False)  # Initially hidden
        
        # Initialize variable calendar widget
        self.variable_calendar = VariableCalendarWidget()
        self.variable_calendar.setVisible(False)
        
        # Initialize Supabase widget
        self.supabase_widget = SupabaseWidget()
        self.supabase_widget.setVisible(False)
        
        # Initialize UI
        self.setup_ui()

    def setup_ui(self):
        """Initialize the UI components."""
        main_layout = QVBoxLayout(self)
        
        # Mode selector and tools container
        mode_container = QWidget()
        mode_layout = QVBoxLayout(mode_container)
        
        # Add theme toggle and release manager next to mode selector
        mode_header = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            'Archive',           # Normal archiving with skip patterns
            'Dev Tools',        # Development tools and utilities
            'Variable Calendar' # Variable tracking and visualization
        ])
        self.mode_combo.setToolTip(
            'Operation mode:\n'
            'Archive: Normal archiving with skip patterns\n'
            'Dev Tools: Development utilities and configuration management\n'
            'Variable Calendar: Variable tracking and visualization'
        )
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_header.addWidget(self.mode_combo)
        
        # Theme toggle
        self.theme_button = QPushButton("Light Mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        mode_header.addWidget(self.theme_button)
        
        # Release Manager button
        self.release_button = QPushButton("Release Manager")
        self.release_button.clicked.connect(self.show_release_manager)
        mode_header.addWidget(self.release_button)
        
        mode_layout.addLayout(mode_header)
        main_layout.addWidget(mode_container)
        
        # Add recent archives section
        self.recent_group = QGroupBox("Recent Archives")
        recent_layout = QVBoxLayout(self.recent_group)
        
        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self._on_recent_archive_clicked)
        recent_layout.addWidget(self.recent_list)
        
        # Add clear recent button
        clear_recent_button = QPushButton("Clear Recent")
        clear_recent_button.clicked.connect(self.clear_recent_archives)
        recent_layout.addWidget(clear_recent_button)
        
        main_layout.addWidget(self.recent_group)
        
        # Add Git widget
        main_layout.addWidget(self.git_widget)
        
        # Add variable calendar widget
        main_layout.addWidget(self.variable_calendar)
        
        # Add Supabase widget (for Dev Tools mode)
        main_layout.addWidget(self.supabase_widget)
        
        # Create archive group
        self.archive_group = QGroupBox("Archive Operations")
        archive_layout = QVBoxLayout(self.archive_group)
        
        # Create toolbar
        toolbar = QHBoxLayout()
        
        # Browse button
        self.browse_button = QPushButton("Browse")
        self.browse_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogStart))
        self.browse_button.clicked.connect(self.browse_archive_dialog)
        toolbar.addWidget(self.browse_button)
        
        # Info button
        self.info_button = QPushButton("Info")
        self.info_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView))
        self.info_button.setEnabled(False)
        self.info_button.clicked.connect(self.show_archive_info)
        toolbar.addWidget(self.info_button)
        
        # Create archive button
        self.create_button = QPushButton("Create Archive")
        self.create_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.create_button.clicked.connect(self.compress_files_dialog)
        toolbar.addWidget(self.create_button)
        
        # Extract buttons
        extract_button_section = QHBoxLayout()

        # Queue Extract button
        self.queue_extract_button = QPushButton("Queue Extract")
        self.queue_extract_button.clicked.connect(lambda: self.extract_archive_dialog(queue=True))
        extract_button_section.addWidget(self.queue_extract_button)

        # Start Extract button
        self.start_extract_button = QPushButton("Start Extract")
        self.start_extract_button.clicked.connect(self.process_extraction_queue)
        self.start_extract_button.setEnabled(False)
        extract_button_section.addWidget(self.start_extract_button)

        extract_button_section.addStretch()
        toolbar.addLayout(extract_button_section)
        
        # Add toolbar to layout
        archive_layout.addLayout(toolbar)
        
        # Create skip patterns section
        skip_group = QGroupBox("Skip Patterns")
        skip_layout = QVBoxLayout(skip_group)
        
        # Add description
        skip_desc = QLabel("Common patterns to exclude:")
        skip_desc.setWordWrap(True)
        skip_layout.addWidget(skip_desc)
        
        # Create horizontal layout for skip patterns
        skip_patterns_layout = QHBoxLayout()
        
        # Create a flow layout container
        flow_widget = QWidget()
        flow_layout = QHBoxLayout(flow_widget)
        flow_layout.setSpacing(4)
        
        # Add checkboxes to flow layout
        self.skip_checkboxes = {}
        for category, patterns in DEFAULT_SKIP_PATTERNS.items():
            checkbox = QCheckBox(category)
            checkbox.setToolTip("\n".join(patterns))
            checkbox.setChecked(True)
            self.skip_checkboxes[category] = checkbox
            flow_layout.addWidget(checkbox)
        
        # Add stretch to prevent checkboxes from expanding
        flow_layout.addStretch()
        
        # Add flow widget to skip layout
        skip_patterns_layout.addWidget(flow_widget)
        skip_layout.addLayout(skip_patterns_layout)
        
        # Add custom patterns input
        custom_layout = QHBoxLayout()
        custom_label = QLabel("Custom:")
        custom_layout.addWidget(custom_label)
        
        self.skip_patterns_edit = QLineEdit()
        self.skip_patterns_edit.setPlaceholderText("Additional patterns to skip (comma-separated)")
        self.skip_patterns_edit.setToolTip("Enter additional patterns to skip, separated by commas")
        custom_layout.addWidget(self.skip_patterns_edit)
        
        skip_layout.addLayout(custom_layout)
        archive_layout.addWidget(skip_group)
        
        # Options group
        options_group = QGroupBox("Options")
        options_layout = QFormLayout(options_group)

        # Compression level slider
        compression_layout = QHBoxLayout()
        
        # Add min label (Fast)
        min_label = QLabel("Fast")
        min_label.setToolTip("Faster compression, larger file size")
        min_label.setStyleSheet("color: #2196F3; font-weight: bold;")  # Blue for speed
        compression_layout.addWidget(min_label)
        
        # Compression slider
        self.compression_slider = QSlider(Qt.Orientation.Horizontal)
        self.compression_slider.setMinimum(0)
        self.compression_slider.setMaximum(9)
        self.compression_slider.setValue(5)
        self.compression_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.compression_slider.setTickInterval(1)
        self.compression_slider.setMinimumWidth(200)
        self.compression_slider.setEnabled(True)
        compression_layout.addWidget(self.compression_slider)
        
        # Add max label (Small)
        max_label = QLabel("Small")
        max_label.setToolTip("Slower compression, smaller file size")
        max_label.setStyleSheet("color: #4CAF50; font-weight: bold;")  # Green for size
        compression_layout.addWidget(max_label)
        
        # Add compression value label
        self.compression_value_label = QLabel("Level 5: Balanced compression")
        self.compression_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.compression_value_label.setStyleSheet("""
            QLabel {
                background-color: #222222;
                color: white;
                padding: 4px;
                border-radius: 4px;
                margin: 4px;
            }
        """)
        
        # Add layouts to options group
        options_layout.addRow("Compression:", compression_layout)
        options_layout.addRow(self.compression_value_label)
        
        # Connect slider after creating the label
        self.compression_slider.valueChanged.connect(self.update_compression_label)
        
        # Collision strategy selector
        collision_group = QGroupBox("On File Collision")
        collision_layout = QVBoxLayout(collision_group)
        
        # Add description
        collision_desc = QLabel("Choose how to handle existing files:")
        collision_desc.setWordWrap(True)
        collision_layout.addWidget(collision_desc)
        
        self.collision_combo = QComboBox()
        self.collision_combo.addItems([
            'ask',      # Ask for each file
            'skip',     # Skip existing files
            'rename',   # Rename new files
            'newer',    # Keep newer files
            'older',    # Keep older files
            'larger',   # Keep larger files
            'smaller',  # Keep smaller files
            'overwrite' # Always overwrite
        ])
        
        # Style the combo box to be more prominent
        self.collision_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 2px solid #666;
                border-radius: 4px;
                min-width: 150px;
                font-weight: bold;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
        """)
        
        collision_layout.addWidget(self.collision_combo)
     
        # Add to options layout
        options_layout.addRow("", collision_group)
        
        # Preserve permissions checkbox
        self.preserve_permissions = QCheckBox("Preserve file permissions")
        self.preserve_permissions.setChecked(True)
        self.preserve_permissions.setEnabled(True)
        options_layout.addRow("", self.preserve_permissions)
        
        archive_layout.addWidget(options_group)
        
        # Create tree view for file display
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Name", "Size", "Modified", "Ratio"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.setAlternatingRowColors(True)
        self._tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        archive_layout.addWidget(self._tree)
        
        main_layout.addWidget(self.archive_group)
        
        # Status label for detailed progress
        self.status_label = QLabel(" ")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666666;
                padding: 10px;
                font-size: 12px;
                background-color: #AACCCC;
                border-radius: 4px;
            }
        """)
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)
        
        # Progress bar for loading feedback
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)
        
        # Error box with consistent styling
        error_box = QGroupBox()
        error_layout = QHBoxLayout(error_box)
        error_box.setStyleSheet("""
            QGroupBox {
                border: none;
                margin-top: 10px;
            }
        """)
        
        self.error_label = QLabel('')
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background-color: #d32f2f;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        error_layout.addWidget(self.error_label)
        
        self.copy_error_button = QPushButton("Copy Error")
        self.copy_error_button.clicked.connect(self.copy_error_to_clipboard)
        self.copy_error_button.setVisible(False)
        error_layout.addWidget(self.copy_error_button)
        
        main_layout.addWidget(error_box)
        
        # Update theme button
        self.update_theme_button()
        
        # Initially hide archive group in Dev Tools mode
        if self.mode_combo.currentText() == "Dev Tools":
            self.archive_group.hide()
            self.git_widget.show()
            self.recent_group.hide()
            self.variable_calendar.hide()
            self.supabase_widget.show()
        elif self.mode_combo.currentText() == "Variable Calendar":
            self.git_widget.hide()
            self.archive_group.hide()
            self.recent_group.hide()
            self.variable_calendar.show()
            self.supabase_widget.hide()
        else:
            self.archive_group.show()
            self.git_widget.hide()
            self.recent_group.show()
            self.variable_calendar.hide()
            self.supabase_widget.hide()

    def update_compression_label(self):
        """Update the compression label based on slider value"""
        value = self.compression_slider.value()
        
        # Update value label with description
        if value < 3:
            color = "#2196F3"  # Blue for fast
            desc = "Faster compression, larger file"
        elif value < 7:
            color = "#222222"  # Orange for balanced
            desc = "Balanced compression"
        else:
            color = "#4CAF50"  # Green for small
            desc = "Slower compression, smaller file"
            
        self.compression_value_label.setText(f"Level {value}: {desc}")
        self.compression_value_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 4px;
                border-radius: 4px;
                margin: 4px;
            }}
        """)        

    def browse_archive_dialog(self):
        """Show file dialog to select archive"""
        try:
            # Create file dialog
            dialog = QFileDialog(self)
            dialog.setWindowTitle("Select Archive or Directory")
            
            # Set file mode to handle both files and directories
            dialog.setFileMode(QFileDialog.FileMode.AnyFile)
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
            dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
            
            # Add mounted devices to sidebar
            sidebar = []
            for device in self._get_mounted_devices():
                url = QUrl.fromLocalFile(device['path'])
                sidebar.append(url)
            dialog.setSidebarUrls(sidebar)
            
            # Add a button to switch between file and directory mode
            dir_button = QPushButton("Toggle Directory Mode", dialog)
            dir_button.setCheckable(True)
            dir_button.setChecked(False)
            dir_button.clicked.connect(lambda checked: self._toggle_dialog_mode(dialog, checked))
            
            # Add the button to the dialog's layout
            layout = dialog.layout()
            if layout:
                # Try to find a good spot for the button
                if isinstance(layout, QGridLayout):
                    # Add to the last row
                    row = layout.rowCount()
                    layout.addWidget(dir_button, row, 0, 1, -1)
                else:
                    # If not a grid layout, just add to the end
                    layout.addWidget(dir_button)
            
            # Find the tree view and connect double-click handler
            tree_view = dialog.findChild(QTreeView)
            if tree_view:
                tree_view.doubleClicked.connect(lambda index: self._handle_double_click(dialog, index))
            
            # Set name filters
            dialog.setNameFilter(
                "All Supported Types (*.zip *.tar *.tar.gz *.tgz *.tar.bz2 *.7z *.rar);;Archives (*.zip);;TAR Archives (*.tar);;Gzipped TAR Archives (*.tar.gz);;TGZ Archives (*.tgz);;Bzip2 TAR Archives (*.tar.bz2);;7z Archives (*.7z);;RAR Archives (*.rar);;All Files (*)"
            )
            
            if dialog.exec() == QFileDialog.DialogCode.Accepted:
                selected_path = dialog.selectedFiles()[0]
                if selected_path:
                    # Store the selected path and update UI
                    self.current_archive_path = selected_path
                    self.status_label.setText(f"Selected: {os.path.basename(selected_path)}")
                    
                    # If it's a directory, create a list of files
                    if os.path.isdir(selected_path):
                        self.current_archive = [selected_path]
                        self._populate_tree(self.current_archive)
                        self.status_label.setText(f"Directory selected: {selected_path}")
                    else:
                        # Handle as archive
                        self._open_archive(selected_path)
                        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error browsing: {str(e)}")

    def _handle_double_click(self, dialog, index):
        """Handle double click in file dialog"""
        try:
            if not index.isValid():
                return
                
            path = dialog.directory().filePath(index.data())
            if os.path.isdir(path):
                # If it's a directory and no file is selected, enter the directory
                dialog.setDirectory(path)
                dialog.selectFile("")
        except Exception as e:
            self.handle_error(f"Error handling double click: {str(e)}")

    def _toggle_dialog_mode(self, dialog, checked):
        """Toggle between file and directory mode in file dialog"""
        if checked:
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            dialog.setOption(QFileDialog.Option.ShowDirsOnly)
        else:
            dialog.setFileMode(QFileDialog.FileMode.AnyFile)
            dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)

    def _open_archive(self, archive_path, password=None):
        """Open an archive and add it to recent archives"""
        try:
            # Add to recent archives
            self.add_recent_archive(archive_path)
            
            # Existing open archive logic...
            self.current_archive_path = archive_path
            self.status_label.setText(f"Opening: {os.path.basename(archive_path)}")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.error_label.setVisible(False)

            # Create and start browse thread
            self._browse_thread = BrowseThread(archive_path, password)
            self._browse_thread.contents_ready.connect(self._on_contents_ready)
            self._browse_thread.error.connect(self._on_error)
            self._browse_thread.status.connect(self.update_status)
            self._browse_thread.progress.connect(self._on_progress)
            self._browse_thread.start()

        except Exception as e:
            self.show_error(str(e))

    def browse_complete(self):
        """Called when browsing is complete"""
        self.browse_button.setEnabled(True)
        self.status_label.setText("Archive loaded successfully")
        self.progress_bar.hide()

    def _on_contents_ready(self, contents):
        """Called when archive contents are ready"""
        self._tree.clear()
        self._populate_tree(contents)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Archive: {os.path.basename(self.current_archive_path)}")
        self.browse_button.setEnabled(True)

    def _on_error(self, error_msg):
        """Called when an error occurs"""
        self.show_error(error_msg)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)  # Reset progress bar
        self.browse_button.setEnabled(True)

    def _on_progress(self, progress):
        """Called when progress is updated"""
        self.progress_bar.setValue(progress)

    def update_status(self, status):
        """Update status message"""
        self.status_label.setText(status)

    def show_error(self, message):
        """Show error message"""
        self.error_label.setText(message)
        self.error_label.setVisible(True)
        self.copy_error_button.setVisible(True)
        self.browse_button.setEnabled(True)
        self.status_label.setText("Error loading archive.")
        self.progress_bar.setVisible(False)

    def extract_archive_dialog(self, queue=False):
        """Show file dialog to extract an archive or update from directory"""
        try:
            if not self.current_archive_path:
                self.show_error("Please select an archive or directory first")
                return

            # Create dialog for extraction settings
            dialog = QDialog(self)
            dialog.setWindowTitle("Extract Archive")
            layout = QVBoxLayout(dialog)

            # Add output directory selection
            output_layout = QHBoxLayout()
            output_label = QLabel("Output Directory:", dialog)
            output_edit = QLineEdit(dialog)
            output_edit.setText(os.path.splitext(self.current_archive_path)[0])
            output_browse = QPushButton("Browse", dialog)
            output_browse.clicked.connect(lambda: self._browse_output_dir(output_edit))
            output_layout.addWidget(output_label)
            output_layout.addWidget(output_edit)
            output_layout.addWidget(output_browse)
            layout.addLayout(output_layout)

            # Add password field only for RAR and 7z archives
            if any(self.current_archive_path.lower().endswith(ext) for ext in ['.rar', '.7z']):
                password_layout = QHBoxLayout()
                password_label = QLabel("Password (if needed):", dialog)
                password_edit = QLineEdit(dialog)
                password_edit.setEchoMode(QLineEdit.EchoMode.Password)
                password_layout.addWidget(password_label)
                password_layout.addWidget(password_edit)
                layout.addLayout(password_layout)
            else:
                password_edit = None

            # Add buttons
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
                dialog
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Queue the extraction
                extraction_info = {
                    'archive_name': self.current_archive_path,
                    'output_dir': output_edit.text(),
                    'password': password_edit.text() if password_edit else None,
                    'collision_strategy': self.collision_combo.currentText(),
                    'preserve_permissions': self.preserve_permissions.isChecked(),
                    'skip_patterns': self.get_active_skip_patterns()
                }
                if queue:
                    self.extraction_queue.append(extraction_info)
                    self.start_extract_button.setEnabled(True)
                    self.update_status(f"Queued extraction of {os.path.basename(self.current_archive_path)}")
                else:
                    self.extract_archive(**extraction_info)
                    self.update_status(f"Extracting {os.path.basename(self.current_archive_path)}")

        except Exception as e:
            self.show_error(f"Error setting up extraction: {str(e)}")

    def process_extraction_queue(self):
        """Process the next item in the extraction queue"""
        if not self.extraction_queue:
            self.start_extract_button.setEnabled(False)
            return

        if self.current_thread and self.current_thread.isRunning():
            self.show_error("An operation is already in progress")
            return

        # Get next extraction from queue
        extraction_info = self.extraction_queue.pop(0)
        
        # Start the extraction
        self.extract_archive(**extraction_info)
        
        # Update button state
        self.start_extract_button.setEnabled(bool(self.extraction_queue))

    def extract_archive(self, archive_name, output_dir=None, password=None, skip_patterns=None,
                       collision_strategy=None, preserve_permissions=None, file_list=None):
        """Extract files from an archive"""
        try:
            # Create progress dialog
            progress_dialog = QProgressDialog("Extracting files...", "Cancel", 0, 100, self)
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setAutoClose(True)
            progress_dialog.setAutoReset(True)
            progress_dialog.show()

            # Create and start extraction thread
            self.current_thread = ExtractionThread(
                archive_name,
                output_dir,
                collision_strategy,
                skip_patterns,
                password,
                preserve_permissions,
                file_list
            )

            # Connect signals
            self.current_thread.progress.connect(progress_dialog.setValue)
            self.current_thread.status.connect(self.update_status)
            self.current_thread.error.connect(self.handle_error)
            self.current_thread.finished.connect(lambda path: self._on_extract_complete())
            self.current_thread.finished.connect(lambda path: progress_dialog.setValue(100))
            self.current_thread.finished.connect(lambda path: progress_dialog.close())
            
            # Disable controls during extraction
            self._enable_controls(False)
            
            # Start extraction
            self.current_thread.start()

        except Exception as e:
            self.show_error(f"Error starting extraction: {str(e)}")
            self._enable_controls(True)

    def extraction_finished(self, extract_path):
        """Handle completion of extraction operation"""
        self.update_status(f"Extraction completed: {extract_path}")
        self._enable_controls(True)
        
        # Process next extraction if any
        if self.extraction_queue:
            self.process_extraction_queue()

    def _on_collision_question(self, target_path):
        """Handle collision question from extraction thread"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setText(f"File already exists: {os.path.basename(target_path)}")
        msg.setInformativeText("What would you like to do?")
        msg.setWindowTitle("File Collision")
        
        # Add buttons
        skip_button = msg.addButton("Skip", QMessageBox.ButtonRole.RejectRole)
        overwrite_button = msg.addButton("Overwrite", QMessageBox.ButtonRole.AcceptRole)
        rename_button = msg.addButton("Rename", QMessageBox.ButtonRole.ActionRole)
        
        msg.exec()
        
        clicked = msg.clickedButton()
        if clicked == skip_button:
            self.current_thread.collision_response.emit(False)
        elif clicked == overwrite_button:
            try:
                if os.path.isfile(target_path):
                    os.remove(target_path)
                self.current_thread.collision_response.emit(True)
            except Exception as e:
                self.show_error(f"Error overwriting file: {str(e)}")
                self.current_thread.collision_response.emit(False)
        else:  # rename
            base, ext = os.path.splitext(target_path)
            counter = 1
            new_path = target_path
            while os.path.exists(new_path):
                new_path = f"{base}_{counter}{ext}"
                counter += 1
            self.current_thread.rename_path.emit(new_path)
            self.current_thread.collision_response.emit(True)

    def compress_files_dialog(self):
        """Show dialog to select files and create archive"""
        # Create file dialog
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Choose Files/Directories to Archive")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)  # Allow selecting multiple files
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setOption(QFileDialog.Option.DontUseCustomDirectoryIcons)
        
        # Get the tree view from the dialog
        tree_view = dialog.findChild(QTreeView)
        if tree_view:
            tree_view.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        
        # Add a button to select current directory
        current_dir_button = QPushButton("Select Current Directory", dialog)
        current_dir_button.clicked.connect(lambda: self._select_current_dir(dialog))
        
        # Add a button to toggle directory mode
        dir_mode_button = QPushButton("Toggle Directory Mode", dialog)
        dir_mode_button.setCheckable(True)
        
        def toggle_dir_mode(checked):
            if checked:
                dialog.setFileMode(QFileDialog.FileMode.Directory)
                dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
            else:
                dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
                dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
        
        dir_mode_button.toggled.connect(toggle_dir_mode)
        
        # Add buttons to dialog layout
        layout = dialog.layout()
        if layout:
            # Try to find a good spot for the buttons
            if isinstance(layout, QGridLayout):
                # Add to the last row
                row = layout.rowCount()
                layout.addWidget(current_dir_button, row, 0)
                layout.addWidget(dir_mode_button, row, 1)
            else:
                # If not a grid layout, just add to the end
                layout.addWidget(current_dir_button)
                layout.addWidget(dir_mode_button)
        
        selected_files = []
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Handle both files and directories
            if dialog.fileMode() == QFileDialog.FileMode.Directory:
                selected_files = [dialog.selectedFiles()[0]]  # Single directory mode
            else:
                selected_files = dialog.selectedFiles()  # Multiple files/directories mode
            
            if not selected_files:
                return
            
            # Show save dialog
            save_dialog = QFileDialog(self)
            save_dialog.setWindowTitle("Save Archive As")
            save_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            save_dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
            
            # Set name filters
            file_filter = ";;".join(ARCHIVE_EXTENSIONS.keys())
            save_dialog.setNameFilter(file_filter)
            
            # Set default name based on selection
            if len(selected_files) == 1:
                default_name = os.path.basename(selected_files[0])
            else:
                default_name = os.path.basename(os.path.dirname(selected_files[0]))
            if not default_name:
                default_name = "archive"
            save_dialog.selectFile(default_name + ".zip")
            
            # Set default directory to the directory of selected files
            save_dialog.setDirectory(os.path.dirname(selected_files[0]))
            
            # Connect filter change signal
            save_dialog.filterSelected.connect(lambda selected_filter: self.on_filter_selected(save_dialog, selected_filter))
            
            if save_dialog.exec() != QDialog.DialogCode.Accepted:
                return

            archive_name = save_dialog.selectedFiles()[0]
            archive_dir = os.path.dirname(archive_name)
            
            # Check if we need elevated privileges
            needs_elevation = not os.access(archive_dir, os.W_OK)
            if os.path.exists(archive_name):
                needs_elevation = needs_elevation or not os.access(archive_name, os.W_OK)
                # Ask for confirmation to overwrite
                reply = QMessageBox.question(self, "Confirm Overwrite",
                    f"File already exists: {archive_name}\nDo you want to overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Ask for elevated privileges if needed
            if needs_elevation:
                reply = QMessageBox.question(self, "Elevated Privileges Required",
                    f"Cannot write to selected location: {archive_name}\n"
                    "Do you want to try with elevated privileges?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    
                if reply == QMessageBox.StandardButton.No:
                    return
                    
                try:
                    # Test if we can write to directory with elevated privileges
                    subprocess.run(['pkexec', 'touch', os.path.join(archive_dir, '.varchiver_test')], check=True)
                    subprocess.run(['pkexec', 'rm', os.path.join(archive_dir, '.varchiver_test')], check=True)
                    
                    # Remove existing file if it exists
                    if os.path.exists(archive_name):
                        subprocess.run(['pkexec', 'rm', '-f', archive_name], check=True)
                        
                    # Store that we'll need elevated privileges for this path
                    self._needs_elevation = True
                    
                except subprocess.CalledProcessError:
                    QMessageBox.critical(self, "Error", 
                        "Failed to get elevated privileges. Please choose a different location.")
                    return
                except Exception as e:
                    QMessageBox.critical(self, "Error", str(e))
                    return
            else:
                self._needs_elevation = False
            
            password, ok = QInputDialog.getText(self, "Password", "Set password (optional):", QLineEdit.EchoMode.Password)
            if ok:
                self.compress_files(selected_files, archive_name, password)
            else:
                self.compress_files(selected_files, archive_name)
                
            # Store password for later use when opening the archive
            self.password = password if password and ok else None

    def compress_files(self, files, archive_name=None, password=None, compression_level=None, 
                      skip_patterns=None, collision_strategy=None, preserve_permissions=None):
        """Compress files into an archive"""
        try:
            if not files:
                self.show_error("No files selected for compression")
                return

            # Get compression level and options from UI if not specified
            if compression_level is None:
                compression_level = self.compression_slider.value()
            if skip_patterns is None:
                skip_patterns = self.get_active_skip_patterns()
            if collision_strategy is None:
                collision_strategy = self.collision_combo.currentText()
            if preserve_permissions is None:
                preserve_permissions = self.preserve_permissions.isChecked()

            # Show progress dialog
            progress_dialog = QProgressDialog("Compressing files...", "Cancel", 0, 100, self)
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setAutoClose(True)
            progress_dialog.setAutoReset(True)
            progress_dialog.show()

            # Create archive thread
            self.current_thread = ArchiveThread(
                files=files,
                archive_name=archive_name,
                password=password,
                compression_level=compression_level,
                skip_patterns=skip_patterns,
                collision_strategy=collision_strategy,
                preserve_permissions=preserve_permissions
            )

            # Connect signals
            self.current_thread.progress.connect(progress_dialog.setValue)
            self.current_thread.finished.connect(lambda: self._on_archive_complete())
            self.current_thread.finished.connect(lambda: progress_dialog.setValue(100))
            self.current_thread.finished.connect(lambda: progress_dialog.close())
            self.current_thread.error.connect(self.handle_error)

            # Start compression
            self.current_thread.start()

        except Exception as e:
            self.show_error(f"Error starting compression: {str(e)}")

    def display_filesystem_item(self, path):
        """Display a file system item (file or directory) in the tree view"""
        if os.path.exists(path):
            root_item = QTreeWidgetItem(self._tree)
            root_item.setText(0, os.path.basename(path))
            root_item.setData(0, Qt.ItemDataRole.UserRole, path)
            
            if os.path.isdir(path):
                # Just add a dummy item to show the expand arrow
                root_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
                dummy = QTreeWidgetItem()
                root_item.addChild(dummy)
                # Connect the expand signal if not already connected
                if not hasattr(self, '_expand_connected'):
                    self._tree.itemExpanded.connect(self._load_directory_contents)
                    self._expand_connected = True
            else:
                root_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))

    def _load_directory_contents(self, item):
        """Load directory contents when expanding a directory in the tree view"""
        # Remove dummy item if it exists
        if item.childCount() == 1 and item.child(0).text(0) == "":
            item.removeChild(item.child(0))
        
        # If already loaded, don't reload
        if item.childCount() > 0:
            return

        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(path, (str, bytes, os.PathLike)):
            self.handle_error(f"Invalid path type: {type(path)}")
            return
            
        try:
            for entry in os.scandir(path):
                child_item = QTreeWidgetItem(item)
                child_item.setText(0, entry.name)
                child_item.setData(0, Qt.ItemDataRole.UserRole, entry.path)
                
                if entry.is_dir():
                    child_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
                    # Add dummy item to show expand arrow
                    dummy = QTreeWidgetItem()
                    child_item.addChild(dummy)
                else:
                    child_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        except PermissionError:
            error_item = QTreeWidgetItem(item)
            error_item.setText(0, "Permission denied")
            error_item.setDisabled(True)
        except Exception as e:
            error_item = QTreeWidgetItem(item)
            error_item.setText(0, f"Error: {str(e)}")
            error_item.setDisabled(True)

    def _add_directory_contents(self, parent_item, directory_path):
        """Recursively add directory contents to the tree view"""
        parent_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        
        try:
            for entry in os.scandir(directory_path):
                child_item = QTreeWidgetItem(parent_item)
                child_item.setText(0, entry.name)
                child_item.setData(0, Qt.ItemDataRole.UserRole, entry.path)
                
                if entry.is_dir():
                    self._add_directory_contents(child_item, entry.path)
                else:
                    child_item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        except PermissionError:
            error_item = QTreeWidgetItem("Permission denied")
            error_item.setDisabled(True)
            parent_item.addChild(error_item)
        except Exception as e:
            error_item = QTreeWidgetItem(f"Error: {str(e)}")
            error_item.setDisabled(True)
            parent_item.addChild(error_item)

    def on_filter_selected(self, dialog, selected_filter):
        """Handle filter selection change"""
        if selected_filter == "Directory":
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            dialog.setOption(QFileDialog.Option.ShowDirsOnly)
        else:
            dialog.setFileMode(QFileDialog.FileMode.AnyFile)
            dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
            
            # Update default extension based on selected filter
            extensions = {
                "Archives (*.zip)": ".zip",
                "TAR Archives (*.tar)": ".tar",
                "Gzipped TAR Archives (*.tar.gz)": ".tar.gz",
                "TGZ Archives (*.tgz)": ".tgz",
                "Bzip2 TAR Archives (*.tar.bz2)": ".tar.bz2",
                "7z Archives (*.7z)": ".7z",
            }
            
            # Only add RAR if available
            if self.rar_available:
                extensions["RAR Archives (*.rar)"] = ".rar"
            
            if selected_filter in extensions:
                current_name = os.path.splitext(dialog.selectedFiles()[0] if dialog.selectedFiles() else "archive")[0]
                dialog.selectFile(current_name + extensions[selected_filter])

    def show_archive_info(self):
        """Show supported archive formats and file type information"""
        dialog = QDialog(self)
        dialog.setWindowTitle('Archive Information')
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        # Create info text
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        
        # Format information
        formats_info = """
<h3>Supported Archive Formats</h3>
<ul>
<li><b>ZIP (.zip)</b>
    <br>- Standard ZIP archives
    <br>- Password protection (ZipCrypto and AES)
    <br>- Compression levels 0-9
</li>
<li><b>TAR (.tar)</b>
    <br>- Unix standard archive format
    <br>- Preserves Unix permissions
    <br>- No compression
</li>
<li><b>TAR.GZ (.tar.gz, .tgz)</b>
    <br>- TAR with GZIP compression
    <br>- Good compression ratio
    <br>- Fast compression/decompression
</li>
<li><b>TAR.BZ2 (.tar.bz2)</b>
    <br>- TAR with BZIP2 compression
    <br>- Better compression than GZIP
    <br>- Slower than GZIP
</li>
<li><b>RAR (.rar)</b>
    <br>- RAR archive format
    <br>- Strong compression
    <br>- Password protection
</li>
<li><b>7Z (.7z)</b>
    <br>- 7-Zip archive format
    <br>- Best compression ratio
    <br>- Strong encryption (AES-256)
    <br>- Solid compression option
</li>
</ul>

<h3>Features</h3>
<ul>
<li><b>Compression</b>
    <br>- Multiple compression levels (0-9)
    <br>- Format-specific optimizations
    <br>- Progress tracking
</li>
<li><b>Security</b>
    <br>- Password protection
    <br>- Encryption support
    <br>- Permission preservation
</li>
<li><b>File Handling</b>
    <br>- Skip patterns for unwanted files
    <br>- Collision resolution options
    <br>- Large file support
</li>
</ul>

<h3>System Requirements</h3>
<ul>
<li><b>Dependencies</b>
    <br>- Python 3.x
    <br>- PyQt6
    <br>- p7zip (7z) command line tool
</li>
<li><b>Optional</b>
    <br>- unrar (for RAR support)
    <br>- gzip, bzip2 (usually pre-installed)
</li>
</ul>
"""
        info_text.setHtml(formats_info)
        layout.addWidget(info_text)
        
        # OK button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)
        
        # Show dialog
        dialog.exec()

    def update_files_found(self, count):
        """Update files found label"""
        self.files_found_label.setText(f"Files found: {count}")

    def handle_error(self, message, is_permission_error=False):
        """Handle error messages"""
        self.error_label.setText(f"Error: {message}")
        self.copy_error_button.setVisible(True)
        if is_permission_error:
            self.error_label.setText(f"Error: {message}\nNote: This may be a permissions issue. Try running with elevated privileges.")

    def closeEvent(self, event: QEvent) -> None:
        """Handle window close event"""
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.terminate()
            self.current_thread.wait()
        super().closeEvent(event)

    def get_active_skip_patterns(self):
        """Get skip patterns if in archive mode"""
        active_patterns = []
        
        # Get patterns from checked categories
        for category, checkbox in self.skip_checkboxes.items():
            if checkbox.isChecked():
                active_patterns.extend(DEFAULT_SKIP_PATTERNS[category])
        
        # Get custom patterns
        if self.skip_patterns_edit.text().strip():
            active_patterns.extend(p.strip() for p in self.skip_patterns_edit.text().split(','))
        
        return active_patterns

    def select_multiple_directories(self):
        """Select multiple directories for archiving"""
        directories = QFileDialog.getExistingDirectory(self, "Select Directories", "", QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks)
        if directories:
            # Process the selected directories
            print("Selected directories:", directories)  # Replace with actual logic to handle directories

    def select_files_and_directories(self):
        """Select both files and directories for archiving"""
        # Select files
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*)")
        
        # Select directories
        directories = []
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", "", QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks)
        if directory:
            directories.append(directory)
        
        # Combine files and directories
        selected_items = files + directories

        if selected_items:
            # Process the selected files and directories
            print("Selected items:", selected_items)  # Replace with actual logic to handle the selection
        return selected_items

    def handle_interrupt(self):
        """Handle keyboard interrupt (Ctrl+C)"""
        # Stop any running threads
        if self.current_thread and self.current_thread.isRunning():
            print("\nStopping current operation...")
            self.current_thread.terminate()
            self.current_thread.wait()
            self.status_label.setText("Operation cancelled")
            self.progress_bar.setVisible(False)
            
        if self._browse_thread and self._browse_thread.isRunning():
            print("\nStopping browse operation...")
            self._browse_thread.terminate()
            self._browse_thread.wait()
            self.status_label.setText("Browse cancelled")
            self.browse_button.setEnabled(True)
            
        # Re-enable UI elements
        self.setEnabled(True)
    
    def toggle_theme(self):
        """Toggle between light and dark theme."""
        self.theme_manager.toggle_theme()
        self.update_theme_button()

    def update_theme_button(self):
        """Update theme button text based on current theme."""
        if hasattr(self, 'theme_button'):
            self.theme_button.setText("Dark Mode" if self.theme_manager.is_dark_theme() else "Light Mode")

    def show_file_preview(self, mode="create"):
        """Show file preview dialog"""
        try:
            if mode == "create":
                # Get files to preview for archiving
                files = QFileDialog.getOpenFileNames(
                    self,
                    "Select Files or Directories to Preview",
                    "",
                    "All Files (*)"
                )[0]
            elif mode == "git":
                # Get repository directory to preview
                repo_dir = QFileDialog.getExistingDirectory(
                    self, "Select Git Repository to Preview"
                )
                if repo_dir:
                    files = [repo_dir]
                else:
                    files = []
            else:
                return

            if files:
                dialog = FilePreviewDialog(self, files)
                dialog.exec()

        except Exception as e:
            self.handle_error(f"Error showing preview: {str(e)}")

    def _on_files_selected(self, selected_files):
        """Handle selected files for archive creation"""
        if selected_files:
            # Display selected items in tree view
            self._tree.clear()
            for file_path in selected_files:
                self.display_filesystem_item(file_path)

    def _on_files_selected_extract(self, selected_files):
        """Handle selected files for archive extraction"""
        if selected_files:
            # Get output directory
            output_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Output Directory"
            )
            if output_dir:
                try:
                    self.extract_archive(
                        self.current_archive_path,
                        output_dir=output_dir,
                        password=self.password,
                        skip_patterns=self.get_active_skip_patterns(),
                        file_list=selected_files
                    )
                except Exception as e:
                    self.handle_error(f"Error during extraction: {str(e)}")

    def _enable_controls(self, enabled=True):
        """Enable or disable controls during operations"""
        # Core buttons that should always exist
        self.browse_button.setEnabled(enabled)
        
        # Optional buttons - check before enabling
        if hasattr(self, 'queue_extract_button'):
            self.queue_extract_button.setEnabled(enabled)
        if hasattr(self, 'queue_compress_button'):
            self.queue_compress_button.setEnabled(enabled)
        if hasattr(self, 'compression_slider'):
            self.compression_slider.setEnabled(enabled)
        if hasattr(self, 'extract_all_button'):
            self.extract_all_button.setEnabled(enabled)
        if hasattr(self, 'extract_selected_button'):
            self.extract_selected_button.setEnabled(enabled)
        if hasattr(self, 'tree_view'):
            self.tree_view.setEnabled(enabled)

    def show_release_manager(self):
        """Show the release manager tab."""
        # Switch to Dev Tools mode if not already
        if self.mode_combo.currentText() != 'Dev Tools':
            self.mode_combo.setCurrentText('Dev Tools')
            
        # Show Git widget if hidden
        if not self.git_widget.isVisible():
            self.git_widget.setVisible(True)
            
        # Find the release manager tab and select it
        tab_widget = self.git_widget.findChild(QTabWidget)
        if tab_widget:
            for i in range(tab_widget.count()):
                if tab_widget.tabText(i) == "Release Manager":
                    tab_widget.setCurrentIndex(i)
                    break

    def copy_error_to_clipboard(self):
        """Copy error text to clipboard."""
        if self.error_label.text():
            clipboard = QApplication.clipboard()
            clipboard.setText(self.error_label.text())
            QMessageBox.information(self, "Error Copied", "Error details have been copied to clipboard")

    def on_mode_changed(self, mode: str):
        """Handle mode selection changes."""
        if mode == "Dev Tools":
            self.show_git_ui()
            self.archive_group.hide()
            self.recent_group.hide()
            self.variable_calendar.hide()
            self.supabase_widget.show()
        elif mode == "Variable Calendar":
            self.git_widget.hide()
            self.archive_group.hide()
            self.recent_group.hide()
            self.variable_calendar.show()
            self.supabase_widget.hide()
        else:  # Archive mode
            self.hide_git_ui()
            self.archive_group.show()
            self.recent_group.show()
            self.variable_calendar.hide()
            self.supabase_widget.hide()
            
    def show_git_ui(self):
        """Show Git-related UI elements"""
        self.git_widget.setVisible(True)
        # Set a reasonable maximum height (e.g., 60% of screen height)
        screen = QApplication.primaryScreen().geometry()
        max_height = int(screen.height() * 0.6)  # Reduced from 80% to 60%
        self.git_widget.setMaximumHeight(max_height)
        # Set a reasonable default height
        default_height = int(screen.height() * 0.4)  # Start at 40% screen height
        self.resize(self.width(), default_height)
        # Adjust window size to fit content within constraints
        self.adjustSize()
        
    def hide_git_ui(self):
        """Hide Git-related UI elements"""
        self.git_widget.setVisible(False)
        
    def on_repository_changed(self, repo_path: str):
        """Handle repository path change."""
        # Update UI or perform necessary actions when repository changes
        pass
        
    def on_sequester_path_changed(self, sequester_path: str):
        """Handle sequester path change."""
        # Update UI or perform necessary actions when sequester path changes
        pass
        
    def on_artifacts_path_changed(self, artifacts_path: str):
        """Handle artifacts path change."""
        # Update UI or perform necessary actions when artifacts path changes
        pass

    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double click on tree item."""
        try:
            path = item.data(0, Qt.ItemDataRole.UserRole)
            if not path:
                return
                
            if os.path.isfile(path):
                # Show file preview dialog
                dialog = FilePreviewDialog(self, [path])
                dialog.exec()
            elif os.path.isdir(path):
                # Toggle expand/collapse
                item.setExpanded(not item.isExpanded())
        except Exception as e:
            self.handle_error(f"Error handling double click: {str(e)}")

    def _handle_files_to_open(self, files):
        """Handle files passed to open from command line or file manager"""
        if not files:
            return

        # If multiple files, queue them for extraction
        if len(files) > 1:
            for file_path in files:
                if os.path.isfile(file_path):
                    extraction_info = {
                        'archive_name': file_path,
                        'output_dir': os.path.dirname(file_path),
                        'password': None,
                        'collision_strategy': self.collision_combo.currentText(),
                        'preserve_permissions': self.preserve_permissions.isChecked(),
                        'skip_patterns': self.get_active_skip_patterns()
                    }
                    self.extraction_queue.append(extraction_info)
            
            # Enable start extract button
            self.start_extract_button.setEnabled(True)
            self.update_status(f"Queued {len(files)} archives for extraction")
        
        # Open the first file immediately
        first_file = files[0]
        if os.path.isfile(first_file):
            self._open_archive(first_file)

    def add_recent_archive(self, archive_path):
        """Add an archive to recent archives list"""
        if not archive_path:
            return
            
        # Convert to absolute path
        archive_path = os.path.abspath(archive_path)
        
        # Remove if already exists (to move to top)
        if archive_path in self.recent_archives:
            self.recent_archives.remove(archive_path)
            
        # Add to start of list
        self.recent_archives.insert(0, archive_path)
        
        # Keep only last 10 items
        self.recent_archives = self.recent_archives[:10]
        
        # Update UI
        self.update_recent_archives_ui()
        
        # Save to file
        self.save_recent_archives()

    def update_recent_archives_ui(self):
        """Update the recent archives list in UI"""
        self.recent_list.clear()
        for archive in self.recent_archives:
            if os.path.exists(archive):  # Only show existing files
                self.recent_list.addItem(os.path.basename(archive))

    def _on_recent_archive_clicked(self, item):
        """Handle click on recent archive"""
        archive_path = self.recent_archives[self.recent_list.row(item)]
        if os.path.exists(archive_path):
            self._open_archive(archive_path)
        else:
            # Remove non-existent file from list
            self.recent_archives.remove(archive_path)
            self.update_recent_archives_ui()
            self.save_recent_archives()
            self.show_error(f"Archive no longer exists: {archive_path}")

    def load_recent_archives(self):
        """Load recent archives from file"""
        try:
            os.makedirs(os.path.dirname(self.recent_archives_file), exist_ok=True)
            if os.path.exists(self.recent_archives_file):
                with open(self.recent_archives_file, 'r') as f:
                    self.recent_archives = json.load(f)
        except Exception as e:
            print(f"Error loading recent archives: {e}")
            self.recent_archives = []

    def save_recent_archives(self):
        """Save recent archives to file"""
        try:
            with open(self.recent_archives_file, 'w') as f:
                json.dump(self.recent_archives, f)
        except Exception as e:
            print(f"Error saving recent archives: {e}")

    def clear_recent_archives(self):
        """Clear recent archives list"""
        self.recent_archives = []
        self.update_recent_archives_ui()
        self.save_recent_archives()

def main():
    app = QApplication(sys.argv)
    
    # Get files to open from command line arguments
    files_to_open = sys.argv[1:] if len(sys.argv) > 1 else None
    
    # Create widget with files to open
    widget = MainWidget(files_to_open=files_to_open)
    widget.show()
    
    signal.signal(signal.SIGINT, lambda sig, frame: widget.handle_interrupt())
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
