print("Loading release_manager module")

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLineEdit, QLabel, QComboBox, QProgressBar, QMessageBox, QDialog,
                            QFileDialog, QGroupBox, QFormLayout, QTextEdit, QApplication)
from PyQt6.QtCore import QThread, pyqtSignal, QSettings, pyqtSlot, QDir, QMetaObject, Qt, Q_ARG
from PyQt6.QtGui import QTextCursor
import subprocess
import os
import re
from pathlib import Path
import time
from typing import List, Optional
from .project_constants import PROJECT_CONFIGS

print("Imports completed in release_manager module")

class ReleaseThread(QThread):
    # Define signals
    progress = pyqtSignal(str)
    output = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal(bool)
    dialog_signal = pyqtSignal(str, str, list)  # title, message, options
    
    def __init__(self, project_dir: Path, version: str, tasks: List[str], output_widget: QTextEdit, 
                 use_aur: bool = False, aur_dir: Optional[Path] = None):
        super().__init__()
        # Initialize basic attributes
        self.project_dir = project_dir
        self.version = version
        self.tasks = tasks
        self.output_widget = output_widget
        self.use_aur = use_aur
        self.aur_dir = aur_dir
        
        # Dialog control
        self.wait_for_dialog = False
        self.dialog_response = None
        self.stashed = False
        
        # Set up logging
        try:
            self.log_dir = project_dir / "logs"
            self.log_dir.mkdir(exist_ok=True)
            self.log_file = self.log_dir / f"release_{version}_{int(time.time())}.log"
        except Exception as e:
            print(f"Failed to set up logging: {e}")
            self.log_file = None
        
        # Git configuration
        self.git_branch = "master"
        self.url = self._get_git_url()
        
        # Version file patterns
        self.version_files = ['pyproject.toml', 'PKGBUILD']
        self.version_patterns = {
            'pyproject.toml': r'version\s*=\s*"[^"]*"',
            'PKGBUILD': r'^pkgver=[0-9][0-9a-zA-Z.-]*$'
        }

    def _get_git_url(self) -> Optional[str]:
        """Safely get git remote URL"""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()
            if remote_url.startswith("git@github.com:"):
                remote_url = remote_url.replace("git@github.com:", "https://github.com/")
            if remote_url.endswith(".git"):
                remote_url = remote_url[:-4]
            return remote_url
        except Exception as e:
            self.output_message(f"Warning: Failed to get Git remote URL: {e}")
            return None

    def output_message(self, message: str):
        """Thread-safe message output"""
        try:
            # Update widget through signal if needed
            if self.output_widget:
                QMetaObject.invokeMethod(self.output_widget, "append", 
                                       Qt.ConnectionType.QueuedConnection,
                                       Q_ARG(str, message))
                # Scroll to bottom
                QMetaObject.invokeMethod(self.output_widget, "moveCursor",
                                       Qt.ConnectionType.QueuedConnection,
                                       Q_ARG(QTextCursor.MoveOperation, QTextCursor.MoveOperation.End))
            
            # Write to log file
            if self.log_file:
                with open(self.log_file, 'a') as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
        except Exception as e:
            print(f"Error in output_message: {e}")

    def handle_dialog_response(self, response):
        """Handle dialog response in a thread-safe way"""
        self.dialog_response = response
        self.wait_for_dialog = False

    def run(self):
        """Main release process with improved error handling"""
        try:
            self.output_message(f"Starting release process for version {self.version}")
            
            # Check Git status first
            if not self._handle_git_status():
                return  # Git status handling failed or was cancelled
            
            try:
                # Update version files if needed
                if 'update_version' in self.tasks:
                    self._update_version_files()
                    self._commit_version_changes()
                
                # Build packages
                self._build_packages()
                
                # Create GitHub release if requested
                if 'create_release' in self.tasks:
                    self._check_github_authentication()
                    self._create_github_release()
                    
                # Update AUR if requested
                if 'update_aur' in self.tasks and self.use_aur and self.aur_dir:
                    self._update_aur()
                
                self.output_message("Release process completed successfully!")
                self.finished.emit(True)
                
            except Exception as e:
                self.output_message(f"Error during release process: {str(e)}")
                self.error.emit(str(e))
                self.finished.emit(False)
                
        finally:
            # Always try to restore stashed changes
            if self.stashed:
                try:
                    self._run_command(["git", "stash", "pop"])
                    self.output_message("Restored stashed changes")
                except Exception as e:
                    self.output_message(f"Warning: Failed to restore stashed changes: {e}")

    def _handle_git_status(self) -> bool:
        """Handle git status check and dialog interaction"""
        try:
            git_status = self._check_git_status()
            if not git_status:
                return True  # No changes, proceed
                
            self.output_message("\nWARNING: There are uncommitted changes:")
            self.output_message(git_status)
            
            # Show dialog and wait for response
            self.wait_for_dialog = True
            self.dialog_signal.emit(
                "Uncommitted Changes",
                "There are uncommitted changes. Choose an action:\n\n" +
                "1. Commit all changes\n" +
                "2. Stash changes (will restore after)\n" +
                "3. Cancel release",
                ["Commit", "Stash", "Cancel"]
            )
            
            # Wait for response with timeout
            start_time = time.time()
            while self.wait_for_dialog:
                if time.time() - start_time > 60:  # 1 minute timeout
                    self.output_message("Dialog timed out")
                    return False
                self.msleep(100)
                QApplication.processEvents()
            
            # Handle response
            if self.dialog_response == "Cancel":
                self.output_message("Release cancelled by user")
                self.finished.emit(False)
                return False
            
            try:
                if self.dialog_response == "Commit":
                    self._run_command(["git", "add", "-u"])
                    self._run_command(["git", "commit", "-m", "Pre-release changes"])
                elif self.dialog_response == "Stash":
                    self._run_command(["git", "stash", "save", "Pre-release stash"])
                    self.stashed = True
                return True
            except Exception as e:
                self.output_message(f"Failed to handle git changes: {e}")
                return False
                
        except Exception as e:
            self.output_message(f"Error checking git status: {e}")
            return False

    def _run_command(self, cmd, cwd=None, timeout=60, env=None, check=True):
        """Enhanced command runner with better error handling"""
        try:
            merged_env = os.environ.copy()
            if env:
                merged_env.update(env)
            
            self.output_message(f"Running: {' '.join(cmd)}")
            
            # Run command with timeout
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=merged_env,
                check=check
            )
            
            # Process output
            if result.stdout.strip():
                self.output_message(f"Output: {result.stdout.strip()}")
            if result.stderr.strip():
                self.output_message(f"Warnings: {result.stderr.strip()}")
                
            return result
            
        except subprocess.TimeoutExpired:
            self.output_message(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            raise
        except subprocess.CalledProcessError as e:
            self.output_message(f"Command failed with code {e.returncode}: {' '.join(cmd)}")
            if e.stdout:
                self.output_message(f"Output: {e.stdout}")
            if e.stderr:
                self.output_message(f"Error: {e.stderr}")
            raise
        except Exception as e:
            self.output_message(f"Failed to run command: {e}")
            raise

    def _check_git_status(self, cwd=None):
        """Check Git status, ignoring logs directory and other release artifacts"""
        try:
            # First check if logs directory is ignored
            gitignore_path = self.project_dir / ".gitignore"
            if not gitignore_path.exists() or "logs/" not in gitignore_path.read_text():
                self.output_message("Adding logs directory to .gitignore...")
                with open(gitignore_path, 'a') as f:
                    f.write("\n# Release logs\nlogs/\n")
                self._run_command(["git", "add", ".gitignore"])
                self._run_command(["git", "commit", "-m", "Add logs directory to .gitignore"])

            # Check status excluding logs directory
            status_result = self._run_command(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=cwd or self.project_dir
            )
            return status_result.stdout.strip()
        except Exception as e:
            self.output_message(f"Error checking Git status: {e}")
            raise

    def _commit_version_changes(self):
        """Commit version number changes."""
        try:
            # Check if there are changes to commit
            status_result = self._run_command(["git", "status", "--porcelain"])
            if status_result.stdout.strip():
                self.output_message("Committing version changes...")
                
                # Add changed files
                if not isinstance(self.version_files, list):
                    self.version_files = [str(f) for f in self.version_files]
                
                # Make sure all files exist before adding
                files_to_add = []
                for file_path in self.version_files:
                    if (self.project_dir / file_path).exists():
                        files_to_add.append(file_path)
                    else:
                        self.output_message(f"Warning: File not found: {file_path}")
                
                if not files_to_add:
                    raise Exception("No version files found to commit")
                
                self._run_command(["git", "add"] + files_to_add)
                
                # Commit changes
                commit_msg = f"Release v{self.version}"
                self._run_command(["git", "commit", "-m", commit_msg])
                
                self.output_message(f"Committed version changes for v{self.version}")
            else:
                self.output_message("No version changes to commit")

        except Exception as e:
            self.output_message(f"Warning: Failed to commit version changes: {str(e)}")
            raise

    def _update_version_files(self):
        self.progress.emit("Updating version in files...")
        
        for file_pattern in self.version_files:
            file_pattern = file_pattern.strip()
            if not file_pattern:
                continue
                
            # Handle absolute and relative paths correctly
            if Path(file_pattern).is_absolute():
                glob_pattern = file_pattern
            else:
                glob_pattern = str(self.project_dir / file_pattern)
                
            for file_path in Path(self.project_dir).glob(file_pattern):
                for pattern in self.version_patterns:
                    pattern = pattern.strip()
                    if not pattern:
                        continue
                    if "*" in pattern:
                        regex_pattern = pattern.replace("*", r"[^\"']*")
                        self._update_file_version(file_path, regex_pattern, pattern.replace("*", self.version))

    def _build_packages(self):
        """Build packages in a dedicated dist directory"""
        self.output_message("Starting package build process...")
        
        # First check if PKGBUILD exists
        pkgbuild_path = self.project_dir / "PKGBUILD"
        if not pkgbuild_path.exists():
            raise Exception("PKGBUILD not found in project directory")
            
        # Create dist directory if it doesn't exist
        dist_dir = self.project_dir / "dist"
        dist_dir.mkdir(exist_ok=True)
            
        # Clean up previous build artifacts
        self.output_message("Cleaning up previous build artifacts...")
        
        # Clean build directories and artifacts
        for d in ["pkg", "src", "dist"]:
            build_dir = self.project_dir / d
            if build_dir.exists():
                try:
                    import shutil
                    shutil.rmtree(build_dir)
                    self.output_message(f"Cleaned up {d} directory")
                except Exception as e:
                    self.output_message(f"Warning: Could not clean {d} directory: {e}")
                    continue
        
        # Create source archive
        self.output_message("Creating source archive...")
        archive_name = f"{self.project_dir.name}-{self.version}.tar.gz"
        archive_path = self.project_dir / archive_name
        
        # Create source archive using git archive
        self._run_command([
            "git", "archive",
            "--format=tar.gz",
            f"--prefix={self.project_dir.name}-{self.version}/",
            "-o", str(archive_path),
            "HEAD"
        ])
        
        # Calculate SHA256 sum
        sha256_result = self._run_command(["sha256sum", str(archive_path)])
        sha256 = sha256_result.stdout.split()[0]
        
        # Update PKGBUILD with new source and checksum
        with open(pkgbuild_path, 'r') as f:
            pkgbuild_content = f.read()
            
        # Update source and sha256sums
        pkgbuild_content = pkgbuild_content.replace(
            'sha256sums=("SKIP")',
            f'sha256sums=("{sha256}")'
        )
        
        with open(pkgbuild_path, 'w') as f:
            f.write(pkgbuild_content)
            
        # Build package
        self.output_message("Starting makepkg process...")
        try:
            env = os.environ.copy()
            env["PKGDEST"] = str(dist_dir)
            
            result = self._run_command(
                ["makepkg", "-f"],
                env=env,
                timeout=300  # 5 minutes timeout
            )
            
            self.output_message("\nBuild output:")
            self.output_message(result.stdout)
            
            if result.stderr.strip():
                self.output_message("\nBuild errors:")
                self.output_message(result.stderr)
                
        except subprocess.TimeoutExpired:
            raise Exception("Build process timed out")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Build failed with error code {e.returncode}")
            
        # Verify build artifacts
        package_file = next(dist_dir.glob("*.pkg.tar.zst"), None)
        if not package_file:
            raise Exception("No package file found after build")

    def _verify_release_assets(self, version, max_retries=20, retry_delay=15):
        """Verify release assets with retries"""
        archive_name = f"{self.project_dir.name}-{version}"
        archive_url = f"{self.url}/releases/download/v{version}/{archive_name}.tar.gz"
        
        for attempt in range(max_retries):
            try:
                self.output_message(f"Verifying release assets (attempt {attempt + 1}/{max_retries})...")
                
                # First verify the release exists
                release_result = self._run_command(
                    ["gh", "release", "view", f"v{version}"],
                    check=False
                )
                
                if release_result.returncode != 0:
                    self.output_message("Release not found yet...")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    continue
                
                # Then verify the asset is downloadable
                result = self._run_command(
                    ["curl", "-IL", archive_url],
                    timeout=30,
                    check=False
                )
                
                if "HTTP/2 200" in result.stdout or "HTTP/1.1 200" in result.stdout:
                    # Try to actually download a small part of the file to verify it's really there
                    test_download = self._run_command(
                        ["curl", "-r", "0-1024", "-o", "/dev/null", archive_url],
                        check=False
                    )
                    if test_download.returncode == 0:
                        self.output_message("Release assets verified successfully")
                        return True
                    
                if attempt < max_retries - 1:
                    self.output_message(f"Assets not ready yet, waiting {retry_delay} seconds...")
                    time.sleep(retry_delay)
            except Exception as e:
                self.output_message(f"Verification attempt failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    
        return False

    def _check_github_authentication(self):
        """Check if the user is authenticated with GitHub CLI and prompt to log in if not."""
        self.progress.emit("Checking GitHub authentication...")
        try:
            auth_status = self._run_command(["gh", "auth", "status"], check=False)
            if "not logged into any GitHub hosts" in auth_status.stdout:
                raise Exception("Not authenticated with GitHub. Please run 'gh auth login' to authenticate.")
        except Exception as e:
            self.error.emit(str(e))
            raise

    def _create_github_release(self):
        """Create a GitHub release"""
        self.output_message("\nCreating GitHub release...")
        
        # Verify GitHub CLI authentication
        self._check_github_authentication()
        
        # Get system architecture
        arch = self._run_command(['uname', '-m']).stdout.strip()
        
        # Check for uncommitted changes
        self.progress.emit("Checking git status...")
        result = self._run_command(['git', 'status', '--porcelain'])
        if result.stdout.strip():
            self.output_message("Committing changes before release...")
            self.progress.emit("Committing changes...")
            self._run_command(['git', 'add', '.'])
            self._run_command(['git', 'commit', '-m', f'Release version {self.version}'])
        
        # Create and push tag
        tag = f'v{self.version}'
        try:
            self.progress.emit("Creating git tag...")
            self._run_command(['git', 'tag', '-a', tag, '-m', f'Release {tag}'])
            self.progress.emit("Pushing git tag...")
            self._run_command(['git', 'push', 'origin', tag])
        except Exception as e:
            if 'already exists' not in str(e):
                raise
                
        # Create GitHub release
        self.progress.emit("Creating GitHub release...")
        release_notes = f"Release {tag}\n\nPackage files:\n"
        
        # Add built package files to release notes
        dist_dir = self.project_dir / 'dist'
        if dist_dir.exists():
            for file in dist_dir.glob('*'):
                if file.is_file():
                    release_notes += f"- {file.name}\n"
        
        # Create the release using gh cli
        self._run_command([
            'gh', 'release', 'create', tag,
            '--title', f'Release {tag}',
            '--notes', release_notes,
            *[str(f) for f in dist_dir.glob('*') if f.is_file()]
        ])
        
        self.output_message(f"GitHub release {tag} created successfully")

    def _update_aur(self):
        """Update AUR package with proper .SRCINFO handling"""
        if not self.use_aur:
            return
            
        self.progress.emit("Updating AUR package...")
        
        # Clone AUR repo if it doesn't exist
        if not self.aur_dir.exists():
            self.progress.emit("Cloning AUR repository...")
            self._run_command(["git", "clone", "ssh://aur@aur.archlinux.org/varchiver.git", str(self.aur_dir)])
            
        # Make sure we're on master branch
        self.progress.emit("Updating AUR repository...")
        
        try:
            # Fetch and reset to latest master
            self._run_command(["git", "fetch", "origin", "master"], cwd=self.aur_dir)
            self._run_command(["git", "reset", "--hard", "origin/master"], cwd=self.aur_dir)
            
            try:
                # Try to checkout master
                self._run_command(["git", "checkout", "master"], cwd=self.aur_dir)
            except Exception:
                # If checkout fails, create master branch
                self._run_command(["git", "checkout", "-b", "master", "origin/master"], cwd=self.aur_dir)
            
            # Read the project's PKGBUILD
            pkgbuild_src = self.project_dir / "PKGBUILD"
            if not pkgbuild_src.exists():
                raise Exception("PKGBUILD not found in project directory")
            
            with pkgbuild_src.open('r') as f:
                pkgbuild_content = f.read()
            
            # Update version and source hash
            pkgbuild_content = re.sub(
                r'^pkgver=.*$',
                f'pkgver={self.version}',
                pkgbuild_content,
                flags=re.MULTILINE
            )
            
            # Update source array if needed
            if 'source=(' not in pkgbuild_content:
                pkgbuild_content = re.sub(
                    r'source=.*$',
                    'source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")',
                    pkgbuild_content,
                    flags=re.MULTILINE
                )
            
            # Update SHA256 sum
            self.progress.emit("Calculating SHA256 of GitHub release file...")
            sha256_result = self._run_command([
                "bash", "-c",
                f"curl -L {self.url}/archive/v{self.version}.tar.gz | sha256sum"
            ])
            sha256 = sha256_result.stdout.split()[0]
            
            pkgbuild_content = re.sub(
                r'sha256sums=\([^)]*\)',
                f'sha256sums=("{sha256}")',
                pkgbuild_content,
                flags=re.MULTILINE | re.DOTALL
            )
            
            # Write updated PKGBUILD
            pkgbuild_dest = self.aur_dir / "PKGBUILD"
            with pkgbuild_dest.open('w') as f:
                f.write(pkgbuild_content)
                
            # Generate and update .SRCINFO
            self.progress.emit("Generating .SRCINFO...")
            srcinfo_result = self._run_command(
                ["makepkg", "--printsrcinfo"], 
                cwd=self.aur_dir, 
                timeout=30
            )
            
            srcinfo_path = self.aur_dir / ".SRCINFO"
            srcinfo_path.write_text(srcinfo_result.stdout)
            
            # Check for changes
            status_result = self._run_command(["git", "status", "--porcelain"], cwd=self.aur_dir)
            
            if not status_result.stdout.strip():
                self.output_message("No changes detected in AUR package")
                return
                
            # Commit and push changes
            self.progress.emit("Pushing to AUR...")
            self._run_command(["git", "add", "PKGBUILD", ".SRCINFO"], cwd=self.aur_dir)
            self._run_command(
                ["git", "commit", "-m", f"Update to version {self.version}"],
                cwd=self.aur_dir
            )
            self._run_command(["git", "push", "origin", "master"], cwd=self.aur_dir)
            
            self.progress.emit("AUR package updated successfully")
            
        except Exception as e:
            self.output_message(f"Error updating AUR package: {e}")
            # Don't raise the exception - let the process continue
            # This allows the release to complete even if AUR update fails
            return

    def _update_file_version(self, file_path, pattern, replacement):
        content = file_path.read_text()
        updated = re.sub(pattern, replacement, content)
        file_path.write_text(updated)


class ReleaseManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Version input
        version_group = QGroupBox("Release Version")
        version_layout = QHBoxLayout()
        version_group.setLayout(version_layout)
        
        self.version_input = QLineEdit()
        settings = QSettings("Varchiver", "ReleaseManager")
        
        # Try to get current version from PKGBUILD
        project_path = settings.value("project_path")
        if project_path:
            pkgbuild_path = Path(project_path) / "PKGBUILD"
            if pkgbuild_path.exists():
                try:
                    with open(pkgbuild_path) as f:
                        for line in f:
                            if line.startswith("pkgver="):
                                current_version = line.split("=")[1].strip()
                                self.version_input.setText(current_version)
                                break
                except Exception:
                    # Fall back to last used version
                    if settings.value("last_version"):
                        self.version_input.setText(settings.value("last_version"))
            elif settings.value("last_version"):
                self.version_input.setText(settings.value("last_version"))
        
        self.version_input.setPlaceholderText("Enter version number (e.g., 0.4.1)")
        version_layout.addWidget(self.version_input)
        layout.addWidget(version_group)
        
        # Task selection
        task_group = QGroupBox("Release Task")
        task_layout = QVBoxLayout()
        task_group.setLayout(task_layout)

        self.task_combo = QComboBox()
        self.task_combo.addItems([
            "Full Release (Update Version + Build + Create Release + Update AUR)",
            "Update Version Only",
            "Build and Create Release",
            "Update AUR Only",
            "Update Version + Build + Create Release",
            "Build + Create Release + Update AUR"
        ])
        task_layout.addWidget(self.task_combo)
        layout.addWidget(task_group)
        
        # AUR Directory
        aur_group = QGroupBox("AUR Directory")
        aur_layout = QHBoxLayout()
        aur_group.setLayout(aur_layout)

        self.aur_path = QLineEdit()
        if settings.value("aur_path"):
            self.aur_path.setText(settings.value("aur_path"))
        self.aur_path.setPlaceholderText("Select AUR package directory")
        aur_layout.addWidget(self.aur_path)

        aur_browse = QPushButton("Choose Directory")
        aur_browse.clicked.connect(self.browse_aur_dir)
        aur_layout.addWidget(aur_browse)
        layout.addWidget(aur_group)

        # Start button and progress bar in horizontal layout
        controls_layout = QHBoxLayout()
        
        # Start button
        self.release_start_button = QPushButton("Start Release")
        self.release_start_button.clicked.connect(self.start_release_process)
        controls_layout.addWidget(self.release_start_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        controls_layout.addWidget(self.progress_bar)
        
        layout.addLayout(controls_layout)

        # Output area
        output_group = QGroupBox("Release Output")
        output_layout = QVBoxLayout()
        output_group.setLayout(output_layout)

        self.release_output = QTextEdit()
        self.release_output.setReadOnly(True)
        self.release_output.setMaximumHeight(150)  # Limit height
        output_layout.addWidget(self.release_output)
        layout.addWidget(output_group)

        # Apply dark mode compatible styles
        self.apply_styles()

    def apply_styles(self):
        """Apply dark mode compatible styles"""
        self.setStyleSheet("""
            QGroupBox {
                background-color: transparent;
                border: 1px solid palette(mid);
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }
            QLineEdit {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 4px;
            }
            QTextEdit {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 4px;
            }
            QComboBox {
                background-color: palette(button);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 4px;
                min-width: 6em;
            }
            QPushButton {
                background-color: palette(button);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 6px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: palette(light);
            }
            QPushButton:pressed {
                background-color: palette(dark);
            }
        """)

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
        """Start the release process with the selected task"""
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
        project_path = settings.value("project_path")
        if not project_path:
            QMessageBox.warning(self, "Error", "Project path not set")
            return
            
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
        
        try:
            self.release_thread = ReleaseThread(
                project_dir=Path(project_path),
                version=version,
                tasks=selected_tasks,
                output_widget=self.release_output,
                use_aur="Update AUR" in selected,
                aur_dir=Path(self.aur_path.text()) if "Update AUR" in selected else None
            )
            
            self.release_thread.progress.connect(self.update_progress)
            self.release_thread.error.connect(self.show_error)
            self.release_thread.output.connect(self.update_output)
            self.release_thread.finished.connect(self.on_release_complete)
            
            self.release_thread.start()
            
        except Exception as e:
            self.release_start_button.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Failed to start release process: {str(e)}")
            self.release_output.append(f"Error: {str(e)}")
            return

    def on_release_complete(self, success: bool):
        """Handle completion of release process"""
        self.release_start_button.setEnabled(True)
        self.progress_bar.hide()
        
        if success:
            QMessageBox.information(
                self,
                "Release Complete",
                "Release process completed successfully!\n\n"
                "All selected tasks have been completed."
            )
        else:
            # Error message will have already been shown by show_error
            pass
            
        # Ensure the output is scrolled to the end
        cursor = self.release_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.release_output.setTextCursor(cursor)

    def show_error(self, message: str):
        """Show error message"""
        self.progress_bar.hide()
        QMessageBox.critical(self, "Error", message)
        self.release_start_button.setEnabled(True)

    def update_progress(self, message: str):
        """Update progress message in the output"""
        self.release_output.append(message)
        # Show progress bar during long operations
        if any(x in message.lower() for x in ["building package", "creating github release", "updating aur package"]):
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.progress_bar.show()
        elif "completed" in message.lower():
            self.progress_bar.hide()
        # Ensure the new text is visible
        cursor = self.release_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.release_output.setTextCursor(cursor)

    def update_output(self, text: str):
        """Update output text"""
        self.release_output.append(text)
        # Ensure the new text is visible
        cursor = self.release_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.release_output.setTextCursor(cursor)
