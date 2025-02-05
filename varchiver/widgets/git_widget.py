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
        self.default_storage_path = self.settings.value("git_storage_path") or str(Path.home() / ".varchiver" / "git_archives")
        self.default_git_url = self.settings.value("git_url") or "https://github.com/username/repo.git"
        self.default_aur_url = self.settings.value("aur_url") or "ssh://aur@aur.archlinux.org/package-name.git"
        
        # Initialize UI elements
        self.git_repo_path = QLineEdit(self.default_repo_path)
        self.git_storage_path = QLineEdit(self.default_storage_path)
        self.git_url = QLineEdit(self.default_git_url)
        self.aur_url = QLineEdit(self.default_aur_url)
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
        
        remote_btn_layout = QHBoxLayout()
        init_repo_btn = QPushButton("Initialize Git")
        init_repo_btn.clicked.connect(self.init_git_repo)
        remote_btn_layout.addWidget(init_repo_btn)
        
        add_remote_btn = QPushButton("Add/Update Remote")
        add_remote_btn.clicked.connect(self.add_git_remote)
        remote_btn_layout.addWidget(add_remote_btn)
        
        url_layout.addLayout(remote_btn_layout)
        paths_layout.addRow("Git URL:", url_layout)
        
        # AUR URL and controls
        aur_layout = QHBoxLayout()
        aur_layout.addWidget(self.aur_url)
        
        # Add buttons for AUR URL
        aur_url_btn = QPushButton("Generate URL")
        aur_url_btn.clicked.connect(self.generate_aur_url)
        aur_layout.addWidget(aur_url_btn)
        
        paths_layout.addRow("AUR URL:", aur_layout)
        
        # Branch selection with create option
        branch_layout = QHBoxLayout()
        branch_layout.addWidget(self.git_branch)
        create_branch_btn = QPushButton("Create Branch")
        create_branch_btn.clicked.connect(self.create_branch)
        branch_layout.addWidget(create_branch_btn)
        paths_layout.addRow("Branch:", branch_layout)
        
        # Repository path selection
        repo_layout = QHBoxLayout()
        repo_layout.addWidget(self.git_repo_path)
        browse_repo_btn = QPushButton("Browse")
        browse_repo_btn.clicked.connect(self.select_git_repo)
        repo_layout.addWidget(browse_repo_btn)
        paths_layout.addRow("Local Path:", repo_layout)
        
        # Storage location (combines artifacts and git storage)
        storage_layout = QHBoxLayout()
        storage_layout.addWidget(self.git_storage_path)
        storage_browse = QPushButton("Browse")
        storage_browse.clicked.connect(self.select_git_storage)
        storage_layout.addWidget(storage_browse)
        paths_layout.addRow("Storage Path:", storage_layout)
        
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
        
        aur_btn_layout = QHBoxLayout()
        aur_browse = QPushButton("Browse")
        aur_browse.clicked.connect(self.browse_aur_dir)
        aur_btn_layout.addWidget(aur_browse)
        
        aur_create = QPushButton("Create New")
        aur_create.clicked.connect(self.create_aur_package)
        aur_btn_layout.addWidget(aur_create)
        
        aur_layout.addWidget(aur_label)
        aur_layout.addWidget(self.aur_path)
        aur_layout.addLayout(aur_btn_layout)
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
            # Reset UI state before loading new repo
            self._reset_ui_state()
            
            if self.git_manager.set_repository(repo_dir):
                self.git_repo_path.setText(repo_dir)
                self.repo_changed.emit(repo_dir)
                self.settings.setValue("project_path", repo_dir)
                
                # Initialize Git config manager
                self.init_git_config_manager(Path(repo_dir))
                
                # Try to infer repository information
                self._infer_repository_info(Path(repo_dir))
                
                # Update UI state
                self._update_git_buttons()
                self.refresh_untracked_files()
            else:
                QMessageBox.warning(self, "Error", "Selected directory is not a Git repository")
                
    def _reset_ui_state(self):
        """Reset UI state when switching repositories."""
        # Clear version input
        self.version_input.clear()
        
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
                text=True
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                # For AUR repositories, always use master
                if "aur.archlinux.org" in self.git_url.text():
                    branch = "master"
                self.git_branch.setText(branch)
            else:
                # Try to get default branch
                result = subprocess.run(
                    ["git", "symbolic-ref", "HEAD"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    branch = result.stdout.strip().replace('refs/heads/', '')
                    # For AUR repositories, always use master
                    if "aur.archlinux.org" in self.git_url.text():
                        branch = "master"
                    self.git_branch.setText(branch)
                else:
                    # Default to master for AUR, main for others
                    if "aur.archlinux.org" in self.git_url.text():
                        self.git_branch.setText("master")
                    else:
                        self.git_branch.setText("main")
            
            # Try to get version from package files
            version = self._infer_version(repo_path)
            if version:
                self.version_input.setText(version)
            
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
            # First check src directory for original version
            src_version_path = repo_path / "src" / f"{repo_path.name}-"
            if src_version_path.parent.exists():
                # Find directories matching the pattern
                version_dirs = [d for d in src_version_path.parent.glob(f"{repo_path.name}-*") if d.is_dir()]
                if version_dirs:
                    # Get the latest version directory
                    latest_dir = sorted(version_dirs)[-1]
                    version = latest_dir.name.replace(f"{repo_path.name}-", "")
                    return version
            
            # Check common version files
            version_files = [
                (repo_path / "PKGBUILD", r'pkgver=([0-9][0-9a-z.-]*)'),
                (repo_path / "pyproject.toml", r'version\s*=\s*["\']([^"\']+)["\']'),
                (repo_path / "package.json", r'"version":\s*"([^"]+)"'),
                (repo_path / "Cargo.toml", r'version\s*=\s*"([^"]+)"')
            ]
            
            import re
            for file_path, pattern in version_files:
                if file_path.exists():
                    content = file_path.read_text()
                    match = re.search(pattern, content)
                    if match:
                        return match.group(1)
            
            # Try to get latest git tag as fallback
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip().lstrip('v')
                
        except Exception as e:
            print(f"Version inference error: {e}")
            
        return ""

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

    def start_release_process(self):
        """Start the release process."""
        try:
            # Get current repository path
            repo_path = Path(self.git_repo_path.text())
            if not repo_path.exists():
                raise RuntimeError("Repository path not found")

            # Get version
            version = self.version_input.text().strip()
            if not version:
                raise RuntimeError("Version number required")

            # Get AUR path if available
            aur_path = self.aur_path.text().strip()

            # Initialize release manager if not exists
            if not hasattr(self, 'release_manager') or self.release_manager is None:
                self.release_manager = ReleaseManager(parent=self)
                self.release_manager.setWindowTitle("Release Manager")
                self.release_manager.setWindowFlags(self.release_manager.windowFlags() | Qt.WindowType.Window)

            # Configure release manager with current repository and version
            self.release_manager.project_dir = repo_path
            self.release_manager.version_input.setText(version)
            
            # Determine tasks based on configuration
            tasks = ["update_version", "build", "create_release"]
            if aur_path:
                tasks.append("update_aur")
                self.release_manager.aur_path.setText(aur_path)

            # Set tasks in combo box
            task_index = 0  # Default to all tasks
            if not aur_path:
                task_index = 1  # Skip AUR update
            self.release_manager.task_combo.setCurrentIndex(task_index)

            # Show the release manager window
            self.release_manager.show()
            self.release_manager.raise_()
            self.release_manager.activateWindow()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start release process: {str(e)}")

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