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
from PyQt6.QtCore import pyqtSignal, QSettings, QDir, Qt
from PyQt6.QtGui import QMovie, QTextCursor
from datetime import datetime
import re
from typing import List, Dict

from ..utils.git_manager import GitManager
from ..utils.git_config_manager import GitConfigManager
from ..utils.release_manager import ReleaseManager
from .git_submodule_widget import GitSubmoduleWidget
from .git_sequester import GitSequester

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
        self.default_storage_path = self.settings.value("git_storage_path") or str(Path.home() / ".varchiver" / "git_archives")
        self.default_git_url = self.settings.value("git_url") or "https://github.com/username/repo.git"
        self.default_aur_url = self.settings.value("aur_url") or "ssh://aur@aur.archlinux.org/package-name.git"
        
        # Initialize UI elements
        self.git_repo_path = QLineEdit(self.default_repo_path)
        self.git_storage_path = QLineEdit(self.default_storage_path)
        self.git_url = QLineEdit(self.default_git_url)
        self.aur_url = QLineEdit(self.default_aur_url)
        self.aur_path = QLineEdit()  # Initialize with empty text
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
        
        # Add compact view toggle button in the top-right
        compact_layout = QHBoxLayout()
        compact_layout.addStretch()
        self.compact_btn = QPushButton("Compact")
        self.compact_btn.setCheckable(True)
        self.compact_btn.clicked.connect(self.toggle_compact_view)
        self.compact_btn.setFixedWidth(70)
        compact_layout.addWidget(self.compact_btn)
        layout.addLayout(compact_layout)
        
        # Repository path group with status indicator
        repo_group = QGroupBox("Repository Settings")
        repo_layout = QFormLayout()
        
        # Repository path with status indicator
        repo_path_layout = QHBoxLayout()
        repo_path_layout.addWidget(self.git_repo_path)
        
        self.repo_status_indicator = QLabel()
        self.repo_status_indicator.setFixedSize(16, 16)
        self.repo_status_indicator.setStyleSheet("""
            QLabel {
                border: 1px solid #666;
                border-radius: 8px;
                background: #f44336;  /* Red by default */
            }
            QLabel[valid="true"] {
                background: #4caf50;  /* Green when valid */
            }
        """)
        repo_path_layout.addWidget(self.repo_status_indicator)
        
        browse_repo_btn = QPushButton("Browse")
        browse_repo_btn.clicked.connect(self.select_git_repo)
        repo_path_layout.addWidget(browse_repo_btn)
        
        # Commit message input
        commit_layout = QHBoxLayout()
        self.commit_message = QLineEdit()
        self.commit_message.setPlaceholderText("Enter commit message...")
        commit_btn = QPushButton("Commit")
        commit_btn.clicked.connect(self.commit_changes)
        commit_layout.addWidget(self.commit_message)
        commit_layout.addWidget(commit_btn)
        repo_layout.addRow("Local Path:", repo_path_layout)
        
        # Git URL and remote controls
        url_layout = QHBoxLayout()
        url_layout.addWidget(self.git_url)
        
        remote_btn_layout = QHBoxLayout()
        init_repo_btn = QPushButton("Initialize Git")
        init_repo_btn.clicked.connect(self.init_git_repo)
        remote_btn_layout.addWidget(init_repo_btn)
        
        add_remote_btn = QPushButton("Add/Update Remote")
        add_remote_btn.clicked.connect(self.add_git_remote)
        remote_btn_layout.addWidget(add_remote_btn)
        
        url_layout.addLayout(remote_btn_layout)
        repo_layout.addRow("Git URL:", url_layout)
        
        # AUR URL and controls
        aur_layout = QHBoxLayout()
        aur_layout.addWidget(self.aur_url)
        
        # Add buttons for AUR URL
        aur_url_btn = QPushButton("Generate URL")
        aur_url_btn.clicked.connect(self.generate_aur_url)
        aur_layout.addWidget(aur_url_btn)
        
        repo_layout.addRow("AUR URL:", aur_layout)
        
        # Branch selection with create option
        branch_layout = QHBoxLayout()
        branch_layout.addWidget(self.git_branch)
        create_branch_btn = QPushButton("Create Branch")
        create_branch_btn.clicked.connect(self.create_branch)
        branch_layout.addWidget(create_branch_btn)
        repo_layout.addRow("Branch:", branch_layout)
        
        # Storage location (combines artifacts and git storage)
        storage_layout = QHBoxLayout()
        storage_layout.addWidget(self.git_storage_path)
        storage_browse = QPushButton("Browse")
        storage_browse.clicked.connect(self.select_git_storage)
        storage_layout.addWidget(storage_browse)
        repo_layout.addRow("Storage Path:", storage_layout)
        
        # Add repository info display
        self.repo_info = QTextEdit()
        self.repo_info.setReadOnly(True)
        self.repo_info.setMaximumHeight(100)
        repo_layout.addRow("Repository Info:", self.repo_info)
        
        repo_group.setLayout(repo_layout)
        layout.addWidget(repo_group)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
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
        
        self.tab_widget.addTab(config_tab, "Git Config")
        
        # Git Sequester tab
        sequester_tab = QWidget()
        sequester_layout = QVBoxLayout(sequester_tab)
        
        # Initialize GitSequester widget
        self.sequester_widget = GitSequester(str(self.git_repo_path.text()))
        self.sequester_widget.set_storage_path(str(self.git_storage_path.text()))
        sequester_layout.addWidget(self.sequester_widget)
        
        self.tab_widget.addTab(sequester_tab, "Git Sequester")
        
        # Git Submodules tab
        submodules_tab = QWidget()
        submodules_layout = QVBoxLayout(submodules_tab)
        submodules_tab.setLayout(submodules_layout)
        
        # Create placeholder for submodule widget
        self.submodule_widget = None
        self.submodules_layout = submodules_layout  # Store reference for later
        
        self.tab_widget.addTab(submodules_tab, "Git Submodules")
        
        # Connect storage path changes
        self.git_storage_path.textChanged.connect(
            lambda path: self.sequester_widget.set_storage_path(path) if self.sequester_widget else None
        )
        
        # Release Manager tab
        release_tab = QWidget()
        release_layout = QVBoxLayout(release_tab)
        
        # Create ReleaseManager instance
        self.release_manager_widget = ReleaseManager()
        release_layout.addWidget(self.release_manager_widget)
        
        self.tab_widget.addTab(release_tab, "Release Manager")
        
        # Connect signals from ReleaseManager
        self.release_manager_widget.progress.connect(self.update_release_progress)
        self.release_manager_widget.error.connect(self.handle_release_error)
        self.release_manager_widget.finished.connect(self.release_finished)
        self.release_manager_widget.dialog_signal.connect(self.handle_release_dialog)
        
        # Update project directory when git repo changes
        self.git_repo_path.textChanged.connect(self._update_release_manager_path)
        
        layout.addWidget(self.tab_widget)
        
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
        
    def _init_submodule_widget(self, repo_path: Path):
        """Initialize or update the submodule widget."""
        if not repo_path or not repo_path.exists():
            return
            
        # Remove existing widget if any
        if self.submodule_widget:
            self.submodules_layout.removeWidget(self.submodule_widget)
            self.submodule_widget.deleteLater()
            
        # Create new widget
        self.submodule_widget = GitSubmoduleWidget(repo_path)
        self.submodules_layout.addWidget(self.submodule_widget)
        self.submodule_widget.refresh_submodules()

    def select_git_repo(self):
        """Open dialog to select Git repository."""
        repo_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Git Repository",
            self.git_repo_path.text() or str(Path.home())
        )
        if repo_dir:
            repo_path = Path(repo_dir)
            self.git_repo_path.setText(str(repo_path))
            # Set default storage path based on repository
            default_storage = repo_path.parent / ".varchiver" / "git_archives"
            self.git_storage_path.setText(str(default_storage))
            
            # Update repository info and status
            self._infer_repository_info(repo_path)
            self.update_repo_status()
            
            # Update release manager
            if hasattr(self, 'release_manager_widget'):
                self.release_manager_widget.project_dir_input.setText(str(repo_path))
                self.release_manager_widget.project_dir = repo_path
                # Set task preset to "Full Release (All Tasks)"
                self.release_manager_widget.task_preset.setCurrentIndex(0)
                self.release_manager_widget.update_task_selection(0)
                
                # Try to infer version for release manager
                version = self._infer_version(repo_path)
                if version and hasattr(self.release_manager_widget, 'version_input'):
                    self.release_manager_widget.version_input.setText(version)

    def _reset_ui_state(self):
        """Reset UI state when switching repositories."""
        # Clear branch input (will be inferred if exists)
        self.git_branch.clear()
        
        # Clear URL (will be inferred if exists)
        self.git_url.setText(self.default_git_url)
        
        # Clear AUR info and reset to defaults
        self.aur_url.clear()  # Clear completely instead of setting default
        self.aur_path.clear()
        self.settings.remove("aur_url")  # Remove from settings to force re-detection
        self.settings.remove("aur_path")
        
        # Clear error and status
        self.git_error_text.clear()
        self.git_error_text.setVisible(False)
        self.git_status_label.clear()
        
        # Clear release output
        if hasattr(self, 'release_output'):
            self.release_output.clear()
            
    def _infer_repository_info(self, repo_path: Path):
        """Try to infer repository information from the selected directory."""
        try:
            # Try to get remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.git_url.setText(result.stdout.strip())
            
            # Try to get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            if result.returncode == 0 and result.stdout.strip():
                branch = result.stdout.strip()
                # For AUR repositories, always use master
                if "aur.archlinux.org" in self.git_url.text():
                    branch = "master"
                self.git_branch.setText(branch)
            
            # Check for corresponding AUR package
            repo_name = repo_path.name
            aur_base = repo_path.parent / "aur-packages"
            potential_aur_paths = [
                aur_base / repo_name,
                aur_base / f"{repo_name}-git",
                aur_base / f"{repo_name}-bin",
                Path.home() / "Code" / "aur-packages" / repo_name,
                Path.home() / "Code" / "aur-packages" / f"{repo_name}-git",
                Path.home() / "Code" / "aur-packages" / f"{repo_name}-bin"
            ]
            
            # Clear AUR info by default
            self.aur_path.clear()
            self.aur_url.clear()
            self.settings.remove("aur_url")
            self.settings.remove("aur_path")
            
            # Try to find AUR package
            for aur_path in potential_aur_paths:
                if aur_path.exists() and (aur_path / ".git").exists():
                    # Found AUR package directory
                    self.aur_path.setText(str(aur_path))
                    self.settings.setValue("aur_path", str(aur_path))
                    
                    # Try to get AUR remote URL
                    try:
                        result = subprocess.run(
                            ["git", "remote", "get-url", "origin"],
                            cwd=aur_path,
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        aur_url = result.stdout.strip()
                        if "aur.archlinux.org" in aur_url:
                            self.aur_url.setText(aur_url)
                            self.settings.setValue("aur_url", aur_url)
                    except subprocess.CalledProcessError:
                        pass
                    break
            
            # Check Git status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            if result.stdout.strip():
                self.git_status_label.setText("Repository has uncommitted changes")
                self.git_status_label.setStyleSheet("color: #FFA500;")  # Orange for warning
            else:
                self.git_status_label.setText("Repository is clean")
                self.git_status_label.setStyleSheet("color: #4CAF50;")  # Green for good
                
        except subprocess.CalledProcessError:
            self.git_status_label.setText("New repository - no commits yet")
            self.git_status_label.setStyleSheet("color: #666666;")  # Gray for info
            
    def _infer_version(self, repo_path: Path) -> str:
        """Try to infer version from package files."""
        try:
            latest_version = None
            
            # First try to get latest git tag
            result = subprocess.run(
                ["git", "tag", "-l", "v*"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                # Get all version tags and sort them
                version_tags = [tag.lstrip('v') for tag in result.stdout.strip().split('\n')]
                version_tags.sort(key=lambda v: [int(x) for x in v.split('.')])
                if version_tags:
                    latest_version = version_tags[-1]
            
            # If no git tags, check PKGBUILD
            if not latest_version:
                pkgbuild = repo_path / "PKGBUILD"
                if pkgbuild.exists():
                    content = pkgbuild.read_text()
                    match = re.search(r'pkgver=([0-9][0-9a-z.-]*)', content)
                    if match:
                        latest_version = match.group(1)
            
            # If still no version, check other common files
            if not latest_version:
                version_files = [
                    (repo_path / "pyproject.toml", r'version\s*=\s*["\']([^"\']+)["\']'),
                    (repo_path / "package.json", r'"version":\s*"([^"]+)"'),
                    (repo_path / "Cargo.toml", r'version\s*=\s*"([^"]+)"')
                ]
                
                for file_path, pattern in version_files:
                    if file_path.exists():
                        content = file_path.read_text()
                        match = re.search(pattern, content)
                        if match:
                            latest_version = match.group(1)
                            break
            
            # If we found a version, increment the patch number
            if latest_version:
                try:
                    # Split version into parts
                    parts = latest_version.split('.')
                    if len(parts) >= 3:
                        # Increment patch version
                        parts[-1] = str(int(parts[-1]) + 1)
                    elif len(parts) == 2:
                        # Add patch version
                        parts.append('1')
                    elif len(parts) == 1:
                        # Add minor and patch version
                        parts.extend(['0', '1'])
                    return '.'.join(parts)
                except ValueError:
                    # If version parsing fails, return the version as is
                    return latest_version
            
            # Default to 0.1.0 if no version found
            return "0.1.0"
                
        except Exception as e:
            print(f"Version inference error: {e}")
            return "0.1.0"

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

    def init_git_repo(self):
        """Initialize a new Git repository."""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Error", "Please select a directory first")
            return
            
        try:
            repo_path = self.git_repo_path.text()
            
            # Initialize Git repository if not already initialized
            if not os.path.exists(os.path.join(repo_path, '.git')):
                subprocess.run(
                    ["git", "init"],
                    cwd=repo_path,
                    check=True
                )
                QMessageBox.information(self, "Success", "Git repository initialized")
                
                # Update UI state
                self._update_git_buttons()
                self.update_git_info()
            else:
                QMessageBox.information(self, "Info", "Git repository already initialized")
                
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize Git repository: {e.stderr}")
            
    def create_branch(self):
        """Create a new Git branch."""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Error", "Please select a Git repository first")
            return
            
        branch_name = self.git_branch.text().strip()
        if not branch_name:
            QMessageBox.warning(self, "Error", "Please enter a branch name")
            return
            
        try:
            # Create and checkout new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.git_repo_path.text(),
                check=True
            )
            
            QMessageBox.information(self, "Success", f"Created and switched to branch '{branch_name}'")
            self.update_git_info()
            
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to create branch: {e.stderr}")
            
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
            branch = self.git_branch.text().strip()
            if branch:
                try:
                    # Try to set upstream tracking
                    subprocess.run(
                        ["git", "branch", "--set-upstream-to=origin/" + branch, branch],
                        cwd=self.git_repo_path.text(),
                        check=True
                    )
                except subprocess.CalledProcessError:
                    # If upstream doesn't exist, push and set upstream
                    if QMessageBox.question(
                        self,
                        "Push Branch?",
                        f"Branch '{branch}' doesn't exist on remote. Would you like to push it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    ) == QMessageBox.StandardButton.Yes:
                        subprocess.run(
                            ["git", "push", "-u", "origin", branch],
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

        if hasattr(self, 'sequester_widget') and self.sequester_widget:
            self.sequester_widget.refresh_untracked_files()

    def browse_aur_dir(self):
        """Browse for AUR package directory."""
        repo_name = Path(self.git_repo_path.text()).name if self.git_repo_path.text() else ""
        if not repo_name:
            QMessageBox.warning(self, "Error", "Please select a repository first")
            return
            
        # Check for existing AUR path first
        start_dir = self.aur_path.text() or self.settings.value("aur_path")
        
        # If no existing path, suggest creating in aur-packages
        if not start_dir and repo_name:
            suggested_paths = [
                Path(self.git_repo_path.text()).parent / "aur-packages",
                Path.home() / "Code" / "aur-packages"
            ]
            
            for path in suggested_paths:
                if path.exists():
                    start_dir = str(path)
                    break
                    
            if not start_dir:
                # Ask user if they want to create aur-packages directory
                reply = QMessageBox.question(
                    self,
                    "Create AUR Directory?",
                    "No AUR packages directory found. Would you like to create one?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    parent_dir = Path(self.git_repo_path.text()).parent
                    aur_dir = parent_dir / "aur-packages"
                    try:
                        aur_dir.mkdir(parents=True, exist_ok=True)
                        start_dir = str(aur_dir)
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to create directory: {e}")
                        return
                else:
                    start_dir = QDir.homePath()
        
        if not start_dir:
            start_dir = QDir.homePath()
            
        aur_dir = QFileDialog.getExistingDirectory(
            self, "Select AUR Package Directory",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if aur_dir:
            # Check if selected directory is for AUR package
            aur_path = Path(aur_dir)
            if not (aur_path / ".git").exists():
                # Ask to create new AUR package
                reply = QMessageBox.question(
                    self,
                    "Initialize AUR Package?",
                    "Selected directory is not a Git repository. Would you like to initialize it as an AUR package?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        # Initialize Git repository
                        import subprocess
                        subprocess.run(["git", "init"], cwd=aur_dir, check=True)
                        
                        # Set up AUR remote
                        package_name = repo_name.lower()
                        aur_remote = f"ssh://aur@aur.archlinux.org/{package_name}.git"
                        
                        # Ask user to confirm/modify package name
                        from PyQt6.QtWidgets import QInputDialog
                        package_name, ok = QInputDialog.getText(
                            self,
                            "AUR Package Name",
                            "Enter AUR package name:",
                            text=package_name
                        )
                        
                        if ok and package_name:
                            aur_remote = f"ssh://aur@aur.archlinux.org/{package_name}.git"
                            subprocess.run(
                                ["git", "remote", "add", "origin", aur_remote],
                                cwd=aur_dir,
                                check=True
                            )
                            
                            # Update UI
                            self.aur_url.setText(aur_remote)
                            self.settings.setValue("aur_url", aur_remote)
                            
                    except subprocess.CalledProcessError as e:
                        QMessageBox.critical(self, "Error", f"Failed to initialize AUR package: {e.stderr}")
                        return
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to initialize AUR package: {e}")
                        return
            
            self.aur_path.setText(aur_dir)
            self.settings.setValue("aur_path", aur_dir)

    def update_release_progress(self, message: str):
        """Update release progress in ReleaseManager."""
        if hasattr(self, 'release_manager_widget'):
            self.release_manager_widget.progress.emit(message)
            
    def handle_release_error(self, error_msg: str):
        """Handle release errors from ReleaseManager."""
        QMessageBox.critical(self, "Error", f"Release failed: {error_msg}")
        
    def release_finished(self, success: bool):
        """Handle release completion from ReleaseManager."""
        if success:
            QMessageBox.information(self, "Success", "Release process completed successfully!")
            
    def handle_release_dialog(self, title: str, message: str, options: list):
        """Handle dialog requests from ReleaseManager."""
        if hasattr(self, 'release_manager_widget'):
            self.release_manager_widget.handle_dialog_response(
                self.release_manager_widget.dialog_signal.emit(title, message, options)
            )

    def infer_version(self):
        """Infer version from repository."""
        if not self.git_repo_path.text():
            QMessageBox.critical(self, "Error", "No Git repository selected")
            return
            
        version = self._infer_version(Path(self.git_repo_path.text()))
        if version:
            self.version_input.setText(version)
        else:
            QMessageBox.warning(self, "Warning", "Could not infer version from repository")

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

    def select_storage_path(self):
        """Open dialog to select storage location."""
        storage_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Storage Location",
            self.git_storage_path.text() or str(Path.home())
        )
        if storage_dir:
            self.git_storage_path.setText(storage_dir)
            self.settings.setValue("git_storage_path", storage_dir)
            
            # Create repo-specific subdirectory
            if self.git_repo_path.text():
                repo_name = Path(self.git_repo_path.text()).name
                repo_storage = Path(storage_dir) / repo_name
                repo_storage.mkdir(parents=True, exist_ok=True)
                
                # Update manager paths
                self.git_manager.set_output_path(repo_storage)
                self.sequester_path_changed.emit(str(repo_storage))
                self.artifacts_path_changed.emit(str(repo_storage))

    def generate_aur_url(self):
        """Generate AUR URL based on repository name."""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Error", "Please select a repository first")
            return
            
        repo_name = Path(self.git_repo_path.text()).name.lower()
        
        # Ask user to confirm/modify package name
        from PyQt6.QtWidgets import QInputDialog
        package_name, ok = QInputDialog.getText(
            self,
            "AUR Package Name",
            "Enter AUR package name:",
            text=repo_name
        )
        
        if ok and package_name:
            aur_url = f"ssh://aur@aur.archlinux.org/{package_name}.git"
            self.aur_url.setText(aur_url)
            self.settings.setValue("aur_url", aur_url)

    def create_aur_package(self):
        """Create a new AUR package directory."""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Error", "Please select a repository first")
            return
            
        repo_name = Path(self.git_repo_path.text()).name
        
        # Suggest aur-packages directory locations
        suggested_paths = [
            Path(self.git_repo_path.text()).parent / "aur-packages",
            Path.home() / "Code" / "aur-packages"
        ]
        
        # Find or create aur-packages directory
        aur_base = None
        for path in suggested_paths:
            if path.exists():
                aur_base = path
                break
                
        if not aur_base:
            reply = QMessageBox.question(
                self,
                "Create AUR Directory?",
                "No AUR packages directory found. Would you like to create one?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                aur_base = suggested_paths[0]  # Use first suggestion
                try:
                    aur_base.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create directory: {e}")
                    return
            else:
                return
                
        # Get package name from user
        from PyQt6.QtWidgets import QInputDialog
        package_name, ok = QInputDialog.getText(
            self,
            "AUR Package Name",
            "Enter AUR package name:",
            text=repo_name.lower()
        )
        
        if ok and package_name:
            # Create package directory
            aur_path = aur_base / package_name
            try:
                aur_path.mkdir(parents=True, exist_ok=True)
                
                # Initialize Git repository
                subprocess.run(["git", "init"], cwd=aur_path, check=True)
                
                # Set up AUR remote
                aur_url = f"ssh://aur@aur.archlinux.org/{package_name}.git"
                subprocess.run(
                    ["git", "remote", "add", "origin", aur_url],
                    cwd=aur_path,
                    check=True
                )
                
                # Update UI
                self.aur_path.setText(str(aur_path))
                self.aur_url.setText(aur_url)
                self.settings.setValue("aur_path", str(aur_path))
                self.settings.setValue("aur_url", aur_url)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Created AUR package directory: {aur_path}\nRemote URL: {aur_url}"
                )
                
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self, "Error", f"Failed to initialize AUR package: {e.stderr}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create AUR package: {e}") 

    def update_repo_status(self):
        """Update repository status indicator and info."""
        repo_path = Path(self.git_repo_path.text())
        is_valid = False
        info_text = []
        
        try:
            # Check if it's a Git repository
            git_dir = repo_path / '.git'
            is_valid = (git_dir.is_dir() or 
                       (git_dir.is_file() and 'gitdir:' in git_dir.read_text()))
            
            if is_valid:
                # Get repository type
                if git_dir.is_file():
                    info_text.append("Type: Git Submodule")
                else:
                    info_text.append("Type: Git Repository")
                
                # Get and set remote URL
                try:
                    result = subprocess.run(
                        ['git', 'remote', 'get-url', 'origin'],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    remote_url = result.stdout.strip()
                    self.git_url.setText(remote_url)
                    
                    # If this is varchiver, try to detect AUR package
                    if repo_path.name == "varchiver":
                        # Set AUR URL
                        aur_url = "ssh://aur@aur.archlinux.org/varchiver.git"
                        self.aur_url.setText(aur_url)
                        
                        # Try to find AUR package directory
                        possible_aur_paths = [
                            Path.home() / "Code" / "aur-packages" / "varchiver",
                            Path.home() / "aur-packages" / "varchiver",
                            repo_path.parent / "aur-packages" / "varchiver"
                        ]
                        
                        for aur_path in possible_aur_paths:
                            if aur_path.exists() and (aur_path / '.git').exists():
                                self.aur_path.setText(str(aur_path))
                                info_text.append(f"\nAUR Package: {aur_path}")
                                break
                
                except subprocess.CalledProcessError:
                    pass
                
                # Get current branch
                try:
                    result = subprocess.run(
                        ['git', 'branch', '--show-current'],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    current_branch = result.stdout.strip()
                    if current_branch:  # Only update if we got a valid branch name
                        self.git_branch.setText(current_branch)
                        info_text.append(f"Branch: {current_branch}")
                except subprocess.CalledProcessError:
                    pass
                
                # Check for nested repositories
                nested_repos = self._find_nested_repos(repo_path)
                if nested_repos:
                    info_text.append("\nNested Repositories:")
                    for repo in nested_repos:
                        info_text.append(f"- {repo.relative_to(repo_path)}")
                
                # Check for submodules
                submodules = self._get_submodules(repo_path)
                if submodules:
                    info_text.append("\nSubmodules:")
                    for name, data in submodules.items():
                        status = "✓" if data['initialized'] else "✗"
                        info_text.append(f"- {name} [{status}]")
        
        except Exception as e:
            info_text.append(f"Error: {str(e)}")
        
        # Update UI
        self.repo_status_indicator.setProperty("valid", is_valid)
        self.repo_status_indicator.style().unpolish(self.repo_status_indicator)
        self.repo_status_indicator.style().polish(self.repo_status_indicator)
        
        self.repo_info.setText("\n".join(info_text))

    def _find_nested_repos(self, root_path: Path) -> List[Path]:
        """Find all nested Git repositories."""
        nested_repos = []
        
        for root, dirs, _ in os.walk(root_path):
            root_path = Path(root)
            
            # Skip the root repository itself
            if root_path == root_path:
                continue
            
            # Skip .git directories
            if '.git' in dirs:
                dirs.remove('.git')
            
            # Check each directory for a Git repository
            for dir_name in dirs[:]:  # Copy list as we'll modify it
                dir_path = root_path / dir_name
                git_dir = dir_path / '.git'
                
                # Check if it's a Git repository
                if git_dir.is_dir() or (git_dir.is_file() and 'gitdir:' in git_dir.read_text()):
                    nested_repos.append(dir_path)
                    # Don't descend into Git repositories
                    dirs.remove(dir_name)
        
        return nested_repos

    def _get_submodules(self, repo_path: Path) -> Dict[str, Dict]:
        """Get information about Git submodules."""
        submodules = {}
        gitmodules_path = repo_path / '.gitmodules'
        
        if gitmodules_path.exists():
            try:
                # Parse .gitmodules file
                import configparser
                config = configparser.ConfigParser()
                config.read(gitmodules_path)
                
                for section in config.sections():
                    if section.startswith('submodule'):
                        name = section.split('"')[1]
                        path = config.get(section, 'path')
                        submodule_path = repo_path / path
                        
                        # Get submodule status
                        initialized = False
                        if submodule_path.exists():
                            git_file = submodule_path / '.git'
                            initialized = git_file.exists()
                        
                        submodules[name] = {
                            'path': path,
                            'url': config.get(section, 'url'),
                            'initialized': initialized,
                            'branch': config.get(section, 'branch', fallback=None)
                        }
            
            except Exception as e:
                print(f"Error reading .gitmodules: {e}")
        
        return submodules 

    def _update_release_manager_path(self):
        """Update release manager's project directory when git repo changes."""
        if hasattr(self, 'release_manager_widget'):
            self.release_manager_widget.project_dir = Path(self.git_repo_path.text()) if self.git_repo_path.text() else None 

    def toggle_compact_view(self, checked: bool):
        """Toggle between compact and normal view."""
        layout = self.layout()
        if checked:
            layout.setSpacing(2)
            layout.setContentsMargins(2, 2, 2, 2)
        else:
            layout.setSpacing(6)
            layout.setContentsMargins(6, 6, 6, 6)
        self.adjustSize()

    def commit_changes(self):
        """Commit changes with the entered message."""
        if not self.git_repo_path.text():
            QMessageBox.warning(self, "Error", "Please select a Git repository first")
            return
            
        message = self.commit_message.text().strip()
        if not message:
            QMessageBox.warning(self, "Error", "Please enter a commit message")
            return
            
        try:
            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.git_repo_path.text(),
                capture_output=True,
                text=True,
                check=True
            )
            
            if not result.stdout.strip():
                QMessageBox.information(self, "Info", "No changes to commit")
                return
                
            # Show changes to be committed
            changes = result.stdout.strip()
            reply = QMessageBox.question(
                self,
                "Confirm Commit",
                f"The following changes will be committed:\n\n{changes}\n\nProceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Add all changes and commit
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=self.git_repo_path.text(),
                    check=True
                )
                
                subprocess.run(
                    ["git", "commit", "-m", message],
                    cwd=self.git_repo_path.text(),
                    check=True
                )
                
                QMessageBox.information(self, "Success", "Changes committed successfully")
                self.commit_message.clear()
                self.update_repo_status()
                
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to commit changes: {e.stderr}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during commit: {str(e)}") 