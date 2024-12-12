import sys
import os
from pathlib import Path
import tarfile
import zipfile
import rarfile  

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QProgressBar, QFileDialog, 
                            QDialog, QGridLayout, QTextEdit, QComboBox, QGroupBox, QCheckBox,
                            QLineEdit, QInputDialog, QProgressDialog, QTreeWidget, QTreeWidgetItem, QHeaderView, QFrame, QScrollArea,
                            QListView, QTreeView, QAbstractItemView, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont
import fnmatch
import subprocess
import time
import pickle
import re
import gzip
import tempfile
from sevenz import SevenZipHandler

    # Common patterns to skip
DEFAULT_SKIP_PATTERNS = {
        'build': ['_build', 'build', 'dist', 'target', '*/_build', '*/build', '*/dist', '*/target'],
        'deps': ['deps', 'node_modules', 'venv', '.venv', '__pycache__', 'vendor', '*/deps', '*/deps/*', '**/deps/**', '**/node_modules/**', '**/venv/**', '**/.venv/**', '**/__pycache__/**', '**/vendor/**'],
        'ide': ['.idea', '.vscode', '*.pyc', '*.pyo', '*.pyd', '.DS_Store', '**/.idea/**', '**/.vscode/**', '**/*.pyc', '**/*.pyo', '**/*.pyd', '**/.DS_Store'],
        'git': ['.git', '.gitignore', '.gitmodules', '.gitattributes', '**/.git/**', '**/.gitignore', '**/.gitmodules', '**/.gitattributes'],
        'elixir': ['_build', 'deps', '.elixir_ls', '.fetch', '**/_build/**', '**/deps/**', '**/.elixir_ls/**', '**/.fetch/**'],
        'logs': ['*.log', 'logs', '*.dump', '**/*.log', '**/logs/**', '**/*.dump'],
        'tmp': ['tmp', '*.tmp', '*.bak', '*.swp', '**/tmp/**', '**/*.tmp', '**/*.bak', '**/*.swp']
    }
  
