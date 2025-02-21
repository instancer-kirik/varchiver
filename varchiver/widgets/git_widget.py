"""Git functionality widget for managing Git repositories."""

from pathlib import Path
import os
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QMessageBox, QFileDialog, QGroupBox, QTabWidget,
    QTextEdit, QFormLayout, QComboBox, QListWidget, QProgressBar,
    QDialog, QDialogButtonBox, QScrollArea, QTreeWidget, QTreeWidgetItem,
    QCheckBox
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
        self.repo_info = QLabel()  # Add repository info label
        self.repo_info.setWordWrap(True)
        self.git_manager = GitManager()
        
        # Initialize managers
        self.git_config_manager = None
        self.release_manager = None
        self.sequester_widget = None  # Add sequester widget initialization
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the Git UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)  # Reduce default spacing
        
        # Add compact view toggle button in the top-right
        compact_layout = QHBoxLayout()
        compact_layout.addStretch()
        self.compact_btn = QPushButton("Compact")
        self.compact_btn.setCheckable(True)
        self.compact_btn.clicked.connect(self.toggle_compact_view)
        self.compact_btn.setFixedWidth(70)
        compact_layout.addWidget(self.compact_btn)
        layout.addLayout(compact_layout)
        
        # Left side: Repository settings and info
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(4)
        
        # Repository settings group
        repo_group = QGroupBox("Repository Settings")
        repo_layout = QFormLayout()
        repo_layout.setSpacing(4)
        
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
        
        # Add quick access button for varchiver
        varchiver_btn = QPushButton("varchiver/")
        varchiver_btn.setToolTip("Quick access to varchiver project")
        varchiver_btn.clicked.connect(self.select_varchiver_project)
        repo_path_layout.addWidget(varchiver_btn)
        
        repo_layout.addRow("Local Path:", repo_path_layout)
        
        # Git URL input
        git_url_layout = QHBoxLayout()
        git_url_layout.addWidget(self.git_url)
        repo_layout.addRow("Git URL:", git_url_layout)
        
        # Git storage path
        storage_layout = QHBoxLayout()
        storage_layout.addWidget(self.git_storage_path)
        storage_browse_btn = QPushButton("Browse")
        storage_browse_btn.clicked.connect(self.select_git_storage)
        storage_layout.addWidget(storage_browse_btn)
        repo_layout.addRow("Storage Path:", storage_layout)
        
        # AUR URL and path
        aur_url_layout = QHBoxLayout()
        aur_url_layout.addWidget(self.aur_url)
        repo_layout.addRow("AUR URL:", aur_url_layout)
        
        aur_path_layout = QHBoxLayout()
        aur_path_layout.addWidget(self.aur_path)
        aur_browse_btn = QPushButton("Browse")
        aur_browse_btn.clicked.connect(self.browse_aur_dir)
        aur_path_layout.addWidget(aur_browse_btn)
        repo_layout.addRow("AUR Path:", aur_path_layout)
        
        # Git branch
        branch_layout = QHBoxLayout()
        branch_layout.addWidget(self.git_branch)
        repo_layout.addRow("Branch:", branch_layout)
        
        # Commit message input with reduced height
        commit_layout = QHBoxLayout()
        self.commit_message = QLineEdit()
        self.commit_message.setPlaceholderText("Enter commit message...")
        commit_btn = QPushButton("Commit")
        commit_btn.clicked.connect(self.commit_changes)
        commit_layout.addWidget(self.commit_message)
        commit_layout.addWidget(commit_btn)
        repo_layout.addRow("Commit:", commit_layout)
        
        repo_group.setLayout(repo_layout)
        left_layout.addWidget(repo_group)
        
        # Repository info
        info_group = QGroupBox("Repository Info")
        info_layout = QVBoxLayout()
        info_layout.addWidget(self.repo_info)
        info_group.setLayout(info_layout)
        left_layout.addWidget(info_group)
        
        # Create main horizontal layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_widget, 1)  # Left side takes 1 part
        
        # Right side: Tabs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Create tab widget with reduced spacing
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)  # More compact tabs
        
        # Git Config tab
        self.git_config_container = QWidget()
        self.git_config_container.setLayout(QVBoxLayout())
        self.tab_widget.addTab(self.git_config_container, "Git Config")
        
        # Release Manager tab
        self.release_manager_widget = ReleaseManager()
        self.tab_widget.addTab(self.release_manager_widget, "Release Manager")
        
        # Git Sequester tab
        if self.git_repo_path.text():
            self.sequester_widget = GitSequester(self.git_repo_path.text())
            if self.git_storage_path.text():
                self.sequester_widget.set_storage_path(self.git_storage_path.text())
            self.tab_widget.addTab(self.sequester_widget, "Git Sequester")
        
        right_layout.addWidget(self.tab_widget)
        main_layout.addWidget(right_widget, 2)  # Right side takes 2 parts
        
        layout.addLayout(main_layout)
        
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
                
                # Try to infer version for release manager
                version = self._infer_version(repo_path)
                if version and hasattr(self.release_manager_widget, 'version_input'):
                    self.release_manager_widget.version_input.setText(version)
                    
                # Force update of task selection
                self.release_manager_widget.task_preset.setCurrentIndex(0)
                self.release_manager_widget.update_task_selection(0)
                
                # Update project path in release manager
                self._update_release_manager_path()
            
            # Update Git Sequester
            if self.sequester_widget:
                self.tab_widget.removeTab(self.tab_widget.indexOf(self.sequester_widget))
                self.sequester_widget.deleteLater()
            self.sequester_widget = GitSequester(str(repo_path))
            if self.git_storage_path.text():
                self.sequester_widget.set_storage_path(self.git_storage_path.text())
            self.tab_widget.addTab(self.sequester_widget, "Git Sequester")

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
            
            # First check PKGBUILD
            pkgbuild = repo_path / "PKGBUILD"
            if pkgbuild.exists():
                content = pkgbuild.read_text()
                match = re.search(r'pkgver=([0-9][0-9a-z.-]*)', content)
                if match:
                    latest_version = match.group(1)
            
            # Then check other common files
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
            
            # Finally try git tags
            if not latest_version:
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
        """Open dialog to select AUR package directory."""
        aur_dir = QFileDialog.getExistingDirectory(
            self,
            "Select AUR Package Directory",
            self.aur_path.text() or str(Path.home() / "Code" / "aur-packages")
        )
        if aur_dir:
            self.aur_path.setText(aur_dir)
            self.settings.setValue("aur_path", aur_dir)
            
            # Try to infer AUR URL from directory
            if Path(aur_dir).exists():
                try:
                    result = subprocess.run(
                        ["git", "remote", "get-url", "origin"],
                        cwd=aur_dir,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0 and "aur.archlinux.org" in result.stdout:
                        self.aur_url.setText(result.stdout.strip())
                        self.settings.setValue("aur_url", result.stdout.strip())
                except Exception:
                    pass

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
        """Open dialog to select Git storage path."""
        storage_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Git Storage Directory",
            self.git_storage_path.text() or str(Path.home())
        )
        if storage_dir:
            self.git_storage_path.setText(storage_dir)
            self.settings.setValue("git_storage_path", storage_dir)
            self.sequester_path_changed.emit(storage_dir)
            
            # Update sequester storage path
            if self.sequester_widget:
                self.sequester_widget.set_storage_path(storage_dir)

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
            repo_path = Path(self.git_repo_path.text()) if self.git_repo_path.text() else None
            if repo_path and repo_path.exists():
                self.release_manager_widget.project_dir = repo_path
                self.release_manager_widget.project_dir_input.setText(str(repo_path))
                # Force update of task selection
                self.release_manager_widget.task_preset.setCurrentIndex(0)
                self.release_manager_widget.update_task_selection(0)
                # Try to infer version
                version = self._infer_version(repo_path)
                if version and hasattr(self.release_manager_widget, 'version_input'):
                    self.release_manager_widget.version_input.setText(version)

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

    def select_varchiver_project(self):
        """Quick access to select the varchiver project."""
        # Common locations to check for varchiver
        possible_paths = [
            Path.home() / "Code" / "varchiver",
            Path.home() / "Projects" / "varchiver",
            Path.home() / "git" / "varchiver",
            Path("/opt/varchiver"),
        ]
        
        for path in possible_paths:
            if path.exists() and (path / '.git').exists():
                self.git_repo_path.setText(str(path))
                # Set default storage path based on repository
                default_storage = path.parent / ".varchiver" / "git_archives"
                self.git_storage_path.setText(str(default_storage))
                
                # Update repository info and status
                self._infer_repository_info(path)
                self.update_repo_status()
                
                # Update release manager
                if hasattr(self, 'release_manager_widget'):
                    self.release_manager_widget.project_dir_input.setText(str(path))
                    self.release_manager_widget.project_dir = path
                    # Set task preset to "Full Release (All Tasks)"
                    self.release_manager_widget.task_preset.setCurrentIndex(0)
                    self.release_manager_widget.update_task_selection(0)
                    
                    # Try to infer version for release manager
                    version = self._infer_version(path)
                    if version and hasattr(self.release_manager_widget, 'version_input'):
                        self.release_manager_widget.version_input.setText(version)
                return
                
        # If not found, show error
        QMessageBox.warning(
            self,
            "Project Not Found",
            "Could not find varchiver project in common locations.\nPlease use Browse to locate it manually."
        ) 

    def handle_untracked_files(self, untracked_files):
        """Handle untracked files by offering to add them to .gitignore"""
        if not untracked_files:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Untracked Files")
        layout = QVBoxLayout(dialog)
        
        # Add description
        desc = QLabel("The following files are untracked. Select files to add to .gitignore:")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Add file list with checkboxes
        file_list = QTreeWidget()
        file_list.setHeaderLabels(["File", "Pattern"])
        file_list.setSelectionMode(QTreeWidget.SelectionMode.MultiSelection)
        
        for file_path in untracked_files:
            item = QTreeWidgetItem(file_list)
            item.setText(0, file_path)
            # Suggest gitignore pattern
            pattern = f"/{file_path}" if "/" not in file_path else file_path
            item.setText(1, pattern)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)
        
        layout.addWidget(file_list)
        
        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get selected patterns
            patterns = []
            for i in range(file_list.topLevelItemCount()):
                item = file_list.topLevelItem(i)
                if item.checkState(0) == Qt.CheckState.Checked:
                    patterns.append(item.text(1))
            
            if patterns:
                # Add patterns to .gitignore
                gitignore_path = Path(self.git_repo_path.text()) / ".gitignore"
                try:
                    # Create .gitignore if it doesn't exist
                    if not gitignore_path.exists():
                        gitignore_path.touch()
                    
                    # Read existing content
                    content = gitignore_path.read_text() if gitignore_path.exists() else ""
                    
                    # Add new patterns
                    if content and not content.endswith('\n'):
                        content += '\n'
                    content += '\n'.join(patterns) + '\n'
                    
                    # Write back
                    gitignore_path.write_text(content)
                    
                    QMessageBox.information(self, "Success", 
                        f"Added {len(patterns)} pattern(s) to .gitignore")
                        
                    # Refresh repository status
                    self.update_repo_status()
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", 
                        f"Failed to update .gitignore: {str(e)}")

    def update_task_selection(self, index):
        """Update task selection in ReleaseManager."""
        if hasattr(self, 'release_manager_widget'):
            self.release_manager_widget.task_preset.setCurrentIndex(index)
            self.release_manager_widget.update_task_selection(index) 

    def _check_git_status(self, cwd=None):
        """Check Git status and handle untracked files."""
        try:
            # Check for untracked files
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=cwd or self.git_repo_path.text(),
                capture_output=True,
                text=True,
                check=True
            )
            
            untracked_files = [f for f in result.stdout.splitlines() if f.strip()]
            
            if untracked_files:
                reply = QMessageBox.question(
                    self,
                    "Untracked Files Found",
                    f"Found {len(untracked_files)} untracked files. Would you like to add them to .gitignore?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.handle_untracked_files(untracked_files)
            
            # Check for changes in tracked files
            result = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=cwd or self.git_repo_path.text(),
                capture_output=True,
                text=True,
                check=True
            )
            
            return result.stdout.strip()
            
        except subprocess.CalledProcessError as e:
            self.git_error_text.setText(f"Git status check failed: {e.stderr}")
            self.git_error_text.setVisible(True)
            return None
        except Exception as e:
            self.git_error_text.setText(f"Error checking Git status: {str(e)}")
            self.git_error_text.setVisible(True)
            return None 