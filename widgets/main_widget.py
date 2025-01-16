from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QLabel, QProgressBar, QTextEdit, QComboBox,
                            QGroupBox, QCheckBox, QDialog, QGridLayout, QFrame,
                            QInputDialog, QLineEdit, QMessageBox, QFileDialog, QFormLayout, QSlider,
                            QTreeWidget, QTreeWidgetItem, QHeaderView, QApplication, QStyle, QDialogButtonBox,
                            QProgressDialog, QTreeView, QTabWidget,  QMenu, QListWidget, QScrollArea)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QDir, QUrl, QEvent, QSettings
from PyQt6.QtGui import QAction
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import os
import subprocess
import tempfile
import shutil
import signal
import sys
import psutil
from ..threads.archive_thread import ArchiveThread
from ..threads.extraction_thread import ExtractionThread
from ..threads.browse_thread import BrowseThread
from ..threads.directory_update_thread import DirectoryUpdateThread
from ..utils.project_constants import DEFAULT_SKIP_PATTERNS, ARCHIVE_EXTENSIONS
from ..utils.archive_utils import get_archive_type, is_rar_available
from ..sevenz import SevenZipHandler
from ..utils.git_utils import backup_git_configs, restore_git_configs, GitConfigHandler
from ..utils.theme_manager import ThemeManager
from ..utils.release_manager import ReleaseManager
from .file_preview_dialog import FilePreviewDialog
from .collision_dialog import CollisionDialog
from datetime import datetime
from ..utils.git_config_manager import GitConfigManager