class TarGzWidget(QWidget):
    def browse_archive(self):
        """Browse archive contents"""
        try:
            print(f"[TarGzWidget] Starting browse_archive for {self.archive_name}")  # Debug
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Create browse thread
            self.browse_thread = BrowseThread(
                self.archive_name,
                password=self.password if hasattr(self, 'password') else None
            )
            self.browse_thread.finished.connect(self.browse_finished)
            self.browse_thread.error.connect(self.handle_error)
            self.browse_thread.status.connect(self.update_status)
            self.browse_thread.progress.connect(self.progress_bar.setValue)
            self.browse_thread.show_contents.connect(self.show_contents)
            
            # Start browsing
            self.browse_thread.start()
            
        except Exception as e:
            print(f"[TarGzWidget] Error in browse_archive: {e}")  # Debug
            self.handle_error(str(e))

    def show_contents(self, contents):
        """Show archive contents in the tree view"""
        try:
            print(f"[TarGzWidget] Showing contents, got {len(contents)} items")  # Debug
            for item in contents:
                print(f"[TarGzWidget] Item: {item}")  # Debug
                
            self.tree.clear()
            
            # Create root item
            root = QTreeWidgetItem(self.tree)
            root.setText(0, os.path.basename(self.archive_name))
            root.setIcon(0, QIcon.fromTheme('folder'))
            
            # Add items to tree
            for item in contents:
                try:
                    path_parts = item['name'].split('/')
                    current = root
                    
                    # Create tree structure
                    for i, part in enumerate(path_parts[:-1]):
                        # Find or create folder item
                        found = False
                        for j in range(current.childCount()):
                            if current.child(j).text(0) == part:
                                current = current.child(j)
                                found = True
                                break
                        
                        if not found:
                            folder = QTreeWidgetItem(current)
                            folder.setText(0, part)
                            folder.setIcon(0, QIcon.fromTheme('folder'))
                            current = folder
                    
                    # Add file item
                    file_item = QTreeWidgetItem(current)
                    file_item.setText(0, path_parts[-1])
                    file_item.setIcon(0, QIcon.fromTheme('text-x-generic'))
                    
                    # Add size information
                    if 'size' in item:
                        size_str = format_size(item['size'])
                        file_item.setText(1, size_str)
                    
                    if 'compressed_size' in item:
                        compressed_str = format_size(item['compressed_size'])
                        file_item.setText(2, compressed_str)
                        
                except Exception as e:
                    print(f"[TarGzWidget] Error adding item {item['name']}: {e}")  # Debug
                    continue
            
            # Expand root item
            root.setExpanded(True)
            
        except Exception as e:
            print(f"[TarGzWidget] Error in show_contents: {e}")  # Debug
            self.handle_error(str(e))

    def browse_finished(self):
        """Called when browsing is complete"""
        print("[TarGzWidget] Browse finished")  # Debug
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(100)
        
    def handle_error(self, error_msg):
        """Handle error from browse thread"""
        print(f"[TarGzWidget] Error: {error_msg}")  # Debug
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error_msg}")
        
    def update_status(self, status):
        """Update status message"""
        print(f"[TarGzWidget] Status: {status}")  # Debug
        self.status_label.setText(status)
        
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Varchive')
        
        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Current archive label
        self.current_archive_label = QLabel('')
        layout.addWidget(self.current_archive_label)

        # Status label for detailed progress
        self.status_label = QLabel('')
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Files found label
        self.files_found_label = QLabel('')
        layout.addWidget(self.files_found_label)

        # Error text
        self.error_text = QTextEdit()
        self.error_text.setReadOnly(True)
        self.error_text.setVisible(False)
        self.error_text.setMaximumHeight(60)
        layout.addWidget(self.error_text)
        
        # Create tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Name', 'Size', 'Compressed'])
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree)
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Fix permissions button (hidden by default)
        self.fix_perms_button = QPushButton('Fix Git Permissions')
        self.fix_perms_button.clicked.connect(self.fix_git_permissions)
        self.fix_perms_button.setVisible(False)
        layout.addWidget(self.fix_perms_button)

        # Skip patterns section
        skip_group = QGroupBox("Skip Options")
        skip_layout = QVBoxLayout()
        
        # Style for checkboxes
        checkbox_style = """
            QCheckBox {
                color: darkgreen;
            }
            QCheckBox:hover {
                color: black;
            }
        """
        
        # Create checkboxes for each category with patterns
        self.skip_checkboxes = {}
        for category, patterns in DEFAULT_SKIP_PATTERNS.items():
            patterns_str = ', '.join(patterns)
            checkbox = QCheckBox(f"Skip {category} ({patterns_str})")
            checkbox.setStyleSheet(checkbox_style)
            checkbox.setChecked(True)  # Enable by default
            skip_layout.addWidget(checkbox)
            self.skip_checkboxes[category] = checkbox
        
        skip_group.setLayout(skip_layout)
        layout.addWidget(skip_group)

        # Options section
        options_layout = QHBoxLayout()
        
        # Collision strategy dropdown
        collision_label = QLabel('On Collision:')
        options_layout.addWidget(collision_label)
        
        self.collision_strategy = QComboBox()
        self.collision_strategy.addItems([
            'ask',         # Ask user for each collision
            'skip',        # Skip existing files
            'overwrite',   # Always overwrite
            'newer',       # Keep newer file
            'larger',      # Keep larger file
            'smaller',     # Keep smaller file
            'rename'       # Add number suffix
        ])
        self.collision_strategy.setToolTip(
            'How to handle file conflicts:\n'
            'ask: Show detailed comparison and ask for each file\n'
            'skip: Skip existing files\n'
            'overwrite: Replace existing files\n'
            'newer: Keep the newer file\n'
            'larger: Keep the larger file\n'
            'smaller: Keep the smaller file\n'
            'rename: Add number suffix to new files'
        )
        options_layout.addWidget(self.collision_strategy)
        
        # Add compression level selector
        compression_label = QLabel('Compression:')
        options_layout.addWidget(compression_label)
        
        self.compression_level = QComboBox()
        self.compression_level.addItems([
            'Store (0)',
            'Fastest (1)',
            'Fast (3)',
            'Normal (5)',
            'Maximum (7)',
            'Ultra (9)'
        ])
        self.compression_level.setCurrentText('Normal (5)')  # Default to normal compression
        self.compression_level.setToolTip(
            'Compression level:\n'
            'Store (0): No compression, fastest\n'
            'Fastest (1): Minimal compression, very fast\n'
            'Fast (3): Light compression, fast\n'
            'Normal (5): Balanced compression and speed\n'
            'Maximum (7): High compression, slower\n'
            'Ultra (9): Maximum compression, slowest'
        )
        options_layout.addWidget(self.compression_level)
        
        # Add preserve permissions checkbox
        self.preserve_permissions = QCheckBox('Preserve executable permissions')
        self.preserve_permissions.setChecked(True)  # Enable by default
        self.preserve_permissions.setToolTip('Preserve executable permissions when extracting files')
        options_layout.addWidget(self.preserve_permissions)
        
        layout.addLayout(options_layout)

        # Buttons
        button_layout = QHBoxLayout()
        
        self.browse_button = QPushButton('Browse Archive')
        self.browse_button.clicked.connect(self.browse_archive)
        button_layout.addWidget(self.browse_button)
        
        self.view_current_button = QPushButton('View Current')
        self.view_current_button.clicked.connect(lambda: self.browse_archive(use_current=True))
        self.view_current_button.setEnabled(False)  # Disabled until we have a current archive
        button_layout.addWidget(self.view_current_button)
        
        self.compress_button = QPushButton('Compress _ to...')
        self.compress_button.clicked.connect(self.compress_files)
        button_layout.addWidget(self.compress_button)

        self.extract_button = QPushButton('Extract _ into...')
        self.extract_button.clicked.connect(self.extract_files)
        button_layout.addWidget(self.extract_button)
        
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.compression_thread = None
        self.extraction_thread = None
        self.browse_thread = None

    def get_active_skip_patterns(self):
        patterns = []
        for category, checkbox in self.skip_checkboxes.items():
            if checkbox.isChecked():
                patterns.extend(DEFAULT_SKIP_PATTERNS[category])
        return patterns

    def fix_git_permissions(self):
        try:
            git_dir = None
            for file in getattr(self.compression_thread, 'files', []):
                if '.git' in file.split(os.sep):
                    git_dir = file[:file.index('.git')] + '.git'
                    break
            
            if git_dir and os.path.exists(git_dir):
                subprocess.run(['chmod', '-R', 'u+rw', os.path.join(git_dir, 'objects')], check=True)
                dialog = QDialog()
                dialog.setWindowTitle('Success')
                dialog_layout = QGridLayout(dialog)
                
                # Format info
                formats = QLabel(
                    "Git permissions fixed successfully!"
                )
                formats.setFont(QFont("Monospace"))
                dialog_layout.addWidget(formats, 0, 0)
                
                # OK button
                ok_button = QPushButton("OK")
                ok_button.clicked.connect(dialog.accept)
                dialog_layout.addWidget(ok_button, 1, 0)
                
                dialog.exec()
            else:
                dialog = QDialog()
                dialog.setWindowTitle('Error')
                dialog_layout = QGridLayout(dialog)
                
                # Format info
                formats = QLabel(
                    "Could not locate .git directory"
                )
                formats.setFont(QFont("Monospace"))
                dialog_layout.addWidget(formats, 0, 0)
                
                # OK button
                ok_button = QPushButton("OK")
                ok_button.clicked.connect(dialog.accept)
                dialog_layout.addWidget(ok_button, 1, 0)
                
                dialog.exec()
        except Exception as e:
            dialog = QDialog()
            dialog.setWindowTitle('Error')
            dialog_layout = QGridLayout(dialog)
            
            # Format info
            formats = QLabel(
                f"Failed to fix permissions: {str(e)}"
            )
            formats.setFont(QFont("Monospace"))
            dialog_layout.addWidget(formats, 0, 0)
            
            # OK button
            ok_button = QPushButton("OK")
            ok_button.clicked.connect(dialog.accept)
            dialog_layout.addWidget(ok_button, 1, 0)
            
            dialog.exec()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_label(self, text):
        self.status_label.setText(text)
        # Reset UI elements
        self.progress_bar.setVisible(False)
        self.error_text.setVisible(False)
        self.fix_perms_button.setVisible(False)
        self.files_found_label.setText("")
        self.compress_button.setEnabled(True)
        self.extract_button.setEnabled(True)
        
        # Start indexing for tar archives after compression
        if text.startswith('Compressed') and self.current_archive and \
           self.current_archive.lower().endswith(('.tar', '.tar.gz', '.tar.bz2', '.tgz')):
            self.status_label.setText(text + "\nCreating archive index...")
            self.browse_thread = BrowseThread(self.current_archive)
            self.browse_thread.finished.connect(self.index_created)
            self.browse_thread.error.connect(self.show_error)
            self.browse_thread.start()
            
    def index_created(self, info):
        """Called when archive indexing is complete"""
        self.status_label.setText(self.status_label.text().replace("\nCreating archive index...", "\nArchive index created"))


    def show_error(self, error_message, is_permission_error):
        self.error_text.setText(f"Error: {error_message}")
        self.error_text.setVisible(True)
        
        # Only show fix permissions button if Git files aren't being skipped
        git_checkbox = self.skip_checkboxes.get('git')
        show_perm_button = is_permission_error and git_checkbox and not git_checkbox.isChecked()
        self.fix_perms_button.setVisible(show_perm_button)
        
        self.progress_bar.setVisible(False)
        self.compress_button.setEnabled(True)
        self.extract_button.setEnabled(True)
        
    def get_password_if_needed(self, archive_path, mode='r'):
        """Get password for password-protected archives"""
        if not os.path.exists(archive_path):
            return None
            
        try:
            # Try to open without password first
            test_archive = None
            archive_type = self._get_archive_type(archive_path)
            
            if archive_type == '.zip':
                test_archive = zipfile.ZipFile(archive_path, mode)
                try:
                    first_file = test_archive.namelist()[0]
                    test_archive.open(first_file)  # Try to read first file
                    return None  # No password needed
                except RuntimeError:  # Password required
                    pass
                finally:
                    test_archive.close()
                    
            elif archive_type == '.7z':
                test_archive = SevenZipFile(archive_path, mode)
                try:
                    first_file = test_archive.namelist()[0]
                    test_archive.read(first_file)  # Try to read first file
                    return None  # No password needed
                except RuntimeError:  # Password required
                    pass
                finally:
                    if test_archive:
                        test_archive.close()
                        
            # If we get here, either password is needed or it's not a supported encrypted format
            password, ok = QInputDialog.getText(
                self, 'Password Required', 
                'Enter password for archive:',
                QLineEdit.EchoMode.Password
            )
            
            if ok and password:
                return password
            return None
            
        except (zipfile.BadZipFile, FileNotFoundError, RuntimeError) as e:
            return None

    def _get_archive_type(self, archive_path):
        """Helper method to determine archive type from file extension"""
        ext = os.path.splitext(archive_path.lower())[1]
        if ext in ('.gz', '.bz2', '.xz'):
            # Handle .tar.gz, .tar.bz2, etc.
            base = os.path.splitext(archive_path[:-len(ext)])[1]
            if base == '.tar':
                return base + ext
        return ext

    def fix_git_permissions(self):
        try:
            git_dir = None
            for file in getattr(self.compression_thread, 'files', []):
                if '.git' in file.split(os.sep):
                    git_dir = file[:file.index('.git')] + '.git'
                    break
            
            if git_dir and os.path.exists(git_dir):
                subprocess.run(['chmod', '-R', 'u+rw', os.path.join(git_dir, 'objects')], check=True)
                dialog = QDialog()
                dialog.setWindowTitle('Success')
                dialog_layout = QGridLayout(dialog)
                
                # Format info
                formats = QLabel(
                    "Git permissions fixed successfully!"
                )
                formats.setFont(QFont("Monospace"))
                dialog_layout.addWidget(formats, 0, 0)
                
                # OK button
                ok_button = QPushButton("OK")
                ok_button.clicked.connect(dialog.accept)
                dialog_layout.addWidget(ok_button, 1, 0)
                
                dialog.exec()
            else:
                dialog = QDialog()
                dialog.setWindowTitle('Error')
                dialog_layout = QGridLayout(dialog)
                
                # Format info
                formats = QLabel(
                    "Could not locate .git directory"
                )
                formats.setFont(QFont("Monospace"))
                dialog_layout.addWidget(formats, 0, 0)
                
                # OK button
                ok_button = QPushButton("OK")
                ok_button.clicked.connect(dialog.accept)
                dialog_layout.addWidget(ok_button, 1, 0)
                
                dialog.exec()
        except Exception as e:
            dialog = QDialog()
            dialog.setWindowTitle('Error')
            dialog_layout = QGridLayout(dialog)
            
            # Format info
            formats = QLabel(
                f"Failed to fix permissions: {str(e)}"
            )
            formats.setFont(QFont("Monospace"))
            dialog_layout.addWidget(formats, 0, 0)
            
            # OK button
            ok_button = QPushButton("OK")
            ok_button.clicked.connect(dialog.accept)
            dialog_layout.addWidget(ok_button, 1, 0)
            
            dialog.exec()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_label(self, text):
        self.status_label.setText(text)
        # Reset UI elements
        self.progress_bar.setVisible(False)
        self.error_text.setVisible(False)
        self.fix_perms_button.setVisible(False)
        self.files_found_label.setText("")
        self.compress_button.setEnabled(True)
        self.extract_button.setEnabled(True)
        
        # Start indexing for tar archives after compression
        if text.startswith('Compressed') and self.current_archive and \
           self.current_archive.lower().endswith(('.tar', '.tar.gz', '.tar.bz2', '.tgz')):
            self.status_label.setText(text + "\nCreating archive index...")
            self.browse_thread = BrowseThread(self.current_archive)
            self.browse_thread.finished.connect(self.index_created)
            self.browse_thread.error.connect(self.show_error)
            self.browse_thread.start()
            
    def index_created(self, info):
        """Called when archive indexing is complete"""
        self.status_label.setText(self.status_label.text().replace("\nCreating archive index...", "\nArchive index created"))


