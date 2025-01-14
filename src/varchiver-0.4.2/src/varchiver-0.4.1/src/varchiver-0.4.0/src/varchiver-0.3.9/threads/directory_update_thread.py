from PyQt6.QtCore import QThread, pyqtSignal
import os
import shutil
import zipfile
import tarfile
import rarfile
import fnmatch
from pathlib import Path
from ..utils.archive_utils import get_archive_type
from ..utils.constants import DEFAULT_SKIP_PATTERNS
from ..sevenz import SevenZipHandler

class DirectoryUpdateThread(QThread):
    """Thread for updating a directory from another directory or archive"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str, bool)  # error message, is_permission_error
    status = pyqtSignal(str)  # Current file being processed
    file_counted = pyqtSignal(int)  # Emits total files found during counting

    def __init__(self, source_path, target_path, collision_strategy='skip', skip_patterns=None, password=None):
        super().__init__()
        self.source_path = source_path
        self.target_path = target_path
        self.collision_strategy = collision_strategy
        self.skip_patterns = skip_patterns or []
        self.password = password
        self._cancelled = False
        self._total_files = 0
        self._processed_files = 0

    def run(self):
        """Run the directory update thread"""
        try:
            # Determine if source is a directory or archive
            source_type = get_archive_type(self.source_path)
            
            # Handle directory source
            if source_type == 'dir':
                self._update_from_directory()
            # Handle archive source
            else:
                self._update_from_archive()

        except Exception as e:
            self.error.emit(str(e), False)
        finally:
            self.finished.emit(self.target_path)

    def _update_from_directory(self):
        """Update target directory from source directory"""
        try:
            # First, count total files for progress tracking
            self._count_files(self.source_path)
            self.file_counted.emit(self._total_files)

            # Now perform the update
            for root, _, files in os.walk(self.source_path):
                if self._cancelled:
                    break

                # Get relative path from source root
                rel_path = os.path.relpath(root, self.source_path)
                target_dir = os.path.join(self.target_path, rel_path)

                # Create target directory if it doesn't exist
                os.makedirs(target_dir, exist_ok=True)

                # Process files in current directory
                for file in files:
                    if self._cancelled:
                        break

                    source_file = os.path.join(root, file)
                    target_file = os.path.join(target_dir, file)

                    # Skip if file matches skip patterns
                    if self._should_skip(source_file):
                        continue

                    self.status.emit(f"Processing: {os.path.relpath(source_file, self.source_path)}")

                    # Handle file based on collision strategy
                    if os.path.exists(target_file):
                        if self.collision_strategy == 'skip':
                            continue
                        elif self.collision_strategy == 'rename':
                            target_file = self._get_unique_name(target_file)

                    # Copy the file
                    try:
                        shutil.copy2(source_file, target_file)
                    except PermissionError:
                        self.error.emit(f"Permission denied: {target_file}", True)
                        continue
                    except Exception as e:
                        self.error.emit(f"Failed to copy {source_file}: {str(e)}", False)
                        continue

                    self._processed_files += 1
                    self.progress.emit(int((self._processed_files / self._total_files) * 100))

        except Exception as e:
            self.error.emit(f"Directory update failed: {str(e)}", False)

    def _update_from_archive(self):
        """Update target directory from archive"""
        try:
            # Open the archive
            archive = self._open_archive()
            if not archive:
                return

            try:
                # Get list of files
                members = self._get_archive_members(archive)
                if not members:
                    self.error.emit("No files found in archive", False)
                    return

                self._total_files = len(members)
                self.file_counted.emit(self._total_files)

                # Process each file
                for member in members:
                    if self._cancelled:
                        break

                    try:
                        # Skip if file matches skip patterns
                        if self._should_skip(member):
                            continue

                        self.status.emit(f"Processing: {member}")

                        # Determine target path
                        target_file = os.path.join(self.target_path, member)
                        target_dir = os.path.dirname(target_file)

                        # Create target directory if needed
                        os.makedirs(target_dir, exist_ok=True)

                        # Handle file based on collision strategy
                        if os.path.exists(target_file):
                            if self.collision_strategy == 'skip':
                                continue
                            elif self.collision_strategy == 'rename':
                                target_file = self._get_unique_name(target_file)

                        # Extract the file
                        self._extract_member(archive, member, target_file)

                        self._processed_files += 1
                        self.progress.emit(int((self._processed_files / self._total_files) * 100))

                    except Exception as e:
                        self.error.emit(f"Failed to extract {member}: {str(e)}", False)
                        continue

            finally:
                if isinstance(archive, SevenZipHandler):
                    archive.close()
                elif hasattr(archive, 'close'):
                    archive.close()

        except Exception as e:
            self.error.emit(f"Archive update failed: {str(e)}", False)

    def _count_files(self, path):
        """Count total number of files for progress tracking"""
        try:
            for root, _, files in os.walk(path):
                if self._cancelled:
                    break
                for file in files:
                    if not self._should_skip(os.path.join(root, file)):
                        self._total_files += 1
        except Exception as e:
            self.error.emit(f"Failed to count files: {str(e)}", False)

    def _should_skip(self, filename):
        """Check if file should be skipped based on patterns"""
        name = os.path.basename(filename)
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.skip_patterns + DEFAULT_SKIP_PATTERNS)

    def _get_unique_name(self, filepath):
        """Generate a unique filename by appending a number"""
        if not os.path.exists(filepath):
            return filepath

        base, ext = os.path.splitext(filepath)
        counter = 1
        while True:
            new_path = f"{base} ({counter}){ext}"
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    def _open_archive(self):
        """Open archive based on type"""
        try:
            archive_type = get_archive_type(self.source_path)
            
            if not os.path.exists(self.source_path):
                raise Exception("Archive not found")
                
            if archive_type == '.zip':
                archive = zipfile.ZipFile(self.source_path)
                if self.password:
                    archive.setpassword(self.password.encode())
            elif archive_type in ('.tar', '.tar.gz', '.tar.bz2', '.tar.xz'):
                archive = tarfile.open(self.source_path)
            elif archive_type == '.rar':
                archive = rarfile.RarFile(self.source_path)
                if self.password:
                    archive.setpassword(self.password)
            elif archive_type == '.7z':
                archive = SevenZipHandler(self.source_path)
                if self.password:
                    archive.password = self.password
            else:
                raise Exception(f"Unsupported archive type: {archive_type}")
                
            return archive
            
        except Exception as e:
            self.error.emit(str(e), False)
            return None

    def _get_archive_members(self, archive):
        """Get list of files in the archive"""
        try:
            if isinstance(archive, zipfile.ZipFile):
                return archive.namelist()
            elif isinstance(archive, tarfile.TarFile):
                return [m.name for m in archive.getmembers()]
            elif isinstance(archive, rarfile.RarFile):
                return archive.namelist()
            elif isinstance(archive, SevenZipHandler):
                return archive.namelist()
            else:
                raise Exception("Unknown archive type")
                
        except Exception as e:
            self.error.emit(f"Failed to read archive contents: {str(e)}", False)
            return None

    def _extract_member(self, archive, member, target_path):
        """Extract a single member from the archive"""
        try:
            if isinstance(archive, zipfile.ZipFile):
                with archive.open(member) as source, open(target_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
            elif isinstance(archive, tarfile.TarFile):
                archive.extract(member, os.path.dirname(target_path))
                if os.path.exists(target_path) and target_path != os.path.join(os.path.dirname(target_path), member):
                    os.rename(os.path.join(os.path.dirname(target_path), member), target_path)
            elif isinstance(archive, rarfile.RarFile):
                archive.extract(member, os.path.dirname(target_path))
                if os.path.exists(target_path) and target_path != os.path.join(os.path.dirname(target_path), member):
                    os.rename(os.path.join(os.path.dirname(target_path), member), target_path)
            elif isinstance(archive, SevenZipHandler):
                archive.extract(member, os.path.dirname(target_path))
                if os.path.exists(target_path) and target_path != os.path.join(os.path.dirname(target_path), member):
                    os.rename(os.path.join(os.path.dirname(target_path), member), target_path)
            else:
                raise Exception("Unknown archive type")
        except Exception as e:
            raise Exception(f"Failed to extract {member}: {str(e)}")

    def cancel(self):
        """Cancel the update operation"""
        self._cancelled = True
