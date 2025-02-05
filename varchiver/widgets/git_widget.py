"""Git functionality widget for managing Git repositories."""

from pathlib import Path
import os
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QMessageBox, QFileDialog, QGroupBox, QTabWidget,
    QTextEdit, QFormLayout, QComboBox, QListWidget, QProgressBar,
    QDialog, QDialogButtonBox
)
from PyQt6.QtCore import pyqtSignal, QSettings, QDir
from datetime import datetime

from ..utils.git_manager import GitManager
from ..utils.git_config_manager import GitConfigManager
from ..utils.release_manager import ReleaseManager

class GitWidget(QWidget):
    """Widget for managing Git repository functionality."""
    
    # Signals
    repo_changed = pyqtSignal(str)  # Emitted when repository path changes
    sequester_path_changed = pyqtSignal(str)  # Emitted when sequester path changes
    artifacts_path_changed = pyqtSignal(str)  # Emitted when artifacts path changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load settings
        self.settings = QSettings("Varchiver", "ReleaseManager")
        
        # Initialize paths with defaults/saved settings
        self.default_repo_path = self.settings.value("project_path") or str(Path.home() / "Code")
        self.default_artifacts_path = self.settings.value("artifacts_path") or str(Path.home() / "Artifacts")
        self.default_git_url = self.settings.value("git_url") or "https://github.com/username/repo.git"
        
        # Initialize UI elements
        self.git_repo_path = QLineEdit(self.default_repo_path)
        self.git_output_path = QLineEdit(self.default_artifacts_path)
        self.git_url = QLineEdit(self.default_git_url)
        self.git_branch = QLineEdit()
        self.git_branch.setPlaceholderText("main")
        self.git_error_text = QLabel()
        self.git_status_label = QLabel()
        self.git_manager = GitManager()
        
        # Initialize managers
        self.git_config_manager = None
        self.release_manager = None
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the Git UI components."""
        layout = QVBoxLayout(self)
        
        # Common paths group at the top
        paths_group = QGroupBox("Repository Settings")
        paths_layout = QFormLayout()
        
        # Git URL and remote controls
        url_layout = QHBoxLayout()
        url_layout.addWidget(self.git_url)
        add_remote_btn = QPushButton("Add/Update Remote")
        add_remote_btn.clicked.connect(self.add_git_remote)
        url_layout.addWidget(add_remote_btn)
        paths_layout.addRow("Git URL:", url_layout)
        
        # Branch selection
        branch_layout = QHBoxLayout()
        branch_layout.addWidget(self.git_branch)
        paths_layout.addRow("Branch:", branch_layout)
        
        # Repository path selection
        repo_layout = QHBoxLayout()
        repo_layout.addWidget(self.git_repo_path)
        browse_repo_btn = QPushButton("Browse")
        browse_repo_btn.clicked.connect(self.select_git_repo)
        repo_layout.addWidget(browse_repo_btn)
        paths_layout.addRow("Local Path:", repo_layout)
        
        # Artifacts path selection
        artifacts_layout = QHBoxLayout()
        artifacts_layout.addWidget(self.git_output_path)
        browse_output_btn = QPushButton("Browse")
        browse_output_btn.clicked.connect(self.select_git_output)
        artifacts_layout.addWidget(browse_output_btn)
        paths_layout.addRow("Artifacts:", artifacts_layout)
        
        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Git Config Manager tab
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        
        # Git config container for GitConfigManager widget
        self.git_config_container = QWidget()
        config_container_layout = QVBoxLayout()
        self.git_config_container.setLayout(config_container_layout)
        config_layout.addWidget(self.git_config_container)
        
        # Gitignore editor button
        gitignore_btn = QPushButton("Edit .gitignore")
        gitignore_btn.clicked.connect(self.open_gitignore)
        config_layout.addWidget(gitignore_btn)
        
        tab_widget.addTab(config_tab, "Git Config")
        
        # Git Sequester tab
        sequester_tab = QWidget()
        sequester_layout = QVBoxLayout(sequester_tab)
        
        # Storage location
        storage_group = QGroupBox("Storage Location")
        storage_layout = QHBoxLayout()
        self.git_storage_path = QLineEdit(self.settings.value("git_storage_path") or 
                                        os.path.join(os.path.expanduser("~"), ".varchiver", "git_archives"))
        storage_layout.addWidget(self.git_storage_path)
        storage_browse = QPushButton("Browse")
        storage_browse.clicked.connect(self.select_git_storage)
        storage_layout.addWidget(storage_browse)
        storage_group.setLayout(storage_layout)
        sequester_layout.addWidget(storage_group)
        
        # Sequester operations
        sequester_buttons = QHBoxLayout()
        backup_btn = QPushButton("Backup Git Files")
        backup_btn.clicked.connect(self.backup_git_files)
        sequester_buttons.addWidget(backup_btn)
        
        restore_btn = QPushButton("Restore Git Files")
        restore_btn.clicked.connect(self.restore_git_files)
        sequester_buttons.addWidget(restore_btn)
        
        archive_btn = QPushButton("Archive State")
        archive_btn.clicked.connect(self.archive_git_state)
        sequester_buttons.addWidget(archive_btn)
        
        restore_state_btn = QPushButton("Restore State")
        restore_state_btn.clicked.connect(self.restore_git_state)
        sequester_buttons.addWidget(restore_state_btn)
        
        sequester_layout.addLayout(sequester_buttons)
        
        # Untracked files section
        untracked_group = QGroupBox("Untracked Files")
        untracked_layout = QVBoxLayout()
        
        refresh_btn = QPushButton("Refresh Untracked Files")
        refresh_btn.clicked.connect(self.refresh_untracked_files)
        untracked_layout.addWidget(refresh_btn)
        
        self.untracked_list = QListWidget()
        self.untracked_list.setMinimumHeight(200)
        untracked_layout.addWidget(self.untracked_list)
        
        untracked_group.setLayout(untracked_layout)
        sequester_layout.addWidget(untracked_group)
        
        # Sequester status and progress
        self.sequester_status = QTextEdit()
        self.sequester_status.setPlaceholderText("Operation log will appear here...")
        self.sequester_status.setReadOnly(True)
        sequester_layout.addWidget(self.sequester_status)
        
        self.sequester_progress = QProgressBar()
        self.sequester_progress.hide()
        sequester_layout.addWidget(self.sequester_progress)
        
        tab_widget.addTab(sequester_tab, "Git Sequester")
        
        # Release Manager tab
        release_tab = QWidget()
        release_layout = QVBoxLayout(release_tab)
        
        # Version input
        version_layout = QHBoxLayout()
        version_label = QLabel("Version:")
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("1.0.0")
        self.version_input.setText(self.settings.value("last_version", ""))
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_input)
        release_layout.addLayout(version_layout)
        
        # Task selection
        task_layout = QHBoxLayout()
        task_label = QLabel("Task:")
        self.task_combo = QComboBox()
        self.task_combo.addItems([
            "Update Version",
            "Create Release",
            "Update AUR",
            "All Tasks"
        ])
        task_layout.addWidget(task_label)
        task_layout.addWidget(self.task_combo)
        release_layout.addLayout(task_layout)
        
        # AUR package directory
        aur_layout = QHBoxLayout()
        aur_label = QLabel("AUR Package:")
        self.aur_path = QLineEdit()
        self.aur_path.setText(self.settings.value("aur_path", ""))
        aur_browse = QPushButton("Browse")
        aur_browse.clicked.connect(self.browse_aur_dir)
        aur_layout.addWidget(aur_label)
        aur_layout.addWidget(self.aur_path)
        aur_layout.addWidget(aur_browse)
        release_layout.addLayout(aur_layout)
        
        # Release buttons
        release_buttons = QHBoxLayout()
        self.release_start_button = QPushButton("Start Release Process")
        self.release_start_button.clicked.connect(self.start_release_process)
        release_buttons.addWidget(self.release_start_button)
        
        release_layout.addLayout(release_buttons)
        
        # Release log
        self.release_output = QTextEdit()
        self.release_output.setPlaceholderText("Release process log will appear here...")
        self.release_output.setReadOnly(True)
        release_layout.addWidget(self.release_output)
        
        tab_widget.addTab(release_tab, "Release Manager")
        
        layout.addWidget(tab_widget)
        
        # Status and error display at the bottom
        self.git_status_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.git_status_label)
        
        self.git_error_text.setStyleSheet("color: red;")
        self.git_error_text.setVisible(False)
        layout.addWidget(self.git_error_text)
        
        # Initialize Git config manager if repo is selected
        if self.git_repo_path.text():
            self.init_git_config_manager(Path(self.git_repo_path.text()))
            self.update_git_info()
        
    def select_git_repo(self):
        """Open dialog to select Git repository."""
        repo_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Repository Directory",
            self.git_repo_path.text() or str(Path.home())
        )
        if repo_dir:
            if self.git_manager.set_repository(repo_dir):
                self.git_repo_path.setText(repo_dir)
                self.repo_changed.emit(repo_dir)
                self.settings.setValue("project_path", repo_dir)
                self.init_git_config_manager(Path(repo_dir))
                self.update_git_info()
                self._update_git_buttons()
            else:
                QMessageBox.warning(self, "Error", "Selected directory is not a Git repository")
            
    def select_git_output(self):
        """Open dialog to select output directory."""
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Artifacts Directory",
            self.git_output_path.text() or str(Path.home())
        )
        if output_dir:
            if self.git_manager.set_output_path(output_dir):
                self.git_output_path.setText(output_dir)
                self.artifacts_path_changed.emit(output_dir)
                self.settings.setValue("artifacts_path", output_dir)
            else:
                QMessageBox.warning(self, "Error", "Failed to set artifacts directory")

    def add_git_remote(self):
        """Add or update Git remote."""
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
                
            # Save URL in settings
            self.settings.setValue("git_url", url)
                
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to update Git remote: {e.stderr}")

    def update_git_info(self):
        """Update Git remote URL and branch info."""
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

    def init_git_config_manager(self, repo_path: Path):
        """Initialize the Git configuration manager."""
        try:
            # Clear existing manager
            if self.git_config_manager:
                self.git_config_container.layout().removeWidget(self.git_config_manager)
                self.git_config_manager.deleteLater()
                self.git_config_manager = None

            # Create new manager
            self.git_config_manager = GitConfigManager(repo_path)
            self.git_config_container.layout().addWidget(self.git_config_manager)
            self.git_config_container.show()
            
            # Update status
            self.git_status_label.setText(f"Managing Git configuration for: {repo_path}")
            
            # Refresh untracked files
            self.refresh_untracked_files()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize Git config manager: {str(e)}")
            self.git_status_label.setText("Error initializing Git config manager")

    def open_gitignore(self):
        """Open .gitignore file in text editor."""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Error", "Please select a Git repository first")
            return

        repo_path = Path(self.git_repo_path.text())
        gitignore_path = repo_path / '.gitignore'

        if not gitignore_path.exists():
            try:
                gitignore_path.touch()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create .gitignore: {str(e)}")
                return

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
        """Refresh the list of untracked files."""
        if not self.git_repo_path.text():
            return

        try:
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.git_repo_path.text(),
                capture_output=True,
                text=True,
                check=True
            )

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

    def browse_aur_dir(self):
        """Browse for AUR package directory."""
        start_dir = self.aur_path.text() or self.settings.value("aur_path") or QDir.homePath()
        
        aur_dir = QFileDialog.getExistingDirectory(
            self, "Select AUR Package Directory",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if aur_dir:
            self.aur_path.setText(aur_dir)
            self.settings.setValue("aur_path", aur_dir)

    def start_release_process(self):
        """Start the release process."""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Error", "Please select a Git repository first")
            return

        version = self.version_input.text().strip()
        if not version:
            QMessageBox.warning(self, "Error", "Please enter a version number")
            return

        selected = self.task_combo.currentText()
        if "Update AUR" in selected and not self.aur_path.text():
            QMessageBox.warning(self, "Error", "Please select AUR package directory for AUR update")
            return

        # Save settings
        self.settings.setValue("project_path", self.git_repo_path.text())
        self.settings.setValue("last_version", version)
        self.settings.setValue("aur_path", self.aur_path.text())

        # Get selected tasks
        tasks = []
        if selected == "All Tasks" or "Update Version" in selected:
            tasks.append('update_version')
        if selected == "All Tasks" or "Create Release" in selected:
            tasks.append('create_release')
        if selected == "All Tasks" or "Update AUR" in selected:
            tasks.append('update_aur')

        # Start release process
        self.release_start_button.setEnabled(False)
        self.release_output.clear()
        
        try:
            if not self.release_manager:
                self.release_manager = ReleaseManager()
            
            self.release_manager.start_release(
                Path(self.git_repo_path.text()),
                version,
                tasks,
                self.aur_path.text() if 'update_aur' in tasks else None
            )
            
            self.release_output.append(f"Started release process for version {version}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start release process: {str(e)}")
            self.release_start_button.setEnabled(True)

    def _update_git_buttons(self):
        """Update Git button states."""
        has_repo = bool(self.git_repo_path.text() and 
                       os.path.exists(os.path.join(self.git_repo_path.text(), '.git')))
        
        # Update button states
        for button in self.findChildren(QPushButton):
            if button.text() not in ["Browse", "Select Git Storage"]:
                button.setEnabled(has_repo)
                
        # Update release manager button
        if hasattr(self, 'release_start_button'):
            self.release_start_button.setEnabled(has_repo)

    def select_git_storage(self):
        """Open dialog to select Git storage location."""
        storage_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Git Storage Location",
            self.git_output_path.text() or str(Path.home())
        )
        if storage_dir:
            self.sequester_path_changed.emit(storage_dir)
            
    def backup_git_files(self):
        """Backup Git files."""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Warning", "Please select a repository directory first")
            return
            
        if not self.git_output_path.text():
            QMessageBox.warning(self, "Warning", "Please select an output directory first")
            return
            
        try:
            self._update_backup_ui(True)
            success, message = self.git_manager.backup_repository()
            if success:
                QMessageBox.information(self, "Success", message)
            else:
                self._on_backup_failed(message)
        except Exception as e:
            self._on_backup_failed(str(e))
            
    def restore_git_files(self):
        """Restore Git files from backup."""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Warning", "Please select a repository directory first")
            return
            
        backup_file = QFileDialog.getOpenFileName(
            self,
            "Select Git Backup File",
            self.git_output_path.text() or str(Path.home()),
            "JSON Files (*.json)"
        )[0]
        
        if backup_file:
            try:
                self._update_backup_ui(True)
                success, message = self.git_manager.restore_repository(backup_file)
                if success:
                    QMessageBox.information(self, "Success", message)
                else:
                    self._on_backup_failed(message)
            except Exception as e:
                self._on_backup_failed(str(e))
                
    def archive_git_state(self):
        """Archive current Git state."""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Warning", "Please select a repository directory first")
            return
            
        try:
            if self.git_manager.archive_state():
                QMessageBox.information(self, "Success", "Git state archived successfully")
            else:
                QMessageBox.warning(self, "Error", "Failed to archive Git state")
        except Exception as e:
            self.git_error_text.setText(str(e))
            self.git_error_text.setVisible(True)
            
    def restore_git_state(self):
        """Restore Git state from archive."""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Warning", "Please select a repository directory first")
            return
            
        try:
            if self.git_manager.restore_state():
                QMessageBox.information(self, "Success", "Git state restored successfully")
            else:
                QMessageBox.warning(self, "Error", "Failed to restore Git state")
        except Exception as e:
            self.git_error_text.setText(str(e))
            self.git_error_text.setVisible(True)
            
    def _update_backup_ui(self, in_progress: bool):
        """Update UI elements during backup/restore operations."""
        if in_progress:
            self.git_status_label.setText("Operation in progress...")
        else:
            self.git_status_label.setText("")
        self._update_git_buttons()
        
    def _on_backup_failed(self, error_msg: str):
        """Handle backup operation failure."""
        self._update_backup_ui(False)
        self.git_error_text.setText(f"Backup failed: {error_msg}")
        self.git_error_text.setVisible(True)
        QMessageBox.critical(self, "Error", f"Backup failed: {error_msg}") 