def setup_file_associations():
    """Set up file associations for supported archive formats"""
    try:
        import subprocess
        import os
        from pathlib import Path

        # Get the executable path
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            exe_path = sys.executable
        else:
            # Running as script
            exe_path = 'varchiver'

        # Define MIME types and their extensions
        mime_types = {
            'application/zip': ['.zip'],
            'application/x-tar': ['.tar'],
            'application/x-compressed-tar': ['.tar.gz', '.tgz'],
            'application/x-bzip-compressed-tar': ['.tar.bz2'],
            'application/x-rar': ['.rar'],
            'application/x-7z-compressed': ['.7z']
        }

        # Check if running with sufficient privileges
        is_root = os.geteuid() == 0

        for mime_type, extensions in mime_types.items():
            for ext in extensions:
                try:
                    # Update MIME database
                    if is_root:
                        subprocess.run(['xdg-mime', 'default', 'varchiver.desktop', mime_type], check=True)
                    else:
                        subprocess.run(['xdg-mime', 'default', 'varchiver.desktop', mime_type], check=True)
                except subprocess.CalledProcessError:
                    print(f"Warning: Could not set as default handler for {mime_type}")

        # Update desktop database
        try:
            if is_root:
                subprocess.run(['update-desktop-database'], check=True)
            else:
                home = Path.home()
                local_apps = home / '.local/share/applications'
                subprocess.run(['update-desktop-database', str(local_apps)], check=True)
        except subprocess.CalledProcessError:
            print("Warning: Could not update desktop database")

    except Exception as e:
        print(f"Warning: Could not set up file associations: {e}")

