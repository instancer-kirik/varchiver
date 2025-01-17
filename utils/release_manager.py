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
    progress = pyqtSignal(str)  # For progress bar and output widget
    error = pyqtSignal(str)     # For error messages
    finished = pyqtSignal(bool) # For completion status
    dialog_signal = pyqtSignal(str, str, list)  # For user interaction dialogs
    
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
            # Emit progress signal for UI updates
            self.progress.emit(message)
            
            # Write to log file if available
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
            
        # Update PKGBUILD version first
        with open(pkgbuild_path, 'r') as f:
            pkgbuild_content = f.read()
            
        # Update version and source filename
        pkgbuild_content = re.sub(
            r'^pkgver=.*$',
            f'pkgver={self.version}',
            pkgbuild_content,
            flags=re.MULTILINE
        )
        
        # Update source filename to match new version
        pkgbuild_content = re.sub(
            r'source=\([^)]*\)',
            f'source=("$pkgname-{self.version}.tar.gz::$url/archive/v{self.version}.tar.gz")',
            pkgbuild_content,
            flags=re.MULTILINE
        )
        
        with open(pkgbuild_path, 'w') as f:
            f.write(pkgbuild_content)
            
        # Create dist directory if it doesn't exist
        dist_dir = self.project_dir / "dist"
        dist_dir.mkdir(exist_ok=True)
            
        # Clean up previous build artifacts
        self.output_message("Cleaning up previous build artifacts...")
        
        # Clean build directories and artifacts
        for d in ["pkg", "src", "dist", "AppDir"]:
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
        pkgbuild_content = re.sub(
            r'sha256sums=\([^)]*\)',
            f'sha256sums=("{sha256}")',
            pkgbuild_content
        )
        
        with open(pkgbuild_path, 'w') as f:
            f.write(pkgbuild_content)
            
        # Build package
        self.output_message("Starting makepkg process...")
        try:
            env = os.environ.copy()
            env["PKGDEST"] = str(dist_dir)
            
            # Copy resources before building
            src_resources = self.project_dir / "varchiver" / "resources"
            if src_resources.exists():
                dst_resources = self.project_dir / "src" / f"{self.project_dir.name}-{self.version}" / "varchiver" / "resources"
                dst_resources.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                if dst_resources.exists():
                    shutil.rmtree(dst_resources)
                shutil.copytree(src_resources, dst_resources)
                self.output_message("Copied resources directory")
            
            result = self._run_command(
                ["makepkg", "-f"],
                env=env,
                timeout=300  # 5 minutes timeout
            )
            
            self.output_message("\nBuild output:")
            self.output_message(result.stdout)
            
            if result.stderr.strip():
                self.output_message("\nBuild warnings:")
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
            release_notes += "\nAvailable packages:\n"
            for file in dist_dir.glob('*'):
                if file.is_file():
                    if file.name.endswith('.AppImage'):
                        release_notes += f"- {file.name} (Portable Linux AppImage)\n"
                    elif file.name.endswith('.tar.gz'):
                        release_notes += f"- {file.name} (Linux binary)\n"
                    elif file.name.endswith('.pkg.tar.zst'):
                        release_notes += f"- {file.name} (Arch Linux package)\n"
                    else:
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
        """Initialize the UI components"""
        layout = QVBoxLayout()
        
        # Version input
        version_group = QGroupBox("Release Version")
        version_layout = QHBoxLayout()
        version_group.setLayout(version_layout)
        
        self.version_input = QLineEdit()
        settings = QSettings("Varchiver", "ReleaseManager")
        
        # Try to get current version from PKGBUILD
        project_path = settings.value("project_path", str(Path.cwd()))
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
        
        # Progress display
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()  # Initially hidden
        layout.addWidget(self.progress_bar)
        
        # Output display
        output_group = QGroupBox("Release Output")
        output_layout = QVBoxLayout()
        output_group.setLayout(output_layout)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(150)  # Limit height
        output_layout.addWidget(self.output_text)
        layout.addWidget(output_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Release")
        self.start_button.clicked.connect(self.start_release)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_release)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.release_thread = None

    def update_progress(self, message: str):
        """Update progress bar and output text"""
        # Update output text
        self.output_text.append(message)
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)
        
        # Update progress bar text
        self.progress_bar.setFormat(message.split('\n')[0])  # Use first line for progress bar
        
    def handle_error(self, error_msg: str):
        """Handle error messages from the release thread"""
        QMessageBox.critical(self, "Error", error_msg)
        self.release_finished(False)
        
    def handle_dialog(self, title: str, message: str, options: list):
        """Handle dialog requests from the release thread"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        dialog.setIcon(QMessageBox.Icon.Question)
        
        # Create buttons for each option
        buttons = {}
        for option in options:
            button = dialog.addButton(option, QMessageBox.ButtonRole.ActionRole)
            buttons[button] = option
            
        dialog.exec()
        clicked = dialog.clickedButton()
        
        if clicked in buttons and self.release_thread:
            self.release_thread.handle_dialog_response(buttons[clicked])
            
    def release_finished(self, success: bool):
        """Handle release process completion"""
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if success:
            self.progress_bar.setFormat("Release completed successfully")
            QMessageBox.information(self, "Success", "Release process completed successfully!")
        else:
            self.progress_bar.setFormat("Release failed")
            
    def start_release(self):
        """Start the release process"""
        # Get selected tasks based on combo selection
        selected = self.task_combo.currentText()
        tasks = []
        if "Update Version" in selected:
            tasks.append('update_version')
        if "Create Release" in selected:
            tasks.append('create_release')
        if "Update AUR" in selected:
            tasks.append('update_aur')
        
        if not tasks:
            QMessageBox.warning(self, "Warning", "No tasks selected!")
            return
            
        version = self.version_input.text().strip()
        if not version:
            QMessageBox.warning(self, "Warning", "Version number required!")
            return
            
        # Create and start release thread
        self.release_thread = ReleaseThread(
            project_dir=Path.cwd(),
            version=version,
            tasks=tasks,
            output_widget=self.output_text,
            use_aur='update_aur' in tasks,
            aur_dir=Path(self.aur_path.text()) if self.aur_path.text() else None
        )
        
        # Connect signals
        self.release_thread.progress.connect(self.update_progress)
        self.release_thread.error.connect(self.handle_error)
        self.release_thread.finished.connect(self.release_finished)
        self.release_thread.dialog_signal.connect(self.handle_dialog)
        
        # Update UI state
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setFormat("Starting release process...")
        self.progress_bar.show()
        self.output_text.clear()
        
        # Save settings
        settings = QSettings("Varchiver", "ReleaseManager")
        settings.setValue("last_version", version)
        settings.setValue("aur_path", self.aur_path.text())
        
        # Start the thread
        self.release_thread.start()
        
    def cancel_release(self):
        """Cancel the release process"""
        if self.release_thread and self.release_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Cancel",
                "Are you sure you want to cancel the release process?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.release_thread.terminate()
                self.release_finished(False)
                
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
