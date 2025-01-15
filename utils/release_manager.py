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
from typing import List, Optional
from .project_constants import PROJECT_CONFIGS

print("Imports completed in release_manager module")

class ReleaseThread(QThread):
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    output = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, project_dir: Path, version: str, tasks: List[str], output_widget: QTextEdit, 
                 use_aur: bool = False, aur_dir: Optional[Path] = None):
        super().__init__()
        self.project_dir = project_dir
        self.version = version
        self.tasks = tasks
        self.output_widget = output_widget
        self.use_aur = use_aur
        self.aur_dir = aur_dir
        
        # Set up logging
        self.log_dir = project_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / f"release_{version}_{int(time.time())}.log"
        
        # Git configuration
        self.git_branch = "master"  # Default to master branch
        self.url = None  # Will be set from git remote
        
        # Version file patterns
        self.version_files = ['pyproject.toml', 'PKGBUILD']
        self.version_patterns = {
            'pyproject.toml': r'version\s*=\s*"[^"]*"',
            'PKGBUILD': r'^pkgver=[0-9][0-9a-zA-Z.-]*$'
        }
        
        # Initialize Git URL from remote
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()
            # Convert SSH URL to HTTPS URL if needed
            if remote_url.startswith("git@github.com:"):
                remote_url = remote_url.replace("git@github.com:", "https://github.com/")
            if remote_url.endswith(".git"):
                remote_url = remote_url[:-4]
            self.url = remote_url
        except Exception as e:
            self.output_message(f"Warning: Failed to get Git remote URL: {e}")
            self.url = None

    def output_message(self, message: str):
        """Helper method to emit output signal and update widget and log file"""
        # Update widget
        if self.output_widget:
            self.output_widget.append(message)
            # Ensure the new text is visible
            cursor = self.output_widget.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.output_widget.setTextCursor(cursor)
        
        # Write to log file
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")

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

    def run(self):
        """Execute the release process."""
        try:
            self.progress.emit("Starting release process...")
            self.output_message(f"Starting release process for version {self.version}")
            self.output_message(f"Log file: {self.log_file}")

            if not self.url:
                raise Exception("Git remote URL not found. Please configure a remote repository first.")

            # Check Git status before proceeding
            status_output = self._check_git_status()
            if status_output:
                # There are uncommitted changes (excluding untracked files)
                self.output_message("\nWarning: You have uncommitted changes:")
                self.output_message(status_output)
                self.output_message("\nPlease commit or stash your changes before proceeding.")
                raise Exception("Uncommitted changes found. Please commit or stash them before creating a release.")

            if 'update_version' in self.tasks:
                self.progress.emit("Updating version files...")
                self._update_version_files()
                self._commit_version_changes()

            # Always build packages before creating release
            if 'create_release' in self.tasks:
                self.progress.emit("Building packages...")
                self._build_packages()  # Build first
                self.progress.emit("Creating GitHub release...")
                self._create_github_release()  # Then create release with built packages

            if 'update_aur' in self.tasks:
                if not self.use_aur:
                    raise Exception("AUR update requested but AUR support is not enabled")
                if not self.aur_dir:
                    raise Exception("AUR update requested but AUR directory is not set")
                self.progress.emit("Updating AUR package...")
                self._update_aur()

            self.progress.emit("Release process completed!")
            self.output_message("Release process completed successfully!")
            self.finished.emit(True)

        except Exception as e:
            self.error.emit(str(e))
            self.output_message(f"Error during release process: {str(e)}")
            self.finished.emit(False)

    def _commit_version_changes(self):
        """Commit version number changes."""
        try:
            # Check if there are changes to commit
            status_result = self._run_command(["git", "status", "--porcelain"])
            if status_result.stdout.strip():
                self.output_message("Committing version changes...")
                
                # Add changed files
                self._run_command(["git", "add"] + self.version_files)
                
                # Commit changes
                commit_msg = f"Release v{self.version}"
                self._run_command(["git", "commit", "-m", commit_msg])
                
                self.output_message(f"Committed version changes for v{self.version}")
            else:
                self.output_message("No version changes to commit")

        except Exception as e:
            self.output_message(f"Warning: Failed to commit version changes: {str(e)}")
            # Continue with release process even if commit fails

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
            
        # Clean up previous build
        self.output_message("Cleaning up previous build artifacts...")
        for pattern in ["*.pkg.tar.zst", "*.tar.gz"]:
            for f in dist_dir.glob(pattern):
                f.unlink()
        
        # Clean build directories
        for d in ["pkg", "src"]:
            build_dir = self.project_dir / d
            if build_dir.exists():
                import shutil
                shutil.rmtree(build_dir)
        
        # Install dependencies and build package
        self.output_message("Starting makepkg process...")
        self.progress.emit("Building package...")
        
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
            self.output_message("\nBuild output:")
            self.output_message(result.stdout)
        if result.stderr:
            self.output_message("\nBuild errors:")
            self.output_message(result.stderr)
        
        if result.returncode != 0:
            # Try to get more detailed error information
            self.output_message("\nChecking package dependencies...")
            check = subprocess.run(
                ["makepkg", "--printsrcinfo"], 
                cwd=self.project_dir, 
                capture_output=True, 
                text=True
            )
            if check.stdout:
                self.output_message("\nPackage information:")
                self.output_message(check.stdout)
            raise Exception("Build failed. Check the output above for details.")
            
        # Move built packages to dist directory
        self.output_message("Moving built packages to dist directory...")
        for pkg_file in self.project_dir.glob("*.pkg.tar.zst"):
            pkg_file.rename(dist_dir / pkg_file.name)
            
        self.output_message("Build completed successfully")
        self.progress.emit("Build completed")

    def _run_command(self, cmd, cwd=None, timeout=60, env=None, check=True):
        """Helper function to run commands with consistent error handling and timeouts"""
        try:
            merged_env = os.environ.copy()
            if env:
                merged_env.update(env)
            
            self.output_message(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=merged_env,
                check=check
            )
            
            # Handle command output
            if result.stdout:
                # For git commands, check if output is informational
                if cmd[0] == "git":
                    # These are normal git operation messages, not errors
                    if any(x in result.stdout for x in [
                        "->", "branch", "origin", "Switched to", "up to date",
                        "file changed", "insertion", "deletion",
                        "create mode", "rename", "Already on"
                    ]):
                        self.output_message(result.stdout)
                    else:
                        self.output_message(f"Command output: {result.stdout}")
                else:
                    self.output_message(f"Command output: {result.stdout}")
            
            # Handle command stderr
            if result.stderr:
                # For git commands, check if stderr is informational
                if cmd[0] == "git":
                    # These are normal git operation messages that come through stderr
                    if any(x in result.stderr for x in [
                        "remote:", "origin/master", "->", "FETCH_HEAD",
                        "Everything up-to-date", "master -> master"
                    ]):
                        self.output_message(result.stderr)
                    else:
                        self.output_message(f"Warning: {result.stderr}")
                else:
                    self.output_message(f"Warning: {result.stderr}")
            
            return result
            
        except subprocess.TimeoutExpired:
            self.output_message(f"Error: Command timed out after {timeout} seconds: {' '.join(cmd)}")
            raise
        except subprocess.CalledProcessError as e:
            # Check if this is actually an error or just git information
            if cmd[0] == "git" and e.stderr and any(x in e.stderr for x in [
                "remote:", "origin/master", "->", "FETCH_HEAD",
                "Everything up-to-date", "master -> master"
            ]):
                self.output_message(e.stderr)
                if not check:  # If we're not checking return code, continue
                    return e
            else:
                self.output_message(f"Error: Command failed with exit code {e.returncode}:")
                self.output_message(f"Command: {' '.join(cmd)}")
                if e.stdout:
                    self.output_message(f"Output: {e.stdout}")
                if e.stderr:
                    self.output_message(f"Error: {e.stderr}")
            raise
        except Exception as e:
            self.output_message(f"Error: Unexpected error running command: {e}")
            raise

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
                self.output_message("No changes to commit")
                return
            
            # Add and commit changes
            self.output_message("Adding and committing changes...")
            self._run_command(["git", "add", "."])
            self._run_command(["git", "commit", "-m", f"Release v{self.version}"])
            
            # Create and push tag
            self.output_message("Creating and pushing tag...")
            tag_result = self._run_command(["git", "tag", "-a", f"v{self.version}", "-m", f"Release v{self.version}"])
            self.output_message(f"Tag creation output: {tag_result.stdout}")
            push_tag_result = self._run_command(["git", "push", "origin", f"v{self.version}"])
            self.output_message(f"Tag push output: {push_tag_result.stdout}")
            
            # Wait a moment for GitHub to process the tag
            time.sleep(5)
            
            # Create source archive in dist directory
            self.output_message("Creating source archive...")
            dist_dir = self.project_dir / "dist"
            dist_dir.mkdir(exist_ok=True)
            
            archive_name = f"{self.project_dir.name}-{self.version}"
            archive_path = dist_dir / f"{archive_name}.tar.gz"
            
            # Create archive with explicit prefix and all files from the current tag
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
            
            # Create GitHub release
            self.output_message("Creating GitHub release...")
            
            # Find built package in dist directory
            pkg_glob = f"{self.project_dir.name}-{self.version}-*-{arch}.pkg.tar.zst"
            pkg_file = next(dist_dir.glob(pkg_glob), None)
            
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
                self.output_message("Running: " + " ".join(release_args))
                release_result = self._run_command(release_args)
                self.output_message(f"Release creation output: {release_result.stdout}")
                
                # Then upload the assets separately
                self.output_message("Uploading release assets...")
                
                # Upload source archive
                upload_args = [
                    "gh", "release", "upload",
                    f"v{self.version}",
                    str(archive_path),
                    "--clobber"  # Overwrite existing asset if needed
                ]
                self.output_message("Running: " + " ".join(upload_args))
                upload_result = self._run_command(upload_args)
                self.output_message(f"Upload output: {upload_result.stdout}")

                # Calculate SHA256 of the GitHub release file
                self.output_message("Calculating SHA256 of GitHub release file...")
                sha256_result = self._run_command([
                    "bash", "-c",
                    f"curl -L {self.url}/archive/v{self.version}.tar.gz | sha256sum"
                ])
                sha256 = sha256_result.stdout.split()[0]

                # Update PKGBUILD with proper multiline handling
                pkgbuild_path = self.project_dir / "PKGBUILD"
                with pkgbuild_path.open('r') as f:
                    content = f.read()

                # Extract the helper functions before modifying the content
                helper_functions = ""
                if "# Get version from PKGBUILD" in content:
                    helper_functions = content[content.find("# Get version from PKGBUILD"):]

                # Update version - only match the actual version line, not the function
                content = re.sub(
                    r'^pkgver=[0-9][0-9a-zA-Z.-]*$',
                    f'pkgver={self.version}',
                    content,
                    flags=re.MULTILINE
                )

                # Update source array
                content = re.sub(
                    r'source=\([^)]*\)',
                    'source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")',
                    content,
                    flags=re.MULTILINE | re.DOTALL
                )

                # Handle both single and multiline sha256sums formats
                content = re.sub(
                    r'sha256sums=\([^)]*\)',
                    f'sha256sums=("{sha256}")',
                    content,
                    flags=re.MULTILINE | re.DOTALL
                )

                # Remove any existing helper functions from the content
                if "# Get version from PKGBUILD" in content:
                    content = content[:content.find("# Get version from PKGBUILD")]

                # Append the helper functions back
                if helper_functions:
                    content = content.rstrip() + "\n\n" + helper_functions

                with pkgbuild_path.open('w') as f:
                    f.write(content)
                
                # Upload package if it exists
                if pkg_file:
                    pkg_upload_args = [
                        "gh", "release", "upload",
                        f"v{self.version}",
                        str(pkg_file),
                        "--clobber"
                    ]
                    self.output_message("Running: " + " ".join(pkg_upload_args))
                    pkg_upload_result = self._run_command(pkg_upload_args)
                    self.output_message(f"Package upload output: {pkg_upload_result.stdout}")
                
                # Verify release assets with retries
                if not self._verify_release_assets(self.version):
                    raise Exception("Failed to verify release assets after maximum retries")
                
                self.output_message("GitHub release created and verified successfully")
                
            except Exception as e:
                self.output_message(f"Error creating GitHub release: {e}")
                raise
        except Exception as e:
            self.output_message(f"Error in GitHub release process: {e}")
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
        self.output_message("Switching to master branch...")
        
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
            self.output_message("Calculating SHA256 of GitHub release file...")
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
            raise

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
            
        # Check Git status before proceeding
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )
            if result.stdout.strip():
                reply = QMessageBox.question(
                    self,
                    "Uncommitted Changes",
                    "There are uncommitted changes in your repository. Would you like to:\n\n"
                    "Yes = Commit all changes before release\n"
                    "No = Cancel release process\n"
                    "Save = Stash changes and proceed",
                    QMessageBox.StandardButton.Yes |
                    QMessageBox.StandardButton.No |
                    QMessageBox.StandardButton.Save
                )
                
                if reply == QMessageBox.StandardButton.No:
                    return
                elif reply == QMessageBox.StandardButton.Save:
                    # Stash changes
                    subprocess.run(
                        ["git", "stash", "save", "Pre-release stash"],
                        cwd=project_path,
                        check=True
                    )
                    self.release_output.append("Changes stashed successfully")
                elif reply == QMessageBox.StandardButton.Yes:
                    # Commit changes
                    subprocess.run(
                        ["git", "add", "."],
                        cwd=project_path,
                        check=True
                    )
                    subprocess.run(
                        ["git", "commit", "-m", "Pre-release commit"],
                        cwd=project_path,
                        check=True
                    )
                    self.release_output.append("Changes committed successfully")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Git operation failed: {e.stderr}")
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to check Git status: {str(e)}")
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

    def on_release_complete(self):
        """Handle completion of release process"""
        self.release_start_button.setEnabled(True)
        self.release_output.append("\nRelease process completed")

    def update_progress(self, message: str):
        """Update progress message in the output"""
        self.release_output.append(message)
        # Show progress bar during long operations
        if any(x in message for x in ["Building package", "Creating GitHub release", "Updating AUR package"]):
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.progress_bar.show()
        elif "completed" in message.lower():
            self.progress_bar.hide()
        # Ensure the new text is visible
        cursor = self.release_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.release_output.setTextCursor(cursor)

    def show_error(self, message: str):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)
        self.release_start_button.setEnabled(True)

    def update_output(self, text: str):
        """Update output text"""
        self.release_output.append(text)
        # Ensure the new text is visible
        cursor = self.release_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.release_output.setTextCursor(cursor)
