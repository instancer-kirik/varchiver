print("Loading release_manager module")

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLineEdit, QLabel, QComboBox, QProgressBar, QMessageBox, QDialog,
                            QFileDialog, QGroupBox, QFormLayout, QTextEdit, QApplication, QCheckBox)
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QSettings, pyqtSlot, QDir, QMetaObject, Qt, Q_ARG
from PyQt6.QtGui import QTextCursor
import subprocess
import os
import re
from pathlib import Path
import time
from typing import List, Optional
from .project_constants import PROJECT_CONFIGS
import shutil
import requests
from PIL import Image, ImageDraw

print("Imports completed in release_manager module")

class ReleaseThread(QThread):
    # Define signals
    progress = pyqtSignal(str)  # For progress bar and output widget
    error = pyqtSignal(str)     # For error messages
    finished = pyqtSignal(bool) # For completion status
    dialog_signal = pyqtSignal(str, str, list)  # For user interaction dialogs
    
    def __init__(self, project_dir: Path, version: str, tasks: List[str], output_widget: QTextEdit, 
                 use_aur: bool = False, aur_dir: Optional[Path] = None, build_appimage: bool = False):
        super().__init__()
        # Initialize basic attributes
        self.project_dir = project_dir
        self.version = version
        self.tasks = tasks
        self.output_widget = output_widget
        self.use_aur = use_aur
        self.aur_dir = aur_dir
        self.build_appimage = build_appimage
        
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
            'PKGBUILD': r'^pkgver=[0-9][0-9a-z.-]*$'
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
        """Thread-safe message output."""
        try:
            # Write to log file first
            if self.log_file:
                with open(self.log_file, 'a') as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
            
            # Update UI via signal
            if hasattr(self, 'output_widget') and self.output_widget:
                self.progress.emit(message)
                
        except Exception as e:
            print(f"Error in output_message: {e}")
            # Don't try to emit signal here to avoid potential recursion

    def handle_dialog_response(self, response):
        """Handle dialog response in a thread-safe way"""
        self.dialog_response = response
        self.wait_for_dialog = False

    def run(self):
        """Main release process with improved error handling"""
        try:
            self.output_message(f"Starting release process for version {self.version}")
            
            # Always check for unpushed commits first if check_changes is in tasks
            if "check_changes" in self.tasks:
                if not self._handle_git_status():
                    return  # Git status handling failed or was cancelled
            
            try:
                # Update version files if needed
                if 'update_version' in self.tasks:
                    self._update_version_files()
                    self._commit_version_changes(self.version)
                
                # Build source package first (required for both GitHub release and AUR)
                if 'build_packages' in self.tasks:
                    self.output_message("\nBuilding source package...")
                self._build_packages()
                
                # Build AppImage if requested
                if 'build_appimage' in self.tasks:
                    self.output_message("\nBuilding AppImage...")
                    self._build_appimage()
                
                # Create GitHub release if requested
                if 'create_release' in self.tasks:
                    self.output_message("\nCreating GitHub release...")
                    self._check_github_authentication()
                    self._create_github_release()
                    
                # Update AUR if requested (needs source package)
                if 'update_aur' in self.tasks and self.use_aur and self.aur_dir:
                    self.output_message("\nUpdating AUR package...")
                    self._update_aur()
                
                self.output_message("\nRelease process completed successfully!")
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

    def _commit_version_changes(self, version: str) -> bool:
        """Commit version changes to repository."""
        try:
            # Check if there are any changes to commit
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse status output
            status_lines = result.stdout.splitlines()
            modified_files = [line[3:] for line in status_lines if line.startswith(' M') or line.startswith('M ')]
            untracked_files = [line[3:] for line in status_lines if line.startswith('??')]
            
            if not modified_files and not untracked_files:
                self.output_message("No changes to commit")
                return True
            
            # Handle untracked files
            if untracked_files:
                self.output_message(f"\nUntracked files found:")
                for file in untracked_files:
                    self.output_message(f"- {file}")
                
                # Ask user what to do with untracked files
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Question)
                msg.setText("Untracked files found")
                msg.setInformativeText("What would you like to do with the untracked files?")
                ignore_btn = msg.addButton("Ignore", QMessageBox.ButtonRole.RejectRole)
                add_btn = msg.addButton("Add to Git", QMessageBox.ButtonRole.AcceptRole)
                cancel_btn = msg.addButton("Cancel Release", QMessageBox.ButtonRole.DestructiveRole)
                msg.exec()
                
                if msg.clickedButton() == add_btn:
                    # Add untracked files
                    for file in untracked_files:
                        subprocess.run(
                            ['git', 'add', file],
                            cwd=self.project_dir,
                            check=True
                        )
                    self.output_message("Added untracked files to Git")
                elif msg.clickedButton() == cancel_btn:
                    raise Exception("Release cancelled by user")
                # If ignore_btn, continue without adding untracked files
            
            # Check if there are modified files to commit
            result = subprocess.run(
                ['git', 'status', '--porcelain', '--untracked-files=no'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                # Add modified files
                subprocess.run(
                    ['git', 'add', 'pyproject.toml', 'PKGBUILD'],
                    cwd=self.project_dir,
                    check=True
                )
                
                # Commit changes
                try:
                    subprocess.run(
                        ['git', 'commit', '-m', f'Release v{version}'],
                        cwd=self.project_dir,
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    self.output_message(f"Committed version changes for v{version}")
                except subprocess.CalledProcessError as e:
                    if "nothing to commit" in e.stderr:
                        self.output_message("No changes to commit")
                        return True
                    raise
                
            return True

        except Exception as e:
            self.output_message(f"Warning: Failed to commit version changes: {str(e)}")
            return False

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

    def _build_packages(self) -> bool:
        """Build distribution packages."""
        try:
            # Create dist directory if it doesn't exist
            dist_dir = self.project_dir / 'dist'
            dist_dir.mkdir(exist_ok=True)
            
            # Build source distribution (required for AUR)
            self.output_message("\nBuilding source distribution...")
            version = self._get_version()
            archive_name = f"{self.project_dir.name}-{version}"
            archive_file = f"{archive_name}.tar.gz"
            
            subprocess.run(
                ['git', 'archive', '--format=tar.gz',
                 f'--prefix={archive_name}/', '-o',
                 str(dist_dir / archive_file), 'HEAD'],
                cwd=self.project_dir,
                check=True
            )
            
            # Copy archive to current directory for makepkg
            shutil.copy2(dist_dir / archive_file, archive_file)
            
            # Get SHA256 sum
            result = subprocess.run(
                ['sha256sum', str(dist_dir / archive_file)],
                capture_output=True,
                text=True,
                check=True
            )
            local_sha256 = result.stdout.split()[0]
            
            # Update PKGBUILD
            self._update_pkgbuild(version, local_sha256)
            
            # Run makepkg
            self.output_message("Starting makepkg process...")
            subprocess.run(['makepkg', '-f'], check=True)
            
            # Build AppImage if requested
            if self.build_appimage:
                self.output_message("\nBuilding AppImage...")
                try:
                    self._build_appimage()
                except Exception as e:
                    self.output_message(f"Warning: AppImage build failed: {str(e)}")
            
            return True
            
        except Exception as e:
            self.output_message(f"Error during build: {str(e)}")
            return False

    def _get_version(self) -> str:
        """Get version from PKGBUILD or other version files."""
        try:
            # First try PKGBUILD
            pkgbuild = self.project_dir / "PKGBUILD"
            if pkgbuild.exists():
                content = pkgbuild.read_text()
                match = re.search(r'pkgver=([0-9][0-9a-z.-]*)', content)
                if match:
                    return match.group(1)
            
            # Try other common version files
            version_files = [
                (self.project_dir / "pyproject.toml", r'version\s*=\s*["\']([^"\']+)["\']'),
                (self.project_dir / "package.json", r'"version":\s*"([^"]+)"'),
                (self.project_dir / "Cargo.toml", r'version\s*=\s*"([^"]+)"')
            ]
            
            for file_path, pattern in version_files:
                if file_path.exists():
                    content = file_path.read_text()
                    match = re.search(pattern, content)
                    if match:
                        return match.group(1)
            
            raise Exception("Could not determine version from any source files")
            
        except Exception as e:
            raise Exception(f"Error getting version: {str(e)}")

    def _build_appimage(self):
        """Build AppImage package."""
        try:
            # Create AppImage build directory
            appimage_dir = self.project_dir / 'build' / 'AppDir'
            appimage_dir.mkdir(parents=True, exist_ok=True)
            
            # Create basic AppDir structure
            (appimage_dir / 'usr' / 'bin').mkdir(parents=True, exist_ok=True)
            (appimage_dir / 'usr' / 'lib').mkdir(parents=True, exist_ok=True)
            
            # Copy application files
            package_name = self.project_dir.name.replace('-', '_')
            src_dir = self.project_dir / package_name
            if src_dir.exists():
                shutil.copytree(
                    src_dir,
                    appimage_dir / 'usr' / 'lib' / 'python3' / 'site-packages' / package_name,
                    dirs_exist_ok=True
                )
            
            # Create entry point script
            entry_point = appimage_dir / 'usr' / 'bin' / package_name
            entry_point.write_text("""#!/usr/bin/env python3
import sys
import os

# Add application to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib/python3/site-packages'))

from {0}.main import main
if __name__ == '__main__':
    sys.exit(main())
""".format(package_name))
            entry_point.chmod(0o755)
            
            # Create desktop file
            desktop_file = appimage_dir / f"{package_name}.desktop"
            desktop_file.write_text("""[Desktop Entry]
Name={0}
Exec={0}
Icon={0}
Type=Application
Categories=Utility;
""".format(package_name))
            
            # Create icons in multiple sizes
            icon_sizes = [16, 32, 48, 64, 128, 256]
            icons_dir = appimage_dir / "usr" / "share" / "icons" / "hicolor"
            
            for size in icon_sizes:
                size_dir = icons_dir / f"{size}x{size}" / "apps"
                size_dir.mkdir(parents=True, exist_ok=True)
                icon_path = size_dir / f"{package_name}.png"
                
                try:
                    # Create a new image with a blue background
                    img = Image.new('RGB', (size, size), color='#2196F3')
                    draw = ImageDraw.Draw(img)
                    
                    # Draw a darker blue border
                    border_width = max(1, size // 32)  # Scale border width with icon size
                    draw.rectangle([0, 0, size-1, size-1], outline='#1976D2', width=border_width)
                    
                    # Save the icon
                    img.save(str(icon_path))
                    self.output_message(f"Created {size}x{size} icon at: {icon_path}")
                except Exception as e:
                    self.output_message(f"Warning: Failed to create {size}x{size} icon: {e}")
            
            # Create symlink for the main icon
            main_icon = appimage_dir / f"{package_name}.png"
            if not main_icon.exists():
                largest_icon = icons_dir / "256x256" / "apps" / f"{package_name}.png"
                if largest_icon.exists():
                    try:
                        main_icon.symlink_to(largest_icon)
                        self.output_message(f"Created symlink for main icon at: {main_icon}")
                    except Exception as e:
                        self.output_message(f"Warning: Failed to create icon symlink: {e}")
                        # If symlink fails, copy the file instead
                        try:
                            shutil.copy2(largest_icon, main_icon)
                            self.output_message(f"Copied main icon to: {main_icon}")
                        except Exception as e:
                            self.output_message(f"Warning: Failed to copy icon: {e}")
            
            # Create AppRun
            apprun = appimage_dir / 'AppRun'
            apprun.write_text("""#!/bin/sh
HERE="$(dirname "$(readlink -f "${0}")")"
export PYTHONPATH="$HERE/usr/lib/python3/site-packages:$PYTHONPATH"
export PATH="$HERE/usr/bin:$PATH"
exec "$HERE/usr/bin/python3" "$HERE/usr/bin/{0}" "$@"
""".format(package_name))
            apprun.chmod(0o755)
            
            # Download and set up AppImage tools
            tools_dir = self.project_dir / 'build' / 'tools'
            tools_dir.mkdir(exist_ok=True)
            
            appimagetool = tools_dir / 'appimagetool'
            if not appimagetool.exists():
                self.output_message("Downloading appimagetool...")
                url = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
                response = requests.get(url)
                appimagetool.write_bytes(response.content)
                appimagetool.chmod(0o755)
                
                # Initialize the AppImage tool
                try:
                    subprocess.run([str(appimagetool), '--appimage-extract-and-run', '--version'], check=True)
                except subprocess.CalledProcessError:
                    # If direct execution fails, try extracting
                    self.output_message("Initializing appimagetool...")
                    subprocess.run([str(appimagetool), '--appimage-extract'], cwd=tools_dir, check=True)
                    # Use the extracted version
                    appimagetool = tools_dir / 'squashfs-root' / 'AppRun'
            
            # Build AppImage
            version = self._get_version()
            output_file = self.project_dir / 'dist' / f"{package_name}-{version}-x86_64.AppImage"
            
            # Ensure python3 is in the AppDir
            python_dir = appimage_dir / 'usr' / 'bin'
            if not (python_dir / 'python3').exists():
                os.symlink('/usr/bin/python3', python_dir / 'python3')
            
            self.output_message("Building AppImage...")
            # Set up environment with ARCH variable
            env = os.environ.copy()
            env['ARCH'] = 'x86_64'  # Set architecture explicitly
            
            result = subprocess.run(
                [str(appimagetool), '--appimage-extract-and-run', str(appimage_dir), str(output_file)],
                capture_output=True,
                text=True,
                env=env  # Pass the environment with ARCH set
            )
            
            if result.returncode != 0:
                raise Exception(f"AppImage build failed: {result.stderr}")
            
            self.output_message(f"AppImage created: {output_file}")
            
        except Exception as e:
            raise Exception(f"AppImage build failed: {str(e)}")

    def _verify_release_assets(self, version, max_retries=20, retry_delay=15):
        """Verify release assets with retries"""
        archive_name = f"{self.project_dir.name}-{version}.tar.gz"
        archive_url = f"{self.url}/archive/v{version}/{archive_name}"
        
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
                
                # Then verify the source archive is downloadable
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
        
        # Clean up dist directory first
        dist_dir = self.project_dir / "dist"
        if dist_dir.exists():
            self.output_message("Cleaning up old distribution files...")
            for file in dist_dir.glob('*'):
                if file.is_file():
                    file.unlink()
        dist_dir.mkdir(exist_ok=True)
        
        # Create source archive first
        self.output_message("Creating source archive...")
        archive_name = f"{self.project_dir.name}-{self.version}.tar.gz"
        archive_path = self.project_dir / "dist" / archive_name
        
        # Create source archive using git archive
        self._run_command([
            "git", "archive",
            "--format=tar.gz",
            f"--prefix={self.project_dir.name}-{self.version}/",
            "-o", str(archive_path),
            "HEAD"
        ])
        
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
        release_notes = self._create_release_notes(self.version)
        
        # Create the release using gh cli, including only current version files
        self._run_command([
            'gh', 'release', 'create', tag,
            '--title', f'Release {tag}',
            '--notes', release_notes,
            str(archive_path)  # Only include the current version source archive
        ], timeout=300)  # 5 minutes timeout
        
        # Verify release and wait for it to be available
        if not self._verify_release_assets(self.version):
            raise Exception("Failed to verify release assets after creation")
            
        # Calculate SHA256 from GitHub release
        self.output_message("Calculating SHA256 of GitHub release file...")
        max_retries = 5
        sha256 = None
        
        for attempt in range(max_retries):
            try:
                time.sleep(5 * (attempt + 1))  # Increasing delay between attempts
                sha256_result = self._run_command([
                    "bash", "-c",
                    f"curl -L {self.url}/archive/v{self.version}.tar.gz | sha256sum"
                ], timeout=60)
                sha256 = sha256_result.stdout.split()[0]
                
                if not re.match(r'^[a-f0-9]{64}$', sha256):
                    raise Exception(f"Invalid SHA256 sum calculated: {sha256}")
                    
                # Verify the SHA256 by downloading and checking
                verify_result = self._run_command([
                    "bash", "-c",
                    f"curl -L {self.url}/archive/v{self.version}.tar.gz | sha256sum -c --status <(echo {sha256}  -)"
                ], check=False)
                
                if verify_result.returncode == 0:
                    self.output_message(f"SHA256 verified: {sha256}")
                    break
                else:
                    raise Exception("SHA256 verification failed")
                    
            except Exception as e:
                self.output_message(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise Exception("Failed to calculate and verify SHA256 after multiple attempts")
        
        # Update PKGBUILD with SHA256
        pkgbuild_path = self.project_dir / "PKGBUILD"
        with open(pkgbuild_path, 'r') as f:
            pkgbuild_content = f.read()
            
        # Update source URL to use GitHub release
        pkgbuild_content = re.sub(
            r'source=\([^)]*\)',
            f'source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")',
            pkgbuild_content,
            flags=re.MULTILINE | re.DOTALL
        )
            
        pkgbuild_content = self._update_pkgbuild_sha256(pkgbuild_content, sha256)
        
        with open(pkgbuild_path, 'w') as f:
            f.write(pkgbuild_content)
        
        # Commit PKGBUILD changes
        self._run_command(['git', 'add', 'PKGBUILD'])
        self._run_command(['git', 'commit', '-m', f'Update PKGBUILD SHA256 for {self.version}'])
        
        # Push all changes
        self.output_message("Pushing changes to remote...")
        self._run_command(['git', 'push', 'origin', 'HEAD'])
        
        self.output_message(f"\nGitHub release {tag} created and verified successfully!")

    def _update_aur(self):
        """Update AUR package with proper .SRCINFO handling"""
        if not self.use_aur:
            return
            
        self.progress.emit("Updating AUR package...")
        
        # First verify that the GitHub release exists and is accessible
        self.output_message("Verifying GitHub release is available...")
        if not self._verify_release_assets(self.version, max_retries=10, retry_delay=10):
            raise Exception("GitHub release is not available. Cannot update AUR package.")
        
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
            
            # Update source array
            pkgbuild_content = re.sub(
                r'source=\([^)]*\)',
                f'source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")',
                pkgbuild_content,
                flags=re.MULTILINE | re.DOTALL
            )
            
            # Calculate SHA256 with retries
            self.output_message("Calculating SHA256 of GitHub release file...")
            max_retries = 5
            sha256 = None
            
            for attempt in range(max_retries):
                try:
                    time.sleep(5 * (attempt + 1))  # Increasing delay between attempts
                    sha256_result = self._run_command([
                        "bash", "-c",
                        f"curl -L {self.url}/archive/v{self.version}.tar.gz | sha256sum"
                    ], timeout=60)
                    sha256 = sha256_result.stdout.split()[0]
                    
                    if not re.match(r'^[a-f0-9]{64}$', sha256):
                        raise Exception(f"Invalid SHA256 sum calculated: {sha256}")
                        
                    # Verify the SHA256 by downloading and checking
                    verify_result = self._run_command([
                        "bash", "-c",
                        f"curl -L {self.url}/archive/v{self.version}.tar.gz | sha256sum -c --status <(echo {sha256}  -)"
                    ], check=False)
                    
                    if verify_result.returncode == 0:
                        self.output_message(f"SHA256 verified: {sha256}")
                        break
                    else:
                        raise Exception("SHA256 verification failed")
                        
                except Exception as e:
                    self.output_message(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise Exception("Failed to calculate and verify SHA256 after multiple attempts")
            
            # Update SHA256 sum
            pkgbuild_content = self._update_pkgbuild_sha256(pkgbuild_content, sha256)
            
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

    def _update_pkgbuild_sha256(self, pkgbuild_content: str, sha256: str) -> str:
        """Update SHA256 sum in PKGBUILD content"""
        return re.sub(
            r'sha256sums=\([^)]*\)',
            f'sha256sums=("{sha256}")',
            pkgbuild_content,
            flags=re.MULTILINE | re.DOTALL
        )

    def _create_release_notes(self, version: str) -> str:
        """Create release notes for the new version."""
        try:
            # Get commits since last tag
            last_tag = self._get_last_tag()
            if last_tag:
                result = subprocess.run(
                    ['git', 'log', f'{last_tag}..HEAD', '--oneline'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    check=True
                )
                commits = result.stdout.strip()
            else:
                result = subprocess.run(
                    ['git', 'log', '--oneline'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    check=True
                )
                commits = result.stdout.strip()
            
            # Format release notes
            notes = [
                f"# Release v{version}",
                "",
                "## Changes",
                commits if commits else "No changes recorded",
                "",
                "## Support Development",
                "If you find this project useful, consider supporting its development:",
                "",
                "Varchiver - ETH: `0xaF462Cef9E8913a9Cb7B6f0bA0DDf5d733Eae57a`",
                "",
                "Released Project: PLACEHOLDER",
                "",
                "## Installation",
                "Available on the AUR:",
                "",
                "```bash",
                f"yay -S {self.project_dir.name}",
                "```"
            ]
            
            return "\n".join(notes)
            
        except Exception as e:
            self.output_message(f"Warning: Failed to create release notes: {str(e)}")
            return f"Release v{version}"

    def _update_pkgbuild(self, version: str, sha256: str):
        """Update PKGBUILD with new version and SHA256."""
        try:
            pkgbuild_path = self.project_dir / "PKGBUILD"
            if not pkgbuild_path.exists():
                raise Exception("PKGBUILD not found")
                
            content = pkgbuild_path.read_text()
            
            # Update version
            content = re.sub(
                r'^pkgver=.*$',
                f'pkgver={version}',
                content,
                flags=re.MULTILINE
            )
            
            # Update SHA256
            content = re.sub(
                r'sha256sums=\([^)]*\)',
                f'sha256sums=("{sha256}")',
                content,
                flags=re.MULTILINE | re.DOTALL
            )
            
            # Write updated content
            pkgbuild_path.write_text(content)
            self.output_message(f"Updated PKGBUILD with version {version} and SHA256")
            
        except Exception as e:
            raise Exception(f"Failed to update PKGBUILD: {str(e)}")


class ReleaseManager(QWidget):
    """Manages the release process."""
    
    # Signals
    progress = pyqtSignal(str)  # For progress bar and output widget
    error = pyqtSignal(str)     # For error messages
    finished = pyqtSignal(bool) # For completion status
    dialog_signal = pyqtSignal(str, str, list)  # For user interaction dialogs
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_dir = None
        self.release_thread = None
        self.init_ui()

    def browse_project_dir(self):
        """Open dialog to select project directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Project Directory",
            self.project_dir_input.text() or str(Path.home())
        )
        if dir_path:
            self.project_dir_input.setText(dir_path)
            self.project_dir = Path(dir_path)
            
    def cancel_release(self):
        """Cancel the release process."""
        if self.release_thread and self.release_thread.isRunning():
            self.release_thread.terminate()
            self.release_thread.wait()
            self.output_display.append("Release process cancelled.")

    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        layout.setSpacing(10)  # Default spacing
        
        # Add compact view toggle button in the top-right
        compact_layout = QHBoxLayout()
        compact_layout.addStretch()
        self.compact_btn = QPushButton("Compact View")
        self.compact_btn.setCheckable(True)
        self.compact_btn.clicked.connect(self.toggle_compact_view)
        self.compact_btn.setFixedWidth(100)
        compact_layout.addWidget(self.compact_btn)
        layout.addLayout(compact_layout)
        
        # Project directory selection
        project_dir_layout = QHBoxLayout()
        self.project_dir_label = QLabel("Project Directory:")
        self.project_dir_input = QLineEdit()
        self.project_dir_button = QPushButton("Browse")
        self.project_dir_button.clicked.connect(self.browse_project_dir)
        project_dir_layout.addWidget(self.project_dir_label)
        project_dir_layout.addWidget(self.project_dir_input)
        project_dir_layout.addWidget(self.project_dir_button)
        layout.addLayout(project_dir_layout)
        
        # Version input
        version_layout = QHBoxLayout()
        self.version_label = QLabel("Version:")
        self.version_input = QLineEdit()
        version_layout.addWidget(self.version_label)
        version_layout.addWidget(self.version_input)
        layout.addLayout(version_layout)
        
        # Task selection group
        task_group = QGroupBox("Release Tasks")
        task_layout = QVBoxLayout()
        task_layout.setSpacing(6)  # Tighter spacing for checkboxes
        
        # Core tasks
        self.check_changes_cb = QCheckBox("Check for unpushed changes")
        self.update_version_cb = QCheckBox("Update version numbers")
        self.build_packages_cb = QCheckBox("Build source package")
        self.build_appimage_cb = QCheckBox("Build AppImage")
        self.create_release_cb = QCheckBox("Create GitHub release")
        self.update_aur_cb = QCheckBox("Update AUR package")
        
        # Add tasks to layout
        task_layout.addWidget(self.check_changes_cb)
        task_layout.addWidget(self.update_version_cb)
        task_layout.addWidget(self.build_packages_cb)
        task_layout.addWidget(self.build_appimage_cb)
        task_layout.addWidget(self.create_release_cb)
        task_layout.addWidget(self.update_aur_cb)
        
        # Task presets
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Task Preset:")
        self.task_preset = QComboBox()
        self.task_preset.addItems([
            "Full Release (All Tasks)",
            "Full Release (No AUR)",
            "Build + Release (Source + AppImage)",
            "Build + Release (Source Only)",
            "Create Release Only",
            "Update AUR Only"
        ])
        self.task_preset.currentIndexChanged.connect(self.update_task_selection)
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.task_preset)
        task_layout.addLayout(preset_layout)
        
        task_group.setLayout(task_layout)
        layout.addWidget(task_group)
        
        # Output display
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(self.output_display)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Release")
        self.start_button.clicked.connect(self.start_release_process)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_release)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Set initial state to "Full Release (All Tasks)"
        self.task_preset.setCurrentIndex(0)
        self.update_task_selection(0)
        
    def toggle_compact_view(self, checked: bool):
        """Toggle between compact and normal view."""
        layout = self.layout()
        if checked:
            # Compact view
            layout.setSpacing(4)
            layout.setContentsMargins(4, 4, 4, 4)
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if isinstance(item, QHBoxLayout):
                    item.setSpacing(4)
                elif isinstance(item, QVBoxLayout):
                    item.setSpacing(4)
                widget = item.widget()
                if isinstance(widget, QGroupBox):
                    widget.layout().setSpacing(2)
                    widget.layout().setContentsMargins(4, 4, 4, 4)
        else:
            # Normal view
            layout.setSpacing(10)
            layout.setContentsMargins(11, 11, 11, 11)
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if isinstance(item, QHBoxLayout):
                    item.setSpacing(10)
                elif isinstance(item, QVBoxLayout):
                    item.setSpacing(10)
                widget = item.widget()
                if isinstance(widget, QGroupBox):
                    widget.layout().setSpacing(6)
                    widget.layout().setContentsMargins(11, 11, 11, 11)
        
        # Update window size
        self.adjustSize()

    def update_task_selection(self, index):
        """Update task checkboxes based on preset selection."""
        # Clear all checkboxes first
        self.check_changes_cb.setChecked(False)
        self.update_version_cb.setChecked(False)
        self.build_packages_cb.setChecked(False)
        self.build_appimage_cb.setChecked(False)
        self.create_release_cb.setChecked(False)
        self.update_aur_cb.setChecked(False)
        
        # Set checkboxes based on preset
        if index == 0:  # Full Release (All Tasks)
            self.check_changes_cb.setChecked(True)
            self.update_version_cb.setChecked(True)
            self.build_packages_cb.setChecked(True)
            self.build_appimage_cb.setChecked(True)
            self.create_release_cb.setChecked(True)
            self.update_aur_cb.setChecked(True)
        elif index == 1:  # Full Release (No AUR)
            self.check_changes_cb.setChecked(True)
            self.update_version_cb.setChecked(True)
            self.build_packages_cb.setChecked(True)
            self.build_appimage_cb.setChecked(True)
            self.create_release_cb.setChecked(True)
        elif index == 2:  # Build + Release (Source + AppImage)
            self.check_changes_cb.setChecked(True)
            self.build_packages_cb.setChecked(True)
            self.build_appimage_cb.setChecked(True)
            self.create_release_cb.setChecked(True)
        elif index == 3:  # Build + Release (Source Only)
            self.check_changes_cb.setChecked(True)
            self.build_packages_cb.setChecked(True)
            self.create_release_cb.setChecked(True)
        elif index == 4:  # Create Release Only
            self.check_changes_cb.setChecked(True)
            self.create_release_cb.setChecked(True)
        elif index == 5:  # Update AUR Only
            self.check_changes_cb.setChecked(True)
            self.update_aur_cb.setChecked(True)
            
    def start_release_process(self):
        """Start the release process with selected tasks."""
        if not self.project_dir_input.text():
            QMessageBox.critical(self, "Error", "Project directory is required")
            return
            
        version = self.version_input.text().strip()
        if not version:
            QMessageBox.critical(self, "Error", "Version number is required")
            return
            
        # Collect selected tasks
        tasks = []
        if self.check_changes_cb.isChecked():
            tasks.append("check_changes")
        if self.update_version_cb.isChecked():
            tasks.append("update_version")
        if self.build_packages_cb.isChecked():
            tasks.append("build_packages")
        if self.build_appimage_cb.isChecked():
            tasks.append("build_appimage")
        if self.create_release_cb.isChecked():
            tasks.append("create_release")
        if self.update_aur_cb.isChecked():
            tasks.append("update_aur")
            
        # Start the release process
        self.start_release(
            version,
            tasks,
            self.output_display,
            use_aur="update_aur" in tasks
        )

    def start_release(self, version: str, tasks: list, output_widget: QTextEdit,
                     use_aur: bool = False, aur_dir: Optional[Path] = None):
        """Start the release process."""
        if not self.project_dir:
            raise RuntimeError("Project directory not set")
            
        # Create and start release thread
        self.release_thread = ReleaseThread(
            self.project_dir,
            version,
            tasks,  # Use the tasks list passed from start_release_process
            output_widget,
            use_aur=use_aur,
            aur_dir=aur_dir,
            build_appimage='build_appimage' in tasks  # Pass AppImage flag based on task selection
        )
        
        # Connect signals to different slot names to avoid recursion
        self.release_thread.progress.connect(self._on_release_progress)
        self.release_thread.error.connect(self._on_release_error)
        self.release_thread.finished.connect(self._on_release_finished)
        self.release_thread.dialog_signal.connect(self._on_release_dialog)
        
        # Start thread
        self.release_thread.start()
        
    def _on_release_progress(self, message: str):
        """Handle progress updates from release thread."""
        if hasattr(self, 'output_display') and self.output_display:
            self.output_display.append(message)
            # Scroll to bottom
            cursor = self.output_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.output_display.setTextCursor(cursor)
        
    def _on_release_error(self, error_msg: str):
        """Handle errors from release thread."""
        QMessageBox.critical(self, "Error", error_msg)
        
    def _on_release_finished(self, success: bool):
        """Handle release thread completion."""
        if success:
            QMessageBox.information(self, "Success", "Release process completed successfully!")
        
    def _on_release_dialog(self, title: str, message: str, options: list):
        """Handle dialog requests from release thread."""
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
            