def main(args=None):
    """Main entry point for Varchiver"""
    app = QApplication(sys.argv)
    window = TarGzWidget()
    
    # Handle command line arguments for opening archives
    if args:
        archive_path = os.path.abspath(args[0])
        if os.path.isfile(archive_path):
            # Check if it's a supported archive type
            supported_extensions = ('.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.rar', '.7z')
            if archive_path.lower().endswith(supported_extensions):
                window.archive_name = archive_path
                window.current_archive_label.setText(f"Current: {os.path.basename(archive_path)}")
                window.view_current_button.setEnabled(True)
                # Automatically show archive contents
                window.show()  # Show window before browsing to ensure proper UI updates
                QTimer.singleShot(100, lambda: window.browse_archive(use_current=True))  # Use QTimer to ensure UI is ready
            else:
                window.show()
                dialog = QDialog()
                dialog.setWindowTitle('Unsupported Format')
                dialog_layout = QGridLayout(dialog)
                
                # Format info
                formats = QLabel(
                    f'The file {os.path.basename(archive_path)} is not a supported archive format.\n\n'
                    'Supported formats:\n'
                    '• ZIP (*.zip)\n'
                    '• TAR (*.tar)\n'
                    '• Gzipped TAR (*.tar.gz, *.tgz)\n'
                    '• Bzip2 TAR (*.tar.bz2)\n'
                    '• RAR (*.rar)\n'
                    '• 7Z (*.7z)'
                )
                formats.setFont(QFont("Monospace"))
                dialog_layout.addWidget(formats, 0, 0)
                
                # OK button
                ok_button = QPushButton("OK")
                ok_button.clicked.connect(dialog.accept)
                dialog_layout.addWidget(ok_button, 1, 0)
                
                dialog.exec()
    else:
        window.show()

    # Check if this is first run and set up file associations
    config_dir = Path.home() / '.config' / 'varchiver'
    config_file = config_dir / 'first_run'
    
    if not config_file.exists():
        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Ask user if they want to set up file associations
        response = QMessageBox.question(
            window,
            'File Associations',
            'Would you like to set Varchiver as the default application for archive files?\n\n'
            'This will set up associations for:\n'
            '• ZIP files (*.zip)\n'
            '• TAR archives (*.tar)\n'
            '• Gzipped TAR (*.tar.gz, *.tgz)\n'
            '• Bzip2 TAR (*.tar.bz2)\n'
            '• RAR archives (*.rar)\n'
            '• 7Z archives (*.7z)',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if response == QMessageBox.StandardButton.Yes:
            setup_file_associations()
        
        # Create first_run file to mark setup as complete
        config_file.touch()
    
    return app.exec()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))