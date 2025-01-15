from PyQt6.QtCore import QThread, pyqtSignal, QWaitCondition, QMutex
import os
import tarfile
import zipfile
import rarfile
import fnmatch
from ..utils.archive_utils import get_archive_type
from ..sevenz import SevenZipHandler
from datetime import datetime

class ExtractionThread(QThread):
    progress = pyqtSignal(int)  # Progress percentage (0-100)
    finished = pyqtSignal(str)  # Path where files were extracted
    error = pyqtSignal(str, bool)  # error message, is_permission_error
    status = pyqtSignal(str)  # Current file being processed
    collision_question = pyqtSignal(str)  # Emitted when a collision occurs and user input is needed
    collision_response = pyqtSignal(bool)  # Response from user for collision (True=proceed, False=skip)
    rename_path = pyqtSignal(str)  # New path for renamed file
    collision_dialog_requested = pyqtSignal(list)  # Request for collision dialog

    def __init__(self, archive_name, extract_path, collision_strategy='skip', skip_patterns=None, password=None, preserve_permissions=True, file_list=None):
        super().__init__()
        self.archive_name = archive_name
        self.extract_path = extract_path
        self.collision_strategy = collision_strategy
        self.skip_patterns = skip_patterns or []
        self.password = password
        self.preserve_permissions = preserve_permissions
        self.file_list = file_list
        self._cancelled = False
        self._collision_event = QWaitCondition()
        self._collision_mutex = QMutex()
        self._collision_result = None
        self._rename_path = None
        self._collision_resolutions = None

        # Connect signals to slots
        self.collision_response.connect(self._on_collision_response)
        self.rename_path.connect(self._on_rename_path)
        self.collision_dialog_requested.connect(self._on_collision_dialog_requested)

    def _on_collision_response(self, response):
        """Handle collision response from UI"""
        self._collision_mutex.lock()
        self._collision_result = response
        self._collision_event.wakeAll()
        self._collision_mutex.unlock()

    def _on_rename_path(self, new_path):
        """Handle rename path from UI"""
        self._collision_mutex.lock()
        self._rename_path = new_path
        self._collision_mutex.unlock()

    def _on_collision_dialog_requested(self, collisions):
        """Handle collision dialog request from UI"""
        self._collision_mutex.lock()
        self._collision_resolutions = {}
        for member, target_path, archive_info in collisions:
            self._collision_resolutions[target_path] = 'skip'
        self._collision_event.wakeAll()
        self._collision_mutex.unlock()

    def run(self):
        """Run the extraction operation"""
        try:
            self.archive = self._open_archive()
            if not self.archive:
                return

            # Get list of files to extract
            members = self._get_archive_members(self.archive)
            if not members:
                return

            # Filter members based on skip patterns
            filtered_members = []
            for member in members:
                if not any(pattern in member for pattern in self.skip_patterns):
                    filtered_members.append(member)

            # Check for duplicates and collisions
            duplicates = self._find_duplicates(filtered_members)
            if duplicates:
                self.error.emit(
                    f"Archive contains duplicate entries:\n" + 
                    "\n".join(f"- {d}" for d in duplicates), 
                    False
                )
                return

            # Check for existing files
            collisions = self._check_collisions(filtered_members)
            if collisions and self.collision_strategy == 'ask':
                # Emit signal for UI to show collision dialog
                self.collision_dialog_requested.emit(collisions)
                # Wait for resolutions
                if not self._wait_for_resolutions():
                    return

            # Extract files
            total = len(filtered_members)
            for i, member in enumerate(filtered_members, 1):
                if self._cancelled:
                    break

                target_path = os.path.join(self.extract_path, member)
                
                # Skip if collision resolution says to skip
                if target_path in self._collision_resolutions:
                    if self._collision_resolutions[target_path] == 'skip':
                        continue

                # Create parent directory if needed
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                # Handle collision based on strategy
                if os.path.exists(target_path):
                    if not self._handle_collision(target_path):
                        continue

                # Extract the file
                self.status.emit(f"Extracting {member}")
                self._extract_member(self.archive, member)
                self.progress.emit(int(i * 100 / total))

            self.finished.emit(self.extract_path)

        except Exception as e:
            self.error.emit(str(e), False)
        finally:
            if hasattr(self.archive, 'close'):
                self.archive.close()

    def cancel(self):
        """Cancel the extraction operation"""
        self._cancelled = True

    def _handle_collision(self, target_path):
        """Handle file collision based on strategy"""
        if not os.path.exists(target_path):
            return True

        if self.collision_strategy == 'skip':
            return False
        elif self.collision_strategy == 'overwrite':
            try:
                if os.path.isfile(target_path):
                    os.remove(target_path)
                elif os.path.isdir(target_path):
                    os.rmdir(target_path)
                return True
            except Exception as e:
                self.error.emit(f"Error overwriting {target_path}: {str(e)}", False)
                return False
        elif self.collision_strategy == 'rename':
            base, ext = os.path.splitext(target_path)
            counter = 1
            new_path = target_path
            while os.path.exists(new_path):
                new_path = f"{base}_{counter}{ext}"
                counter += 1
            self.status.emit(f"Renamed to {os.path.basename(new_path)}")
            return True
        elif self.collision_strategy == 'newer':
            try:
                existing_mtime = os.path.getmtime(target_path)
                archive_mtime = self._get_member_mtime(target_path)
                return archive_mtime > existing_mtime
            except Exception as e:
                self.error.emit(f"Error comparing modification times: {str(e)}", False)
                return False
        elif self.collision_strategy == 'older':
            try:
                existing_mtime = os.path.getmtime(target_path)
                archive_mtime = self._get_member_mtime(target_path)
                return archive_mtime < existing_mtime
            except Exception as e:
                self.error.emit(f"Error comparing modification times: {str(e)}", False)
                return False
        elif self.collision_strategy == 'larger':
            try:
                existing_size = os.path.getsize(target_path)
                archive_size = self._get_member_size(target_path)
                return archive_size > existing_size
            except Exception as e:
                self.error.emit(f"Error comparing file sizes: {str(e)}", False)
                return False
        elif self.collision_strategy == 'smaller':
            try:
                existing_size = os.path.getsize(target_path)
                archive_size = self._get_member_size(target_path)
                return archive_size < existing_size
            except Exception as e:
                self.error.emit(f"Error comparing file sizes: {str(e)}", False)
                return False
        elif self.collision_strategy == 'ask':
            # Emit a signal to ask the user
            self.collision_question.emit(target_path)
            # Wait for response
            if not self._wait_for_collision_response():
                return False
            return True

        return False

    def _find_duplicates(self, members):
        """Find duplicate entries in the archive"""
        seen = set()
        duplicates = []
        for member in members:
            norm_path = os.path.normpath(member.lower())
            if norm_path in seen:
                duplicates.append(member)
            seen.add(norm_path)
        return duplicates

    def _check_collisions(self, members):
        """Check for existing files that would be overwritten"""
        collisions = []
        for member in members:
            target_path = os.path.join(self.extract_path, member)
            if os.path.exists(target_path):
                # Get info about existing file
                existing_info = {
                    'size': os.path.getsize(target_path),
                    'modified': os.path.getmtime(target_path)
                }
                # Get info about archive member
                archive_info = {
                    'size': self._get_member_size(target_path),
                    'modified': self._get_member_mtime(target_path)
                }
                collisions.append((member, target_path, archive_info))
        return collisions

    def _wait_for_collision_response(self):
        """Wait for user response to collision question"""
        self._collision_mutex.lock()
        self._collision_result = None
        self._rename_path = None
        self._collision_event.wait(self._collision_mutex)
        result = self._collision_result
        new_path = self._rename_path
        self._collision_mutex.unlock()
        
        if new_path:
            # Handle rename case
            return True
        return result

    def _wait_for_resolutions(self):
        """Wait for collision resolutions from UI"""
        self._collision_mutex.lock()
        self._collision_event.wait(self._collision_mutex)
        result = hasattr(self, '_collision_resolutions')
        self._collision_mutex.unlock()
        return result

    def _open_archive(self):
        """Open archive based on type"""
        try:
            archive_type = get_archive_type(self.archive_name)
            
            if archive_type == 'dir':
                return DirectoryHandler(self.archive_name, self.progress, self.status)
            elif archive_type == '.zip':
                archive = zipfile.ZipFile(self.archive_name, 'r')
                if self.password:
                    archive.setpassword(self.password.encode())
                return archive
            elif archive_type in ('.tar', '.tar.gz', '.tgz', '.tar.bz2'):
                return tarfile.open(self.archive_name, 'r:*')
            elif archive_type == '.rar':
                archive = rarfile.RarFile(self.archive_name, 'r')
                if self.password:
                    archive.setpassword(self.password)
                return archive
            elif archive_type == '.7z':
                archive = SevenZipHandler(self.archive_name)
                if self.password:
                    archive.password = self.password
                return archive
            else:
                self.error.emit(f"Unsupported archive type: {archive_type}", False)
                return None
                
        except Exception as e:
            self.error.emit(str(e), False)
            return None

    def _get_archive_members(self, archive):
        """Get list of files in the archive"""
        try:
            if isinstance(archive, (zipfile.ZipFile, rarfile.RarFile, SevenZipHandler, DirectoryHandler)):
                return archive.namelist()
            elif isinstance(archive, tarfile.TarFile):
                return archive.getnames()
            return []
        except Exception as e:
            self.error.emit(str(e), False)
            return []

    def _extract_member(self, archive, member):
        """Extract a single member from the archive"""
        try:
            if isinstance(archive, (zipfile.ZipFile, rarfile.RarFile)):
                archive.extract(member, self.extract_path)
            elif isinstance(archive, tarfile.TarFile):
                archive.extract(member, self.extract_path)
            elif isinstance(archive, SevenZipHandler):
                archive.extract(member, self.extract_path)
            elif isinstance(archive, DirectoryHandler):
                archive.extract(member, self.extract_path)

            # Handle permissions if needed
            if self.preserve_permissions:
                target_path = os.path.join(self.extract_path, member)
                if os.path.exists(target_path):
                    mode = self._get_member_mode(archive, member)
                    if mode:
                        try:
                            os.chmod(target_path, mode)
                        except Exception as e:
                            self.error.emit(f"Error setting permissions for {member}: {str(e)}", True)

        except Exception as e:
            raise Exception(f"Failed to extract {member}: {str(e)}")

    def _get_member_mtime(self, target_path):
        """Get modification time of archive member"""
        member_name = os.path.relpath(target_path, self.extract_path)
        if isinstance(self.archive, zipfile.ZipFile):
            info = self.archive.getinfo(member_name)
            return datetime(*info.date_time).timestamp()
        elif isinstance(self.archive, tarfile.TarFile):
            info = self.archive.getmember(member_name)
            return info.mtime
        elif isinstance(self.archive, SevenZipHandler):
            info = self.archive.getinfo(member_name)
            return info.get('mtime', 0)
        return 0

    def _get_member_size(self, target_path):
        """Get size of archive member"""
        member_name = os.path.relpath(target_path, self.extract_path)
        if isinstance(self.archive, zipfile.ZipFile):
            info = self.archive.getinfo(member_name)
            return info.file_size
        elif isinstance(self.archive, tarfile.TarFile):
            info = self.archive.getmember(member_name)
            return info.size
        elif isinstance(self.archive, SevenZipHandler):
            info = self.archive.getinfo(member_name)
            return info.get('size', 0)
        return 0

    def _get_member_mode(self, archive, member):
        """Get the permission mode for a member"""
        try:
            if isinstance(archive, zipfile.ZipFile):
                return (archive.getinfo(member).external_attr >> 16) & 0o777
            elif isinstance(archive, tarfile.TarFile):
                return archive.getmember(member).mode
            elif isinstance(archive, rarfile.RarFile):
                return archive.getinfo(member).mode
            elif isinstance(archive, SevenZipHandler):
                return archive.getinfo(member).mode
            elif isinstance(archive, DirectoryHandler):
                return os.stat(os.path.join(archive.directory_path, member)).st_mode
            return None
        except Exception:
            return None

class DirectoryHandler:
    """Handler for directory operations that mimics archive interface"""
    def __init__(self, directory_path, progress_signal=None, status_signal=None):
        self.directory_path = directory_path
        self._file_list = None
        self._progress_signal = progress_signal
        self._status_signal = status_signal

    def namelist(self):
        """Get list of files in directory"""
        if self._file_list is None:
            self._file_list = []
            total_items = sum([len(files) for _, _, files in os.walk(self.directory_path)])
            processed = 0
            
            if self._status_signal:
                self._status_signal.emit("Reading directory contents...")
            
            for root, _, files in os.walk(self.directory_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.directory_path)
                    self._file_list.append(rel_path)
                    processed += 1
                    
                    if self._progress_signal and total_items > 0:
                        progress = int(processed * 100 / total_items)
                        self._progress_signal.emit(progress)
            
            if self._status_signal:
                self._status_signal.emit(f"Found {len(self._file_list)} files")
                
        return self._file_list

    def extract(self, member, path):
        """Copy file to target path"""
        src = os.path.join(self.directory_path, member)
        dst = os.path.join(path, member)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        import shutil
        shutil.copy2(src, dst)

    def close(self):
        """No-op for compatibility"""
        pass