class MainWidget(QWidget):
    def __init__(self, parent=None):
        """Initialize the main widget"""
        super().__init__(parent)
        
        # Initialize instance variables
        self.archive_path = None  # Path to current archive
        self.current_archive_path = None  # Path to current archive for extraction
        self.current_contents = None  # Current archive contents
        self.current_thread = None  # Current operation thread
        self._browse_thread = None  # Browse thread for archives/directories
        self.password = None  # Current archive password
        self.skip_checkboxes = {}  # Skip pattern checkboxes
        self.extraction_queue = []  # Queue for pending extractions
        self.release_manager = None  # Release manager instance
        self.setWindowTitle('Varchiver')
        
        # Check RAR availability
        self.rar_available = is_rar_available()
        
        # Initialize Git UI elements
        self.git_repo_path = QLineEdit()
        self.git_output_path = QLineEdit()
        self.git_status_label = QLabel("Select repository to begin")
        self.git_config_status = QLabel("Select a Git repository to begin")
        self.git_error_text = QTextEdit()
        self.git_progress_bar = QProgressBar()
        
        # Main layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        
        # Add donation widget
        donation_widget = QWidget()
        donation_layout = QHBoxLayout()
        donation_widget.setLayout(donation_layout)
        
        sol_label = QLabel("Free the source! $Instancer or SOL:")
        sol_label.setStyleSheet("font-weight: bold;")
        donation_layout.addWidget(sol_label)
        sol_address = "4zn9C2pgnxQwHvmoKCnyoV1YLtYFX5qxSaTxE2T86JEq"
        sol_input = QLineEdit(sol_address)
        sol_input.setReadOnly(True)
        sol_input.setMinimumWidth(400)
        sol_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        donation_layout.addWidget(sol_input)
        
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(lambda: self._copy_to_clipboard(sol_address))
        donation_layout.addWidget(copy_button)
        
        donation_layout.addStretch()
        self.main_layout.addWidget(donation_widget)
        self.main_layout.addWidget(QLabel("Src repo: https://github.com/instancer-kirik/Varchiver"))
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(separator)
        
        # Initialize theme manager
        self.theme_manager = ThemeManager()
        self.theme_manager.apply_theme()
        
        # Mode selector group
        self.mode_group = QGroupBox("Operation Mode")
        mode_layout = QVBoxLayout()
        self.mode_group.setLayout(mode_layout)
        
        self.main_layout.addWidget(self.git_config_status)
        # Add theme toggle and release manager next to mode selector
        mode_header = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            'Archive',           # Normal archiving with skip patterns
            'Dev Tools'         # Development tools and utilities
        ])
        self.mode_combo.setToolTip(
            'Operation mode:\n'
            'Archive: Normal archiving with skip patterns\n'
            'Dev Tools: Development utilities and configuration management'
        )
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_header.addWidget(self.mode_combo)
        
        # Theme toggle
        self.theme_button = QPushButton()
        self.theme_button.clicked.connect(self.toggle_theme)
        mode_header.addWidget(self.theme_button)
        
        # Release Manager button
        self.release_button = QPushButton("Release Manager")
        self.release_button.clicked.connect(self.show_release_manager)
        mode_header.addWidget(self.release_button)
        
        mode_layout.addLayout(mode_header)
        self.main_layout.addWidget(self.mode_group)

        # Current archive label
        self.current_archive_label = QLabel('')
        self.main_layout.addWidget(self.current_archive_label)
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
        self.main_layout.addWidget(self.status_label)

        # Progress bar for loading feedback
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        self.main_layout.addWidget(self.progress_bar)

        # Files found label
        self.files_found_label = QLabel('')
        self.main_layout.addWidget(self.files_found_label)
        
        # Error box with consistent styling
        error_box = QGroupBox()
        error_layout = QHBoxLayout()
        error_box.setLayout(error_layout)
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
        
        self.main_layout.addWidget(error_box)
        
        self.setup_archive_ui(self.main_layout)

    def setup_archive_ui(self, parent_layout):
        """Set up the archive-related UI elements"""
        # Create archive group box
        self.archive_group = QGroupBox("Archive Operations")
        archive_layout = QVBoxLayout()
        self.archive_group.setLayout(archive_layout)
        
        # Create toolbar
        toolbar = QHBoxLayout()
        
        # Browse button
        self.browse_button = QPushButton("Browse")
        self.browse_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogStart))
        self.browse_button.clicked.connect(self.browse_archive_dialog)
        toolbar.addWidget(self.browse_button)
        
        # Preview button (commented out for now)
        # self.preview_button = QPushButton("Preview")
        # self.preview_button.setEnabled(False)
        # self.preview_button.clicked.connect(self.show_file_preview)
        # toolbar.addWidget(self.preview_button)
        
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
        
        # Create collapsible settings section
        settings_group = QGroupBox("Archive Settings")
        settings_group.setCheckable(True)
        settings_group.setChecked(True)  # Start expanded
        settings_layout = QVBoxLayout()
        settings_group.setLayout(settings_layout)
        
        # Create skip patterns section
        skip_group = QGroupBox("Skip Patterns")
        skip_layout = QVBoxLayout()
        skip_group.setLayout(skip_layout)
        
        # Add description
        skip_desc = QLabel("Common patterns to exclude:")
        skip_desc.setWordWrap(True)
        skip_layout.addWidget(skip_desc)
        
        # Create horizontal layout for skip patterns
        skip_patterns_layout = QHBoxLayout()
        skip_layout.addLayout(skip_patterns_layout)
        
        # Create a flow layout container
        flow_widget = QWidget()
        flow_layout = QHBoxLayout()
        flow_layout.setSpacing(4)
        flow_widget.setLayout(flow_layout)
        
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
        
        # Add custom patterns input
        custom_layout = QHBoxLayout()
        custom_label = QLabel("Custom:")
        custom_layout.addWidget(custom_label)
        
        self.skip_patterns_edit = QLineEdit()
        self.skip_patterns_edit.setPlaceholderText("Additional patterns to skip (comma-separated)")
        self.skip_patterns_edit.setToolTip("Enter additional patterns to skip, separated by commas")
        custom_layout.addWidget(self.skip_patterns_edit)
        
        skip_layout.addLayout(custom_layout)
        
        # Add to main layout
        archive_layout.addWidget(skip_group)
        
        # Options group
        options_group = QGroupBox("Options")
        options_layout = QFormLayout()
        options_group.setLayout(options_layout)

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
        collision_layout = QVBoxLayout()
        collision_group.setLayout(collision_layout)
        
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
        
        # Create a grid for collision strategy description

       
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
        
        # Add options group to settings
        settings_layout.addWidget(options_group)
        
        archive_layout.addWidget(settings_group)
        
        # Create status section
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        status_group.setLayout(status_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel()
        status_layout.addWidget(self.status_label)
        
        archive_layout.addWidget(status_group)
        
        # Tree view for file display
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Name", "Size", "Modified", "Ratio"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.setAlternatingRowColors(True)
        self._tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        archive_layout.addWidget(self._tree)
        
        # Add archive group to parent layout
        parent_layout.addWidget(self.archive_group)

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

    def _open_archive(self, filename):
        """Open an archive file or directory"""
        try:
            self.current_archive_path = filename
            self.status_label.setText(f"Opening: {os.path.basename(filename)}")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.error_label.setVisible(False)

            # Create and start browse thread
            self._browse_thread = BrowseThread(filename, self.password)
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
        dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Choose")
        dialog.setLabelText(QFileDialog.DialogLabel.Reject, "Cancel")
        
        # Add a button to select current directory
        current_dir_button = QPushButton("Select Current Directory", dialog)
        current_dir_button.clicked.connect(lambda: self._select_current_dir(dialog))
        
        # Add the button to the dialog's layout
        layout = dialog.layout()
        if layout:
            # Try to find a good spot for the button
            if isinstance(layout, QGridLayout):
                # Add to the last row
                row = layout.rowCount()
                layout.addWidget(current_dir_button, row, 0, 1, -1)
            else:
                # If not a grid layout, just add to the end
                layout.addWidget(current_dir_button)
        
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected_files = dialog.selectedFiles()
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
            
            if save_dialog.exec() != QFileDialog.DialogCode.Accepted:
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

    def update_theme_button(self):
        """Update theme button icon based on current theme."""
        if self.theme_manager.dark_mode:
            # Sun icon for light mode option
            self.theme_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
        else:
            # Moon icon for dark mode option
            self.theme_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarShadeButton))
    
    def toggle_theme(self):
        """Toggle between light and dark themes."""
        self.theme_manager.toggle_theme()
        self.update_theme_button()

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

    def review_git_configs(self):
        """Show dialog to review git configurations"""
        dialog = QDialog(self)
        dialog.setWindowTitle("GitConfigManager")
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(500)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Config Tab
        config_tab = QWidget()
        config_layout = QVBoxLayout()
        config_tab.setLayout(config_layout)
        
        config_text = QTextEdit()
        config_text.setReadOnly(True)
        config_layout.addWidget(config_text)
        
        # Gitignore Tab
        gitignore_tab = QWidget()
        gitignore_layout = QVBoxLayout()
        gitignore_tab.setLayout(gitignore_layout)
        
        gitignore_text = QTextEdit()
        gitignore_layout.addWidget(gitignore_text)
        
        # Add save button for gitignore
        save_gitignore_btn = QPushButton("Save .gitignore")
        gitignore_layout.addWidget(save_gitignore_btn)
        
        # Add tabs
        tabs.addTab(config_tab, "GitConfig")
        tabs.addTab(gitignore_tab, "Gitignore")
        layout.addWidget(tabs)
        
        # Get git configuration data
        if self.git_repo_path.text():
            try:
                handler = GitConfigHandler(self.git_repo_path.text())
                if handler.is_git_repo():
                    config = handler.get_git_config()
                    config_str = []
                    
                    # Add local config
                    if config.get('local_config'):
                        config_str.append("LocalConfig:")
                        config_str.extend(f"  {k} = {v}" for k, v in config['local_config'].items())
                        config_str.append("")
                    
                    # Add remotes
                    if config.get('remotes'):
                        config_str.append("Remotes:")
                        config_str.extend(f"  {name}: {url}" for name, url in config['remotes'].items())
                        config_str.append("")
                    
                    # Add branches
                    if config.get('branches'):
                        config_str.append("Branches:")
                        config_str.extend(
                            f"  {branch} {f'-> {tracking}' if tracking else ''}"
                            for branch, tracking in config['branches'].items()
                        )
                        config_str.append("")
                    
                    # Add submodules more compactly
                    if config.get('submodules'):
                        config_str.append("Submodules:")
                        for path, submodule in config['submodules'].items():
                            parts = [f"  {path}"]
                            if 'url' in submodule:
                                parts.append(f"[{submodule['url']}]")
                            if 'branch' in submodule:
                                parts.append(f"({submodule['branch']})")
                            config_str.append(" ".join(parts))
                        config_str.append("")
                    
                    # Add modules more compactly
                    if config.get('modules'):
                        config_str.append("GitModules:")
                        for path, module_config in config['modules'].items():
                            config_str.append(f"  {path}")
                            if module_config.get('remotes'):
                                remotes = ", ".join(f"{k}: {v}" for k, v in module_config['remotes'].items())
                                config_str.append(f"    Remotes: {remotes}")
                            if module_config.get('branches'):
                                branches = ", ".join(
                                    f"{b}{f' -> {t}' if t else ''}"
                                    for b, t in module_config['branches'].items()
                                )
                                config_str.append(f"    Branches: {branches}")
                        config_str.append("")
                    
                    config_text.setText("\n".join(config_str))
                    
                    # Load gitignore content
                    gitignore_path = os.path.join(self.git_repo_path.text(), '.gitignore')
                    if os.path.exists(gitignore_path):
                        with open(gitignore_path, 'r') as f:
                            gitignore_text.setText(f.read())
                    
                    # Connect save button
                    def save_gitignore():
                        try:
                            with open(gitignore_path, 'w') as f:
                                f.write(gitignore_text.toPlainText())
                            QMessageBox.information(dialog, "Success", ".gitignore saved successfully!")
                        except Exception as e:
                            QMessageBox.warning(dialog, "Error", f"Failed to save .gitignore: {str(e)}")
                    
                    save_gitignore_btn.clicked.connect(save_gitignore)
                    
                else:
                    config_text.setText("Selected directory is not a Git repository.")
                    gitignore_text.setEnabled(False)
                    save_gitignore_btn.setEnabled(False)
            except Exception as e:
                config_text.setText(f"Error reading Git configuration: {str(e)}")
                gitignore_text.setEnabled(False)
                save_gitignore_btn.setEnabled(False)
        else:
            config_text.setText("Please select a Git repository first.")
            gitignore_text.setEnabled(False)
            save_gitignore_btn.setEnabled(False)
        
        # Add buttons at bottom
        button_box = QDialogButtonBox()
        ok_button = button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        # Show dialog
        dialog.exec()

    def copy_git_config(self, source_dir):
        """Copy git configuration to a target repository"""
        if not os.path.exists(os.path.join(source_dir, '.git')):
            raise ValueError(f"Not a git repository: {source_dir}")
            
        # Get target repository
        target_dir = QFileDialog.getExistingDirectory(
            self, "Select Target Repository Directory"
        )
        
        if not target_dir:
            return
            
        if not os.path.exists(os.path.join(target_dir, '.git')):
            raise ValueError(f"Not a git repository: {target_dir}")
            
        # Copy configuration
        source_config = os.path.join(source_dir, '.git', 'config')
        target_config = os.path.join(target_dir, '.git', 'config')
        
        if os.path.exists(source_config):
            shutil.copy2(source_config, target_config)
            
        self.status_label.setText(f"Copied Git config to: {target_dir}")

    def on_mode_changed(self, mode):
        """Handle mode change between archive and dev tools modes"""
        if mode == 'Dev Tools':
            # Hide archive UI
            self.hide_archive_ui()
            
            # Show Git-related UI elements
            git_group = QGroupBox("GitTools")
            git_layout = QVBoxLayout()
            git_group.setLayout(git_layout)

            # Repository selection at the top level
            repo_section = QHBoxLayout()
            repo_label = QLabel("Git Repository:")
            self.git_repo_path = QLineEdit()
            
            # Use release manager settings if available
            settings = QSettings("Varchiver", "ReleaseManager")
            if settings.value("project_path"):
                self.git_repo_path.setText(settings.value("project_path"))
            
            repo_section.addWidget(repo_label)
            repo_section.addWidget(self.git_repo_path)
            select_repo_button = QPushButton("Select Repository")
            select_repo_button.clicked.connect(self.select_git_repo)
            repo_section.addWidget(select_repo_button)
            git_layout.addLayout(repo_section)

            # Git URL and branch controls
            git_controls = QHBoxLayout()
            
            # Git URL
            url_label = QLabel("Remote URL:")
            self.git_url = QLineEdit()
            self.git_url.setPlaceholderText("Git remote URL (e.g., https://github.com/user/repo.git)")
            git_controls.addWidget(url_label)
            git_controls.addWidget(self.git_url)
            
            # Branch
            branch_label = QLabel("Branch:")
            self.git_branch = QLineEdit()
            self.git_branch.setPlaceholderText("main")
            git_controls.addWidget(branch_label)
            git_controls.addWidget(self.git_branch)
            
            # Add remote button
            add_remote = QPushButton("Add Remote")
            add_remote.clicked.connect(self.add_git_remote)
            git_controls.addWidget(add_remote)
            
            git_layout.addLayout(git_controls)

            # Create tabs for different Git tools
            git_tabs = QTabWidget()
            self.git_tabs = git_tabs  # Store reference for later use

            # GitConfigManager tab
            config_tab = QWidget()
            config_layout = QVBoxLayout()
            config_tab.setLayout(config_layout)

            # Git config manager container
            self.git_config_container = QWidget()
            config_container_layout = QVBoxLayout()
            self.git_config_container.setLayout(config_container_layout)
            
            # Initialize GitConfigManager if repo is selected
            if self.git_repo_path.text():
                self.git_config_manager = GitConfigManager(Path(self.git_repo_path.text()))
                config_container_layout.addWidget(self.git_config_manager)
            
            config_layout.addWidget(self.git_config_container)

            # Add gitignore link
            gitignore_link = QPushButton("Open .gitignore")
            gitignore_link.clicked.connect(self.open_gitignore)
            config_layout.addWidget(gitignore_link)

            git_tabs.addTab(config_tab, "GitConfigManager")

            # GitSequester tab
            sequester_tab = QWidget()
            sequester_layout = QVBoxLayout()
            sequester_tab.setLayout(sequester_layout)

            # Git config backup/restore section
            backup_group = QGroupBox("Git Backup/Restore")
            backup_layout = QVBoxLayout()
            backup_group.setLayout(backup_layout)

            # Storage location
            storage_layout = QHBoxLayout()
            storage_label = QLabel("Storage Location:")
            self.git_storage_path = QLineEdit(settings.value("git_storage_path") or os.path.join(os.path.expanduser("~"), ".varchiver", "git_archives"))
            self.git_storage_path.setPlaceholderText("Select storage location for Git archives")
            storage_layout.addWidget(storage_label)
            storage_layout.addWidget(self.git_storage_path)
            
            storage_browse = QPushButton("Browse")
            storage_browse.clicked.connect(self.select_git_storage)
            storage_layout.addWidget(storage_browse)
            backup_layout.addLayout(storage_layout)

            # Operation buttons
            button_layout = QHBoxLayout()
            self.archive_git_button = QPushButton("Archive Git State")
            self.archive_git_button.clicked.connect(self.archive_git_state)
            button_layout.addWidget(self.archive_git_button)

            self.restore_git_button = QPushButton("Restore Git State")
            self.restore_git_button.clicked.connect(self.restore_git_state)
            button_layout.addWidget(self.restore_git_button)
            backup_layout.addLayout(button_layout)

            # Status and progress
            self.git_status_label = QLabel("Select repository and storage location to begin")
            backup_layout.addWidget(self.git_status_label)

            self.git_progress_bar = QProgressBar()
            self.git_progress_bar.hide()
            backup_layout.addWidget(self.git_progress_bar)

            self.git_error_text = QTextEdit()
            self.git_error_text.setReadOnly(True)
            self.git_error_text.setMaximumHeight(60)
            self.git_error_text.hide()
            backup_layout.addWidget(self.git_error_text)

            sequester_layout.addWidget(backup_group)

            # Untracked files section
            untracked_group = QGroupBox("Untracked Files")
            untracked_layout = QVBoxLayout()
            untracked_group.setLayout(untracked_layout)

            refresh_button = QPushButton("Refresh Untracked Files")
            refresh_button.clicked.connect(self.refresh_untracked_files)
            untracked_layout.addWidget(refresh_button)

            self.untracked_list = QListWidget()
            self.untracked_list.setMinimumHeight(200)
            untracked_layout.addWidget(self.untracked_list)

            sequester_layout.addWidget(untracked_group)

            git_tabs.addTab(sequester_tab, "GitSequester")

            # Release Manager tab
            release_tab = QWidget()
            release_layout = QVBoxLayout()
            release_tab.setLayout(release_layout)

            # Add release manager widget
            self.release_manager = ReleaseManager()
            release_layout.addWidget(self.release_manager)

            git_tabs.addTab(release_tab, "ReleaseManager")

            git_layout.addWidget(git_tabs)
            self.main_layout.addWidget(git_group)
            
            # Update Git info if repo is selected
            if self.git_repo_path.text():
                self.update_git_info()
        else:
            # Show archive UI
            self.show_archive_ui()
            
    def add_git_remote(self):
        """Add or update Git remote"""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Error", "Please select a Git repository first")
            return
            
        url = self.git_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a remote URL")
            return
            
        try:
            # Check if remote exists
            result = subprocess.run(
                ["git", "remote"],
                cwd=self.git_repo_path.text(),
                capture_output=True,
                text=True
            )
            
            if "origin" in result.stdout.split():
                # Update existing remote
                subprocess.run(
                    ["git", "remote", "set-url", "origin", url],
                    cwd=self.git_repo_path.text(),
                    check=True
                )
                QMessageBox.information(self, "Success", "Updated remote 'origin'")
            else:
                # Add new remote
                subprocess.run(
                    ["git", "remote", "add", "origin", url],
                    cwd=self.git_repo_path.text(),
                    check=True
                )
                QMessageBox.information(self, "Success", "Added remote 'origin'")
                
            # Set up tracking if branch specified
            if self.git_branch.text().strip():
                subprocess.run(
                    ["git", "branch", "--set-upstream-to=origin/" + self.git_branch.text().strip()],
                    cwd=self.git_repo_path.text(),
                    check=True
                )
                
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to update Git remote: {e.stderr}")

    def update_git_info(self):
        """Update Git remote URL and branch info"""
        try:
            # Get remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.git_repo_path.text(),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.git_url.setText(result.stdout.strip())
                
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.git_repo_path.text(),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.git_branch.setText(result.stdout.strip())
                
        except subprocess.CalledProcessError:
            pass  # Ignore errors, might be a new repo

    def select_git_storage(self):
        """Select storage directory for git archives"""
        start_dir = self.git_storage_path.text() or os.path.join(os.path.expanduser("~"), ".varchiver", "git_archives")
            
        storage_dir = QFileDialog.getExistingDirectory(
            self, "Select Git Archive Storage Location",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if storage_dir:
            self.git_storage_path.setText(storage_dir)
            self._update_git_buttons()

    def archive_git_state(self):
        """Archive the current Git state"""
        self.backup_git_files()  # Reuse existing functionality with new name

    def restore_git_state(self):
        """Restore a previously archived Git state"""
        self.restore_git_files()  # Reuse existing functionality with new name

    def _update_git_buttons(self):
        """Update git operation buttons based on selected paths"""
        has_repo = bool(self.git_repo_path.text())
        has_storage = bool(self.git_storage_path.text())
        
        self.archive_git_button.setEnabled(has_repo)  # Only needs repo path
        self.restore_git_button.setEnabled(has_storage)  # Only needs storage dir for browsing archives
        
        if has_repo:
            self.git_status_label.setText("Ready for operations")
        else:
            self.git_status_label.setText("Select repository to begin")

    def select_git_repo(self):
        """Select repository directory"""
        # Start from current repo path or release manager path
        settings = QSettings("Varchiver", "ReleaseManager")
        start_dir = self.git_repo_path.text() or settings.value("project_path") or QDir.homePath()
        
        repo_dir = QFileDialog.getExistingDirectory(
            self, "Select Repository Directory",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if repo_dir:
            self.git_repo_path.setText(repo_dir)
            
            # Update Git config tab
            if hasattr(self, 'git_repo_path_edit'):
                self.git_repo_path_edit.setText(repo_dir)
                self.init_git_config_manager(Path(repo_dir))
            
            # Set default output location if not already set
            if not self.git_output_path.text():
                default_output = os.path.join(os.path.dirname(repo_dir), "git_backups")
                self.git_output_path.setText(default_output)
                # Create directory if it doesn't exist
                os.makedirs(default_output, exist_ok=True)
            
            self._update_git_buttons()

    def backup_git_files(self):
        """Backup and remove git files from repository"""
        if not self.git_output_path.text():
            QMessageBox.warning(
                self,
                "Warning",
                "Please select an output directory first"
            )
            return
            
        if not self.git_repo_path.text():
            QMessageBox.warning(
                self,
                "Warning",
                "Please select a repository directory first"
            )
            return
            
        self.git_error_text.setVisible(False)
        self.git_status_label.setText("Processing repository...")
            
        # Generate backup filename
        repo_name = os.path.basename(self.git_repo_path.text())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(
            self.git_output_path.text(),
            f"git_backup_{repo_name}_{timestamp}.json"
        )
            
        try:
            self.git_progress_bar.setVisible(True)
            self.git_progress_bar.setRange(0, 0)  # Indeterminate progress
            
            handler = GitConfigHandler(self.git_repo_path.text())
            if handler.remove_git_files(backup_path=backup_file):
                self.git_status_label.setText(
                    f"Git files successfully backed up to:\n{backup_file}"
                )
                QMessageBox.information(
                    self,
                    "Success",
                    f"Git files backed up to {backup_file} and removed from repository"
                )
            else:
                self.git_status_label.setText("Failed to backup and remove git files")
                self.git_error_text.setVisible(True)
                self.git_error_text.setText("Operation failed - check repository permissions")
        except Exception as e:
            self.git_status_label.setText("Error during backup")
            self.git_error_text.setVisible(True)
            self.git_error_text.setText(str(e))
        finally:
            self.git_progress_bar.hide()

    def restore_git_files(self):
        """Restore git files from backup"""
        self.git_error_text.setVisible(False)
        self.git_status_label.setText("Checking for backup files...")

        # First check default backup location (output path)
        default_backup = None
        if self.git_output_path.text():
            # Look for most recent backup in output directory
            output_dir = self.git_output_path.text()
            backups = [f for f in os.listdir(output_dir) if f.startswith('git_backup_') and f.endswith('.json')]
            if backups:
                # Sort by timestamp in filename (git_backup_reponame_YYYYMMDD_HHMMSS.json)
                backups.sort(reverse=True)  # Most recent first
                default_backup = os.path.join(output_dir, backups[0])
    
        # If no default backup found or not using default location, ask user
        if not default_backup:
            self.git_status_label.setText("Selecting backup file...")
            backup_file, _ = QFileDialog.getOpenFileName(
                self, "Select Git Backup File",
                QDir.homePath(),
                "JSON Files (*.json)"
            )
            if not backup_file:
                self.git_status_label.setText("Operation cancelled")
                return
        else:
            backup_file = default_backup
            self.git_status_label.setText(f"Using latest backup: {os.path.basename(backup_file)}")
    
        # Use currently selected repo if available
        repo_dir = self.git_repo_path.text()
        if not repo_dir:
            # Only ask for repo dir if none selected
            repo_dir = QFileDialog.getExistingDirectory(
                self, "Select Target Repository Directory",
                QDir.homePath(),
                QFileDialog.Option.ShowDirsOnly
            )
            if not repo_dir:
                self.git_status_label.setText("Operation cancelled")
                return
            self.git_repo_path.setText(repo_dir)
        
        try:
            self.git_status_label.setText("Restoring git files...")
            self.git_progress_bar.setVisible(True)
            self.git_progress_bar.setRange(0, 0)  # Indeterminate progress
            
            handler = GitConfigHandler(repo_dir)
            if handler.restore_git_files(backup_file):
                self.git_status_label.setText(
                    f"Git files successfully restored to:\n{repo_dir}"
                )
                QMessageBox.information(
                    self,
                    "Success",
                    f"Git files restored to {repo_dir}"
                )
            else:
                self.git_status_label.setText("Failed to restore git files")
                self.git_error_text.setVisible(True)
                self.git_error_text.setText("Operation failed - check directory permissions")
        except Exception as e:
            self.git_status_label.setText("Error during restoration")
            self.git_error_text.setVisible(True)
            self.git_error_text.setText(str(e))
        finally:
            self.git_progress_bar.hide()

    def _prepare_archive(self, source_path, archive_path):
        """Prepare archive based on mode"""
        if self.mode_combo.currentText() == 'Dev Tools':
            self.review_git_configs()
            return
            
        if self.git_config_check.isChecked():
            temp_dir = tempfile.mkdtemp(prefix='varchiver_git_')
            try:
                # Backup Git configs
                config_paths = backup_git_configs(source_path, temp_dir)
                if config_paths:
                    self.status_label.setText(f"Found {len(config_paths)} Git repositories")
                    
                    # Add Git configs to archive
                    for config_path in config_paths:
                        rel_path = os.path.relpath(config_path, temp_dir)
                        target_path = os.path.join(archive_path, '.git_configs', rel_path)
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        shutil.copy2(config_path, target_path)
            finally:
                shutil.rmtree(temp_dir)

    def _restore_git_configs(self, extract_path):
        """Restore Git configurations after extraction if available."""
        git_configs_dir = os.path.join(extract_path, '.git_configs')
        if os.path.exists(git_configs_dir):
            results = restore_git_configs(git_configs_dir, extract_path)
            success_count = sum(1 for _, success in results if success)
            if results:
                self.status_label.setText(
                    f"Restored {success_count}/{len(results)} Git configurations"
                )
            # Clean up Git config files
            shutil.rmtree(git_configs_dir)

    def _on_archive_complete(self):
        """Handle archive operation completion."""
        self.status_label.setText("Archive operation completed")
        self.progress_bar.hide()
        self._enable_controls(True)
        
        if hasattr(self, '_source_path') and hasattr(self, '_archive_path'):
            self._prepare_archive(self._source_path, self._archive_path)

    def _on_extract_complete(self):
        """Handle extraction operation completion."""
        if self.git_config_check.isChecked():
            self._restore_git_configs(self._extract_path)
        
        self.status_label.setText("Extraction completed")
        self.progress_bar.hide()
        self._enable_controls(True)

    def _get_mounted_devices(self):
        """Get list of mounted storage devices"""
        devices = []
        
        try:
            # Add home directory
            devices.append({
                'path': os.path.expanduser('~'),
                'label': 'Home'
            })
            
            # Add root directory
            devices.append({
                'path': '/',
                'label': 'Root'
            })
            
            # Add /run/media/user devices
            media_path = f"/run/media/{os.getenv('USER')}"
            if os.path.exists(media_path):
                for device in os.listdir(media_path):
                    device_path = os.path.join(media_path, device)
                    if os.path.ismount(device_path):
                        devices.append({
                            'path': device_path,
                            'label': f"USB {device}"
                        })
            
        except Exception as e:
            print(f"Error getting mounted devices: {e}")
        
        return devices

    def select_git_output(self):
        """Select output directory for git backups"""
        # Start from current output path if set, otherwise use repo parent dir
        start_dir = self.git_output_path.text()
        if not start_dir and self.git_repo_path.text():
            start_dir = os.path.dirname(self.git_repo_path.text())
        if not start_dir:
            start_dir = QDir.homePath()
            
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory for Git Backups",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if output_dir:
            self.git_output_path.setText(output_dir)
            self._update_git_buttons()

    def select_git_repo(self):
        """Select repository directory"""
        # Start from current repo path or release manager path
        settings = QSettings("Varchiver", "ReleaseManager")
        start_dir = self.git_repo_path.text() or settings.value("project_path") or QDir.homePath()
        
        repo_dir = QFileDialog.getExistingDirectory(
            self, "Select Repository Directory",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if repo_dir:
            self.git_repo_path.setText(repo_dir)
            
            # Update Git config tab
            if hasattr(self, 'git_repo_path_edit'):
                self.git_repo_path_edit.setText(repo_dir)
                self.init_git_config_manager(Path(repo_dir))
            
            # Set default output location if not already set
            if not self.git_output_path.text():
                default_output = os.path.join(os.path.dirname(repo_dir), "git_backups")
                self.git_output_path.setText(default_output)
                # Create directory if it doesn't exist
                os.makedirs(default_output, exist_ok=True)
            
            self._update_git_buttons()

    def _select_current_dir(self, dialog):
        """Helper to select current directory in file dialog"""
        current_dir = dialog.directory().absolutePath()
        dialog.done(QDialog.DialogCode.Accepted)
        dialog.setDirectory(current_dir)
        dialog.selectFile(current_dir)

    def _on_status(self, message):
        """Update status label with message"""
        self.status_label.setText(message)
        self.status_label.show()

    def _on_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)
        self.progress_bar.show()

    def _on_error(self, message, fatal=False):
        """Handle error message"""
        self.error_label.setText(f"Error: {message}")
        self.copy_error_button.setVisible(True)
        if fatal:
            QMessageBox.critical(self, "Error", message)
        self.progress_bar.setValue(0)  # Reset progress bar

    def _on_archive_finished(self, archive_path):
        """Handle archive completion"""
        self.progress_bar.hide()
        self.status_label.setText("Archive created successfully")
        self.current_thread = None
        QMessageBox.information(self, "Success", f"Archive created: {archive_path}")

    def _on_index_entry(self, entry):
        """Handle new index entry"""
        # Add entry to tree view
        if entry['is_dir']:
            return
        item = QTreeWidgetItem(self._tree)
        item.setText(0, entry['name'])
        item.setText(1, str(entry['size']))
        item.setText(2, str(entry.get('compressed', 0)))
        if entry['size'] > 0:
            ratio = (entry.get('compressed', entry['size']) / entry['size']) * 100
            item.setText(3, f"{ratio:.1f}%")

    def _on_tree_item_double_clicked(self, item, column):
        """Handle double-click on tree item"""
        if item and item.parent():  # Only handle child items (files)
            self.show_file_preview()

    def _copy_to_clipboard(self, text):
        """Copy text to clipboard and show brief notification"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # Show brief success message in status label
        self.status_label.setText("Address copied to clipboard!")
        # Reset after 2 seconds
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def copy_error_to_clipboard(self):
        """Copy error message to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.error_label.text())

    def show_archive_ui(self):
        """Show archive-related UI elements"""
        
        if hasattr(self, 'archive_group'):
            self.archive_group.show()
        if hasattr(self, 'extract_group'):
            self.extract_group.show()
        if hasattr(self, 'browse_group'):
            self.browse_group.show()
        # Remove Git UI if it exists
        self.remove_git_ui()

    def hide_archive_ui(self):
        """Hide archive-related UI elements"""
        if hasattr(self, 'archive_group'):
            self.archive_group.hide()
        if hasattr(self, 'extract_group'):
            self.extract_group.hide()
        if hasattr(self, 'browse_group'):
            self.browse_group.hide()

    def remove_git_ui(self):
        """Remove Git-related UI elements"""
        # Find and remove the Git tools group box
        for i in range(self.main_layout.count()):
            item = self.main_layout.itemAt(i)
            if item and item.widget():
                if isinstance(item.widget(), QGroupBox) and item.widget().title() == "GitTools":
                    widget = item.widget()
                    self.main_layout.removeWidget(widget)
                    widget.deleteLater()
                    break

    def clear_error(self):
        """Clear error message"""
        self.error_label.setText("")
        self.error_label.setVisible(False)
        self.copy_error_button.setVisible(False)

    def clear_archive(self):
        """Clear current archive"""
        self.current_archive_label.setText("")
        self.files_found_label.setText("")
        self.clear_error()
        self.hide_archive_ui()

    def show_release_manager(self):
        """Switch to dev tools mode and show release manager tab"""
        # Switch to dev tools mode if not already
        if self.mode_combo.currentText() != "Dev Tools":
            self.mode_combo.setCurrentText("Dev Tools")
            
        # Switch to release manager tab
        for i in range(self.git_tabs.count()):
            if self.git_tabs.tabText(i) == "ReleaseManager":
                self.git_tabs.setCurrentIndex(i)
                break

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add donation widget
        donation_widget = QWidget()
        donation_layout = QHBoxLayout()
        donation_widget.setLayout(donation_layout)
        
        sol_label = QLabel("Free the source! $Instancer or SOL:")
        sol_label.setStyleSheet("font-weight: bold;")
        donation_layout.addWidget(sol_label)
        sol_address = "4zn9C2pgnxQwHvmoKCnyoV1YLtYFX5qxSaTxE2T86JEq"
        sol_input = QLineEdit(sol_address)
        sol_input.setReadOnly(True)
        sol_input.setMinimumWidth(400)
        sol_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        donation_layout.addWidget(sol_input)
        
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(lambda: self._copy_to_clipboard(sol_address))
        donation_layout.addWidget(copy_button)
        
        donation_layout.addStretch()
        layout.addWidget(donation_widget)
        layout.addWidget(QLabel("Src repo: https://github.com/instancer-kirik/Varchiver"))
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Mode selector group
        self.mode_group = QGroupBox("Operation Mode")
        mode_layout = QVBoxLayout()
        self.mode_group.setLayout(mode_layout)
        
        # Mode selector and buttons
        mode_header = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            'Archive',           # Normal archiving with skip patterns
            'Dev Tools'         # Development tools and utilities
        ])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_header.addWidget(self.mode_combo)
        
        # Theme toggle
        self.theme_button = QPushButton()
        self.theme_button.clicked.connect(self.toggle_theme)
        mode_header.addWidget(self.theme_button)
        
        mode_layout.addLayout(mode_header)
        layout.addWidget(self.mode_group)

        # Initialize Git UI elements
        self.git_repo_path = QLineEdit()
        self.git_output_path = QLineEdit()
        self.git_status_label = QLabel("Select repository to begin")
        self.git_config_status = QLabel("Select a Git repository to begin")
        self.git_error_text = QTextEdit()
        self.git_progress_bar = QProgressBar()

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
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Error handling
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
        layout.addWidget(self.error_label)
        
        # Start in Archive mode
        self.on_mode_changed('Archive')

    def add_gitattribute(self, pattern: str):
        """Add a pattern to .gitattributes file."""
        if not self.git_repo_path_edit.text():
            QMessageBox.warning(self, "Error", "Please select a Git repository first")
            return

        repo_path = Path(self.git_repo_path_edit.text())
        gitattributes_path = repo_path / '.gitattributes'

        try:
            # Create .gitattributes if it doesn't exist
            if not gitattributes_path.exists():
                gitattributes_path.touch()

            # Read existing patterns
            existing_patterns = set()
            if gitattributes_path.exists():
                with open(gitattributes_path, 'r') as f:
                    existing_patterns = set(line.strip() for line in f.readlines())

            # Add new pattern if it doesn't exist
            if pattern not in existing_patterns:
                with open(gitattributes_path, 'a') as f:
                    if existing_patterns:  # Add newline if file is not empty
                        f.write('\n')
                    f.write(pattern + '\n')
                QMessageBox.information(self, "Success", f"Added pattern to .gitattributes: {pattern}")
            else:
                QMessageBox.information(self, "Info", f"Pattern already exists in .gitattributes: {pattern}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update .gitattributes: {str(e)}")

    def browse_git_repo(self):
        """Browse for a Git repository."""
        path = QFileDialog.getExistingDirectory(self, "Select Git Repository")
        if path:
            repo_path = Path(path)
            if not (repo_path / '.git').exists():
                QMessageBox.warning(self, "Error", "Selected directory is not a Git repository")
                return
            
            self.git_repo_path_edit.setText(str(repo_path))
            self.init_git_config_manager(repo_path)

    def init_git_config_manager(self, repo_path: Path):
        """Initialize the Git configuration manager for the selected repository."""
        try:
            # Clear existing manager
            if hasattr(self, 'git_config_manager') and self.git_config_manager:
                self.git_config_container.layout().removeWidget(self.git_config_manager)
                self.git_config_manager.deleteLater()
                self.git_config_manager = None

            # Create new manager
            self.git_config_manager = GitConfigManager(repo_path)
            self.git_config_container.layout().addWidget(self.git_config_manager)
            self.git_config_container.show()
            
            # Update status
            self.git_config_status.setText(f"Managing Git configuration for: {repo_path}")
            
            # Refresh untracked files if available
            if hasattr(self, 'untracked_list'):
                self.refresh_untracked_files()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize Git config manager: {str(e)}")
            self.git_config_status.setText("Error initializing Git config manager")

    def browse_aur_dir(self):
        """Browse for AUR package directory"""
        settings = QSettings("Varchiver", "ReleaseManager")
        start_dir = self.aur_path.text() or settings.value("aur_path") or QDir.homePath()
        
        aur_dir = QFileDialog.getExistingDirectory(
            self, "Select AUR Package Directory",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if aur_dir:
            self.aur_path.setText(aur_dir)
            settings.setValue("aur_path", aur_dir)

    def start_release_process(self):
        """Start the release process with the selected task."""
        if not self.git_repo_path_edit.text():
            QMessageBox.warning(self, "Error", "Please select a Git repository first")
            return

        version = self.version_input.text()
        if not version:
            QMessageBox.warning(self, "Error", "Please enter a version number")
            return

        # Check AUR directory if needed
        selected = self.task_combo.currentText()
        if "Update AUR" in selected and not self.aur_path.text():
            QMessageBox.warning(self, "Error", "Please select AUR package directory for AUR update")
            return

        # Save settings
        settings = QSettings("Varchiver", "ReleaseManager")
        settings.setValue("project_path", self.git_repo_path_edit.text())
        settings.setValue("last_version", version)
        settings.setValue("aur_path", self.aur_path.text())

        # Get selected tasks based on combo selection
        selected_tasks = []
        if "Update Version" in selected:
            selected_tasks.append('update_version')
        if "Create Release" in selected:
            selected_tasks.append('create_release')
        if "Update AUR" in selected:
            selected_tasks.append('update_aur')

        # Start release process
        self.release_start_button.setEnabled(False)
        self.release_output.clear()
        
        self.release_thread = ReleaseThread(Path(self.git_repo_path_edit.text()), version, selected_tasks, self.release_output)
        self.release_thread.finished.connect(self.on_release_complete)
        self.release_thread.start()

    def open_gitignore(self):
        """Open .gitignore file in text editor"""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Error", "Please select a Git repository first")
            return

        repo_path = Path(self.git_repo_path.text())
        gitignore_path = repo_path / '.gitignore'

        if not gitignore_path.exists():
            # Create .gitignore if it doesn't exist
            try:
                gitignore_path.touch()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create .gitignore: {str(e)}")
                return

        # Open dialog to edit .gitignore
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit .gitignore")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        editor = QTextEdit()
        try:
            with open(gitignore_path, 'r') as f:
                editor.setText(f.read())
        except Exception as e:
            QMessageBox.critical(dialog, "Error", f"Failed to read .gitignore: {str(e)}")
            return

        layout.addWidget(editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )

        def save_gitignore():
            try:
                with open(gitignore_path, 'w') as f:
                    f.write(editor.toPlainText())
                dialog.accept()
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"Failed to save .gitignore: {str(e)}")

        buttons.accepted.connect(save_gitignore)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec()

    def refresh_untracked_files(self):
        """Refresh the list of untracked files"""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Error", "Please select a Git repository first")
            return

        try:
            # Run git ls-files command
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.git_repo_path.text(),
                capture_output=True,
                text=True,
                check=True
            )

            # Clear and update list
            self.untracked_list.clear()
            if result.stdout:
                files = result.stdout.strip().split('\n')
                self.untracked_list.addItems(files)
            else:
                self.untracked_list.addItem("No untracked files found")

        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to get untracked files: {e.stderr}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get untracked files: {str(e)}")

    def _setup_release_manager(self):
        """Set up the release manager tab"""
        self.release_thread = None
        self.release_manager = ReleaseManager(self.project_dir)
        self.release_manager.output.connect(self._handle_release_output)
        self.release_manager.error.connect(self._handle_release_error)
        self.release_manager.progress.connect(self._handle_release_progress)
        self.release_manager.dialog_signal.connect(self._handle_release_dialog)
        return self.release_manager
        
    def _handle_release_dialog(self, title, message, options):
        """Handle dialog requests from the release thread"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        dialog.setIcon(QMessageBox.Icon.Question)
        
        # Add buttons for each option
        buttons = {}
        for option in options:
            button = dialog.addButton(option, QMessageBox.ButtonRole.ActionRole)
            buttons[button] = option
            
        dialog.setDefaultButton(dialog.addButton(QMessageBox.StandardButton.Cancel))
        
        # Show dialog and get response
        dialog.exec()
        clicked = dialog.clickedButton()
        
        if clicked in buttons:
            response = buttons[clicked]
            if self.release_thread:
                self.release_thread.handle_dialog_response(response)
        else:
            # Cancel was clicked
            if self.release_thread:
                self.release_thread.handle_dialog_response("Cancel")

def main():
    app = QApplication(sys.argv)
    widget = MainWidget()
    widget.show()
    signal.signal(signal.SIGINT, lambda sig, frame: widget.handle_interrupt())
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
