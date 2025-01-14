print("Loading release_manager module")

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLineEdit, QLabel, QComboBox, QProgressBar, QMessageBox, QDialog,
                            QFileDialog, QGroupBox, QFormLayout, QTextEdit)
from PyQt6.QtCore import QThread, pyqtSignal, QSettings, pyqtSlot
import subprocess
import os
import re
from pathlib import Path
import time

print("Imports completed in release_manager module")

class ReleaseThread(QThread):
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    output = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, version, tasks):
        super().__init__()
        self.version = version
        self.tasks = tasks
        self.settings = QSettings("Varchiver", "ReleaseManager")
        self.project_dir = Path(self.settings.value("project_path")).resolve()
        self.project_type = self.settings.value("project_type")
        self.version_patterns = self.settings.value("version_patterns").split(",")
        self.version_files = self.settings.value("version_files").split(",")
        self.use_git = self.settings.value("use_git") == "Yes"
        self.git_branch = self.settings.value("git_branch")
        self.use_aur = self.settings.value("use_aur") == "Yes"
        self.aur_dir = Path(self.settings.value("aur_path")).resolve() if self.use_aur else None
        self.build_command = self.settings.value("build_command")
        self.url = "https://github.com/instancer-kirik/varchiver"  # Add GitHub URL

    def _check_git_status(self):
        """Check if git repository is clean"""
        self.progress.emit("Checking git status...")
        
        # Check if we're in a git repository
        result = subprocess.run(["git", "rev-parse", "--git-dir"], 
                              cwd=self.project_dir, 
                              capture_output=True, 
                              text=True)
        if result.returncode != 0:
            raise Exception("Not a git repository")
            
        # Check for uncommitted changes
        result = subprocess.run(["git", "status", "--porcelain"], 
                              cwd=self.project_dir, 
                              capture_output=True, 
                              text=True)
        if result.stdout.strip():
            raise Exception("Repository has uncommitted changes. Please commit or stash them first.")
            
        # Check if we're on the correct branch
        result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                              cwd=self.project_dir,
                              capture_output=True,
                              text=True)
        current_branch = result.stdout.strip()
        if current_branch != self.git_branch:
            raise Exception(f"Not on the correct branch. Expected {self.git_branch}, but on {current_branch}")
            
        # Check if branch is up to date with remote
        result = subprocess.run(["git", "fetch", "origin", self.git_branch],
                              cwd=self.project_dir,
                              capture_output=True,
                              text=True)
        if result.returncode != 0:
            raise Exception("Failed to fetch from remote")
            
        result = subprocess.run(["git", "rev-list", "HEAD...origin/" + self.git_branch, "--count"],
                              cwd=self.project_dir,
                              capture_output=True,
                              text=True)
        if result.stdout.strip() != "0":
            raise Exception(f"Branch {self.git_branch} is not up to date with remote")

    def run(self):
        try:
            # Check git status first if we're using git
            if self.use_git and ('update_version' in self.tasks or 'create_release' in self.tasks):
                self._check_git_status()
            
            if 'update_version' in self.tasks:
                self._update_version_files()
            
            if 'build_packages' in self.tasks:
                self._build_packages()
            
            if 'create_release' in self.tasks and self.use_git:
                self._create_github_release()
            
            if 'update_aur' in self.tasks and self.use_aur:
                self._update_aur()

            self.finished.emit(True)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False)

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
        self.progress.emit("Building packages...")
        
        # First check if PKGBUILD exists
        pkgbuild_path = self.project_dir / "PKGBUILD"
        if not pkgbuild_path.exists():
            raise Exception("PKGBUILD not found in project directory")
            
        # Clean up previous build
        self.output.emit("Cleaning up previous build...")
        cleanup = subprocess.run(
            ["rm", "-rf", "pkg/", "src/", "*.pkg.tar.zst"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        
        # Install dependencies and build package
        self.output.emit("Installing dependencies and building package...")
        self.output.emit("Running: makepkg -sf --noconfirm --skipchecksums")
        
        # Run makepkg with syncdeps and force
        result = subprocess.run(
            ["makepkg", "-sf", "--noconfirm", "--skipchecksums"], 
            cwd=self.project_dir, 
            capture_output=True, 
            text=True,
            env={**os.environ, "PKGBUILD": str(pkgbuild_path)}
        )
        
        # Show output regardless of success/failure
        if result.stdout:
            self.output.emit("\nOutput:")
            self.output.emit(result.stdout)
        if result.stderr:
            self.output.emit("\nErrors:")
            self.output.emit(result.stderr)
        
        if result.returncode != 0:
            # Try to get more detailed error information
            self.output.emit("\nChecking package dependencies...")
            check = subprocess.run(
                ["makepkg", "--printsrcinfo"], 
                cwd=self.project_dir, 
                capture_output=True, 
                text=True
            )
            if check.stdout:
                self.output.emit("\nPackage information:")
                self.output.emit(check.stdout)
            raise Exception("Build failed. Check the output above for details.")
            
        self.progress.emit("Build completed successfully")

    def _run_command(self, cmd, cwd=None, timeout=60, env=None, check=True):
        """Helper function to run commands with consistent error handling and timeouts"""
        try:
            merged_env = os.environ.copy()
            if env:
                merged_env.update(env)
            
            self.output.emit(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=merged_env,
                check=check
            )
            self.output.emit(f"Command output: {result.stdout}")
            if result.stderr:
                self.output.emit(f"Command error: {result.stderr}")
            return result
        except subprocess.TimeoutExpired:
            self.output.emit(f"Command timed out after {timeout} seconds: {' '.join(cmd)}")
            raise
        except subprocess.CalledProcessError as e:
            self.output.emit(f"Command failed with exit code {e.returncode}:")
            self.output.emit(f"Command: {' '.join(cmd)}")
            if e.stdout:
                self.output.emit(f"Output:\n{e.stdout}")
            if e.stderr:
                self.output.emit(f"Error:\n{e.stderr}")
            raise
        except Exception as e:
            self.output.emit(f"Unexpected error running command: {e}")
            raise

    def _verify_release_assets(self, version, max_retries=20, retry_delay=15):
        """Verify release assets with retries"""
        archive_name = f"{self.project_dir.name}-{version}"
        archive_url = f"{self.url}/releases/download/v{version}/{archive_name}.tar.gz"
        
        for attempt in range(max_retries):
            try:
                self.output.emit(f"Verifying release assets (attempt {attempt + 1}/{max_retries})...")
                
                # First verify the release exists
                release_result = self._run_command(
                    ["gh", "release", "view", f"v{version}"],
                    check=False
                )
                
                if release_result.returncode != 0:
                    self.output.emit("Release not found yet...")
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
                        self.output.emit("Release assets verified successfully")
                        return True
                    
                if attempt < max_retries - 1:
                    self.output.emit(f"Assets not ready yet, waiting {retry_delay} seconds...")
                    time.sleep(retry_delay)
            except Exception as e:
                self.output.emit(f"Verification attempt failed: {e}")
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
        """Create a GitHub release with improved error handling and verification"""
        self.progress.emit("Creating GitHub release...")
        
        try:
            # Check GitHub authentication
            self._check_github_authentication()
            
            # Get system architecture
            arch_result = self._run_command(["uname", "-m"])
            arch = arch_result.stdout.strip()
            
            # Check for changes
            status_result = self._run_command(["git", "status", "--porcelain"])
            if not status_result.stdout.strip():
                self.output.emit("No changes to commit")
                return
            
            # Add and commit changes
            self.output.emit("Adding and committing changes...")
            self._run_command(["git", "add", "."])
            self._run_command(["git", "commit", "-m", f"Release v{self.version}"])
            
            # Create and push tag
            self.output.emit("Creating and pushing tag...")
            tag_result = self._run_command(["git", "tag", "-f", f"v{self.version}"])
            self.output.emit(f"Tag creation output: {tag_result.stdout}")
            self._run_command(["git", "push", "-f", "origin", self.git_branch])
            self._run_command(["git", "push", "-f", "origin", f"v{self.version}"])
            
            # Wait a moment for GitHub to process the tag
            time.sleep(5)
            
            # Create source archive
            self.output.emit("Creating source archive...")
            archive_name = f"{self.project_dir.name}-{self.version}"
            archive_path = self.project_dir / f"{archive_name}.tar.gz"
            
            # Create archive with explicit prefix and all files
            self._run_command([
                "git", "archive",
                "--format=tar.gz",
                "--prefix", f"{archive_name}/",
                "-o", str(archive_path),
                "--verbose",
                f"v{self.version}"
            ])
            
            # Verify the archive was created and has content
            if not archive_path.exists() or archive_path.stat().st_size == 0:
                raise Exception("Failed to create source archive or archive is empty")
            
            # Calculate and update SHA256
            sha256_result = self._run_command(["sha256sum", str(archive_path)])
            sha256 = sha256_result.stdout.split()[0]
            
            # Update PKGBUILD with proper multiline handling
            pkgbuild_path = self.project_dir / "PKGBUILD"
            with pkgbuild_path.open('r') as f:
                content = f.read()
            
            # Handle both single and multiline sha256sums formats
            content = re.sub(
                r'sha256sums=\([^)]*\)',
                f'sha256sums=("{sha256}")',
                content,
                flags=re.MULTILINE | re.DOTALL
            )
            
            with pkgbuild_path.open('w') as f:
                f.write(content)
            
            # Create GitHub release
            self.output.emit("Creating GitHub release...")
            
            # Find built package
            pkg_glob = f"{self.project_dir.name}-{self.version}-*-{arch}.pkg.tar.zst"
            pkg_file = next(self.project_dir.glob(pkg_glob), None)
            
            # Delete existing release if it exists
            self._run_command(
                ["gh", "release", "delete", f"v{self.version}", "--yes"],
                check=False
            )
            
            # Create new release with source archive
            release_args = [
                "gh", "release", "create",
                f"v{self.version}",
                "--title", f"Release v{self.version}",
                "--notes", f"Release v{self.version}",
                "--target", self.git_branch,
                "--verify-tag"  # Ensure the tag exists before creating release
            ]
            
            try:
                # First create the release
                self.output.emit("Running: " + " ".join(release_args))
                release_result = self._run_command(release_args)
                self.output.emit(f"Release creation output: {release_result.stdout}")
                
                # Then upload the assets separately
                self.output.emit("Uploading release assets...")
                
                # Upload source archive
                upload_args = [
                    "gh", "release", "upload",
                    f"v{self.version}",
                    str(archive_path),
                    "--clobber"  # Overwrite existing asset if needed
                ]
                self.output.emit("Running: " + " ".join(upload_args))
                upload_result = self._run_command(upload_args)
                self.output.emit(f"Upload output: {upload_result.stdout}")
                
                # Upload package if it exists
                if pkg_file:
                    pkg_upload_args = [
                        "gh", "release", "upload",
                        f"v{self.version}",
                        str(pkg_file),
                        "--clobber"
                    ]
                    self.output.emit("Running: " + " ".join(pkg_upload_args))
                    pkg_upload_result = self._run_command(pkg_upload_args)
                    self.output.emit(f"Package upload output: {pkg_upload_result.stdout}")
                
                # Verify release assets with retries
                if not self._verify_release_assets(self.version):
                    raise Exception("Failed to verify release assets after maximum retries")
                
                self.output.emit("GitHub release created and verified successfully")
                
            except Exception as e:
                self.output.emit(f"Error creating GitHub release: {e}")
                raise
        except Exception as e:
            self.output.emit(f"Error in GitHub release process: {e}")
            raise

    def _update_aur(self):
        """Update AUR package with proper .SRCINFO handling"""
        if not self.use_aur:
            return
            
        self.progress.emit("Updating AUR package...")
        
        # Clone AUR repo if it doesn't exist
        if not self.aur_dir.exists():
            self._run_command(["git", "clone", "ssh://aur@aur.archlinux.org/varchiver.git", str(self.aur_dir)])
            
        # Make sure we're on master branch
        self.output.emit("Switching to master branch...")
        
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
            
            # Copy PKGBUILD and update for AUR
            pkgbuild_src = self.project_dir / "PKGBUILD"
            pkgbuild_dest = self.aur_dir / "PKGBUILD"
            
            # Read the development PKGBUILD
            with pkgbuild_src.open() as f:
                content = f.read()
            
            # Modify for AUR (use GitHub source instead of local files)
            content = re.sub(
                r'source=\([^)]*\)',
                f'source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")',
                content,
                flags=re.MULTILINE | re.DOTALL
            )
            
            # Update cd command if needed
            if 'cd "$srcdir"' in content:
                content = content.replace('cd "$srcdir"', 'cd "$srcdir/$pkgname-$pkgver"')
            elif "cd $srcdir" in content:
                content = content.replace("cd $srcdir", 'cd "$srcdir/$pkgname-$pkgver"')
            
            # Write updated PKGBUILD
            with pkgbuild_dest.open('w') as f:
                f.write(content)
                
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
                self.output.emit("No changes detected in AUR package")
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
            self.output.emit(f"Error updating AUR package: {e}")
            raise

    def _update_file_version(self, file_path, pattern, replacement):
        content = file_path.read_text()
        updated = re.sub(pattern, replacement, content)
        file_path.write_text(updated)


class ReleaseManager(QWidget):
    def __init__(self):
        print("Initializing ReleaseManager")
        super().__init__()
        self.settings = QSettings("Varchiver", "ReleaseManager")
        
        # Initialize UI elements
        self.project_dir_label = QLabel()
        self.project_type_label = QLabel()
        self.aur_dir_label = QLabel()
        self.version_input = QLineEdit()
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel()
        self.release_button = QPushButton("Start Release")
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: monospace;
                padding: 8px;
            }
        """)
        self.task_combos = {}
        self.config_dialog = None
        
        # Set up UI
        self.init_ui()
        
        # Check paths and update UI
        if not self.settings.value("project_path"):
            print("No project path, showing config")
            self.show_config()
        else:
            self.check_paths()
            self.update_ui_from_settings()
        
        print("ReleaseManager initialized")

    def show_config(self):
        """Show configuration dialog"""
        print("show_config called")
        if not self.config_dialog:
            print("Creating new config dialog")
            self.config_dialog = ConfigDialog(self)
        result = self.config_dialog.exec()
        print(f"Dialog result: {result}")
        if result == QDialog.DialogCode.Accepted:
            self.check_paths()
            self.update_ui_from_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Configuration section
        config_group = QGroupBox("Configuration")
        config_layout = QFormLayout()
        config_group.setLayout(config_layout)
        
        # Project directory display
        self.project_dir_label.setStyleSheet("""
            QLabel {
                padding: 4px;
                background-color: #e0e0e0;
                color: #000000;
                border-radius: 4px;
                min-width: 300px;
            }
        """)
        config_layout.addRow("Project Directory:", self.project_dir_label)
        
        # Project type display
        self.project_type_label.setStyleSheet("""
            QLabel {
                padding: 4px;
                background-color: #e0e0e0;
                color: #000000;
                border-radius: 4px;
            }
        """)
        config_layout.addRow("Project Type:", self.project_type_label)
        
        # AUR directory display
        self.aur_dir_label.setStyleSheet("""
            QLabel {
                padding: 4px;
                background-color: #e0e0e0;
                color: #000000;
                border-radius: 4px;
                min-width: 300px;
            }
        """)
        config_layout.addRow("AUR Directory:", self.aur_dir_label)
        
        # Configure button
        config_button = QPushButton("Configure")
        config_button.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        config_button.clicked.connect(self.show_config)
        config_layout.addRow("", config_button)
        
        layout.addWidget(config_group)
        
        # Version input
        version_group = QGroupBox("Version")
        version_layout = QVBoxLayout()
        version_group.setLayout(version_layout)
        
        version_input_layout = QHBoxLayout()
        version_input_layout.addWidget(QLabel("New Version:"))
        
        # Get current version from PKGBUILD
        pkgbuild_path = Path(self.settings.value("project_path")) / "PKGBUILD"
        current_version = ""
        if pkgbuild_path.exists():
            try:
                with pkgbuild_path.open() as f:
                    for line in f:
                        if line.startswith("pkgver="):
                            current_version = line.split("=")[1].strip()
                            break
            except Exception:
                pass
        
        self.version_input.setText(current_version or "0.3.6")
        self.version_input.setStyleSheet("""
            QLineEdit {
                padding: 4px;
                border: 1px solid #bdbdbd;
                border-radius: 4px;
                min-width: 100px;
            }
        """)
        version_input_layout.addWidget(self.version_input)
        version_input_layout.addStretch()
        version_layout.addLayout(version_input_layout)
        
        layout.addWidget(version_group)
        
        # Tasks selection
        tasks_group = QGroupBox("Tasks")
        tasks_layout = QVBoxLayout()
        tasks_group.setLayout(tasks_layout)
        
        self.tasks = {
            "update_version": "Update version in files",
            "build_packages": "Build packages",
            "create_release": "Create GitHub release",
            "update_aur": "Update AUR package"
        }
        
        self.task_combos = {}
        for key, label in self.tasks.items():
            task_layout = QHBoxLayout()
            task_label = QLabel(label)
            task_label.setMinimumWidth(150)
            task_layout.addWidget(task_label)
            
            checkbox = QComboBox()
            checkbox.addItems(["Skip", "Include"])
            checkbox.setObjectName(key)
            checkbox.setStyleSheet("""
                QComboBox {
                    padding: 4px;
                    border: 1px solid #bdbdbd;
                    border-radius: 4px;
                    min-width: 100px;
                }
            """)
            task_layout.addWidget(checkbox)
            task_layout.addStretch()
            tasks_layout.addLayout(task_layout)
            self.task_combos[key] = checkbox
        
        layout.addWidget(tasks_group)
        
        # Terminal output section
        output_group = QGroupBox("Build Output")
        output_layout = QVBoxLayout()
        output_group.setLayout(output_layout)
        output_layout.addWidget(self.output_text)
        layout.addWidget(output_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        progress_group.setLayout(progress_layout)
        
        self.progress_bar.setTextVisible(True)
        self.progress_label.setStyleSheet("""
            QLabel {
                padding: 4px;
                color: #666666;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(progress_group)
        
        # Release button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.release_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.release_button.clicked.connect(self.start_release)
        button_layout.addWidget(self.release_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setWindowTitle("Release Manager")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

    def check_paths(self):
        """Check if required paths are configured and enable/disable release button accordingly"""
        project_path = self.settings.value("project_path", "")
        use_aur = self.settings.value("use_aur", "No")
        aur_path = self.settings.value("aur_path", "") if use_aur == "Yes" else "disabled"
        
        if not project_path or (use_aur == "Yes" and not aur_path):
            self.release_button.setEnabled(False)
            self.release_button.setToolTip("Configure paths first")
        else:
            self.release_button.setEnabled(True)
            self.release_button.setToolTip("")

    def update_ui_from_settings(self):
        """Update UI elements based on current settings"""
        # Update directory labels
        project_path = self.settings.value("project_path", "")
        self.project_dir_label.setText(project_path or "Not configured")
        
        # Update project type
        project_type = self.settings.value("project_type", "Python")
        self.project_type_label.setText(project_type)
        
        # Update AUR path and visibility
        use_aur = self.settings.value("use_aur", "No")
        aur_path = self.settings.value("aur_path", "")
        self.aur_dir_label.setText(aur_path if use_aur == "Yes" else "Disabled")
        self.aur_dir_label.setVisible(use_aur == "Yes")
        
        # Update task visibility
        use_git = self.settings.value("use_git", "Yes")
        self.task_combos["create_release"].parent().setVisible(use_git == "Yes")
        self.task_combos["update_aur"].parent().setVisible(use_aur == "Yes")

    def start_release(self):
        """Start the release process"""
        # Clear previous output
        self.output_text.clear()
        
        version = self.version_input.text()
        if not version:
            QMessageBox.warning(self, "Error", "Please enter a version number")
            return
            
        # Check paths again
        project_path = self.settings.value("project_path", "")
        use_aur = self.settings.value("use_aur", "No")
        aur_path = self.settings.value("aur_path", "") if use_aur == "Yes" else "disabled"
        
        if not project_path or (use_aur == "Yes" and not aur_path):
            QMessageBox.warning(self, "Error", "Please configure paths first")
            self.show_config()
            return
            
        selected_tasks = []
        for key, combo in self.task_combos.items():
            if combo.isVisible() and combo.currentText() == "Include":
                selected_tasks.append(key)
                
        self.release_thread = ReleaseThread(version, selected_tasks)
        self.release_thread.progress.connect(self.update_progress)
        self.release_thread.error.connect(self.show_error)
        self.release_thread.output.connect(self.update_output)
        self.release_thread.finished.connect(self.release_finished)
        
        self.release_button.setEnabled(False)
        self.progress_bar.setMaximum(0)
        self.release_thread.start()

    def update_progress(self, message):
        """Update progress message"""
        self.progress_label.setText(message)
        self.progress_label.repaint()

    def show_error(self, message):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)
        self.release_button.setEnabled(True)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

    def release_finished(self, success):
        """Handle release completion"""
        self.release_button.setEnabled(True)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100 if success else 0)
        
        if success:
            QMessageBox.information(self, "Success", "Release completed successfully!")
        else:
            self.progress_label.setText("Release failed")

    def update_output(self, text):
        """Update terminal output"""
        self.output_text.append(text)
        # Scroll to bottom
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)

    def show_config2(self):
        print("show_config2 called")
        self.show_config()

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Release Manager Configuration")
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Project configuration
        project_group = QGroupBox("Project Configuration")
        project_layout = QFormLayout()
        project_group.setLayout(project_layout)
        
        # Project directory
        project_dir_layout = QHBoxLayout()
        self.project_path = QLineEdit()
        self.project_path.setPlaceholderText("Path to project repository")
        browse_project = QPushButton("Browse")
        use_git_repo = QPushButton("Use Git Repo")
        browse_project.clicked.connect(self.browse_project)
        use_git_repo.clicked.connect(self.use_git_repo_path)
        project_dir_layout.addWidget(self.project_path)
        project_dir_layout.addWidget(browse_project)
        project_dir_layout.addWidget(use_git_repo)
        project_layout.addRow("Project Directory:", project_dir_layout)

        # Project type
        self.project_type = QComboBox()
        self.project_type.addItems(["Python", "Node.js", "Rust", "Go", "Custom"])
        self.project_type.currentTextChanged.connect(self.on_project_type_changed)
        project_layout.addRow("Project Type:", self.project_type)

        # Version file patterns
        self.version_patterns = QLineEdit()
        self.version_patterns.setPlaceholderText("version = \"*\", version: *, etc. (comma-separated)")
        project_layout.addRow("Version Patterns:", self.version_patterns)

        # Version files
        self.version_files = QLineEdit()
        self.version_files.setPlaceholderText("pyproject.toml,package.json,etc. (comma-separated)")
        project_layout.addRow("Version Files:", self.version_files)
        
        layout.addWidget(project_group)

        # Repository configuration
        repo_group = QGroupBox("Repository Configuration")
        repo_layout = QFormLayout()
        repo_group.setLayout(repo_layout)

        # Git repository
        self.use_git = QComboBox()
        self.use_git.addItems(["Yes", "No"])
        self.use_git.currentTextChanged.connect(self.on_git_changed)
        repo_layout.addRow("Use Git:", self.use_git)

        # Git branch
        self.git_branch = QLineEdit()
        self.git_branch.setText("main")
        repo_layout.addRow("Git Branch:", self.git_branch)

        # AUR configuration
        self.use_aur = QComboBox()
        self.use_aur.addItems(["Yes", "No"])
        self.use_aur.currentTextChanged.connect(self.on_aur_changed)
        repo_layout.addRow("Use AUR:", self.use_aur)

        # AUR repository directory
        aur_dir_layout = QHBoxLayout()
        self.aur_path = QLineEdit()
        self.aur_path.setPlaceholderText("Path to AUR repository")
        browse_aur = QPushButton("Browse")
        use_git_output = QPushButton("Use Git Output")
        browse_aur.clicked.connect(self.browse_aur)
        use_git_output.clicked.connect(self.use_git_output_path)
        aur_dir_layout.addWidget(self.aur_path)
        aur_dir_layout.addWidget(browse_aur)
        aur_dir_layout.addWidget(use_git_output)
        repo_layout.addRow("AUR Directory:", aur_dir_layout)

        layout.addWidget(repo_group)

        # Build configuration
        build_group = QGroupBox("Build Configuration")
        build_layout = QFormLayout()
        build_group.setLayout(build_layout)

        # Build command
        self.build_command = QLineEdit()
        self.build_command.setPlaceholderText("./build.sh all, npm run build, etc.")
        build_layout.addRow("Build Command:", self.build_command)

        layout.addWidget(build_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_and_close)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    def on_project_type_changed(self, project_type):
        """Set default patterns based on project type"""
        patterns = {
            "Python": {
                "files": "pyproject.toml,PKGBUILD",
                "patterns": 'version = "*",pkgver=*,version="*"',
                "build": "makepkg -f"
            },
            "Node.js": {
                "files": "package.json",
                "patterns": '"version": "*"',
                "build": "npm run build"
            },
            "Rust": {
                "files": "Cargo.toml",
                "patterns": 'version = "*"',
                "build": "cargo build --release"
            },
            "Go": {
                "files": "go.mod",
                "patterns": 'v*',
                "build": "go build"
            }
        }
        
        if project_type in patterns:
            self.version_files.setText(patterns[project_type]["files"])
            self.version_patterns.setText(patterns[project_type]["patterns"])
            self.build_command.setText(patterns[project_type]["build"])

    def on_git_changed(self, use_git):
        """Enable/disable git-related fields"""
        self.git_branch.setEnabled(use_git == "Yes")

    def on_aur_changed(self, use_aur):
        """Enable/disable AUR-related fields"""
        self.aur_path.setEnabled(use_aur == "Yes")

    def browse_project(self):
        path = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if path:
            self.project_path.setText(path)

    def browse_aur(self):
        path = QFileDialog.getExistingDirectory(self, "Select AUR Repository Directory")
        if path:
            self.aur_path.setText(path)

    def load_settings(self):
        settings = QSettings("Varchiver", "ReleaseManager")
        self.project_path.setText(settings.value("project_path", ""))
        self.project_type.setCurrentText(settings.value("project_type", "Python"))
        self.version_patterns.setText(settings.value("version_patterns", ""))
        self.version_files.setText(settings.value("version_files", ""))
        self.use_git.setCurrentText(settings.value("use_git", "Yes"))
        self.git_branch.setText(settings.value("git_branch", "master"))
        self.use_aur.setCurrentText(settings.value("use_aur", "No"))
        self.aur_path.setText(settings.value("aur_path", ""))
        self.build_command.setText(settings.value("build_command", ""))

    def save_and_close(self):
        settings = QSettings("Varchiver", "ReleaseManager")
        settings.setValue("project_path", self.project_path.text())
        settings.setValue("project_type", self.project_type.currentText())
        settings.setValue("version_patterns", self.version_patterns.text())
        settings.setValue("version_files", self.version_files.text())
        settings.setValue("use_git", self.use_git.currentText())
        settings.setValue("git_branch", self.git_branch.text())
        settings.setValue("use_aur", self.use_aur.currentText())
        settings.setValue("aur_path", self.aur_path.text())
        settings.setValue("build_command", self.build_command.text())
        self.accept()

    def use_git_repo_path(self):
        """Use the path from Git repository configuration"""
        settings = QSettings("Varchiver", "MainWidget")
        git_repo = settings.value("git_repo_path", "")
        if git_repo:
            self.project_path.setText(git_repo)
            self.use_git.setCurrentText("Yes")

    def use_git_output_path(self):
        """Use the path from Git output configuration"""
        settings = QSettings("Varchiver", "MainWidget")
        git_output = settings.value("git_output_path", "")
        if git_output:
            self.aur_path.setText(git_output)
            self.use_aur.setCurrentText("Yes")
