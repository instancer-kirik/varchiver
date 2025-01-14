from PyQt6.QtCore import QThread, pyqtSignal
import os
import tarfile
import zipfile
import rarfile
import fnmatch
from pathlib import Path
from ..utils.constants import DEFAULT_SKIP_PATTERNS
from ..utils.archive_utils import get_archive_type
from ..sevenz import SevenZipHandler

class ArchiveThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)  # Include archive name in finished signal
    error = pyqtSignal(str, bool)  # error message, is_permission_error
    status = pyqtSignal(str)  # Current file being processed
    file_counted = pyqtSignal(int)  # Emits total files found during counting
    index_entry = pyqtSignal(dict)  # Emits file info as it's added to archive

    def __init__(self, files, archive_name, collision_strategy='skip', skip_patterns=None, 
                 password=None, compression_level=5, preserve_permissions=True):
        super().__init__()
        self.files = files
        self.archive_name = archive_name
        self.collision_strategy = collision_strategy
        self.skip_patterns = skip_patterns or []
        self.password = password
        self.compression_level = compression_level
        self.preserve_permissions = preserve_permissions
        self.existing_files = {}
        self.archive_type = get_archive_type(archive_name)
        self._cancelled = False
        self._total_files = 0
        self._processed_files = 0

    def run(self):
        """Run the archive creation thread"""
        try:
            # Now scan and collect all files
            all_files = []
            self._processed_files = 0
            for path in self.files:
                if self._cancelled:
                    break
                if os.path.isfile(path):
                    if not self._should_skip(path):
                        # For single files, use their parent dir as base
                        all_files.append((path, os.path.dirname(path)))
                        self._processed_files += 1
                        self.progress.emit(int((self._processed_files / self._total_files) * 100))
                else:
                    self._scan_directory(path, all_files)
                    
            if self._cancelled:
                return
                
            # Update total for archive creation progress
            self._total_files = len(all_files)
            if self._total_files == 0:
                raise Exception("No files to archive")
                
            # Create archive with collected files
            self.status.emit("Creating archive...")
            self._processed_files = 0  # Reset for archive creation progress
            
            if self.archive_type == '.zip':
                self._create_zip_archive(all_files)
            elif self.archive_type in ('.tar', '.tar.gz', '.tgz', '.tar.bz2'):
                self._create_tar_archive(all_files)
            elif self.archive_type == '.7z':
                self._create_7z_archive(all_files)
            elif self.archive_type == '.rar':
                self._create_rar_archive(all_files)
            elif self.archive_type == 'dir':
                self._create_directory_archive(all_files)
                
            if not self._cancelled:
                self.status.emit("Archive created successfully")
                self.finished.emit(self.archive_name)
                
        except Exception as e:
            self.error.emit(str(e), False)

    def cancel(self):
        """Cancel the archiving operation"""
        self._cancelled = True
        self.status.emit("Cancelling operation...")
        
    def terminate(self):
        """Handle thread termination"""
        self.cancel()  # Set cancelled flag
        super().terminate()  # Call parent's terminate method

    def _count_files(self, path):
        """Count files in directory using pathlib for better performance"""
        from pathlib import Path
        count = 0
        try:
            p = Path(path)
            root_dir = p if p.is_dir() else p.parent
            if p.is_file():
                return 1 if not self._should_skip(str(p)) else 0
                
            # Use pathlib for faster directory traversal
            for entry in p.rglob('*'):
                if self._cancelled:
                    break
                try:
                    if entry.is_file():
                        if not self._should_skip(str(entry)):
                            count += 1
                            # Update status every 1000 files
                            if count % 1000 == 0:
                                # Get path relative to the root being archived
                                try:
                                    rel_path = entry.parent.relative_to(root_dir)
                                    first_dir = next(iter(rel_path.parts), '')
                                    self.status.emit(f"Scanning {first_dir}: {count:,} files...")
                                except ValueError:
                                    # Fallback if relative_to fails
                                    self.status.emit(f"Scanning {entry.parent.name}: {count:,} files...")
                except (PermissionError, OSError) as e:
                    print(f"Warning: Skipping {entry}: {e}")
                    continue
                    
        except (PermissionError, OSError) as e:
            print(f"Warning: Error scanning {path}: {e}")
            
        return count

    def _scan_directory(self, path, files_list):
        """Scan directory using pathlib and add files to list"""
        from pathlib import Path
        try:
            p = Path(path)
            # Use the actual directory being scanned as root
            root_dir = p
            file_count = 0
            
            for entry in p.rglob('*'):
                if self._cancelled:
                    break
                try:
                    if entry.is_file():
                        if not self._should_skip(str(entry)):
                            # Store tuple of (file_path, base_dir) to maintain structure
                            files_list.append((str(entry), str(root_dir)))
                            file_count += 1
                            if file_count % 1000 == 0:
                                try:
                                    rel_path = entry.parent.relative_to(root_dir)
                                    first_dir = next(iter(rel_path.parts), '')
                                    self.status.emit(f"On {first_dir}: {file_count:,}")
                                except ValueError:
                                    self.status.emit(f"ValueError - {file_count:,} files in {entry.parent.name}...")
                except (PermissionError, OSError) as e:
                    print(f"Warning: Skipping {entry}: {e}")
                    continue
                    
        except (PermissionError, OSError) as e:
            print(f"Warning: Error scanning {path}: {e}")

    def _should_skip(self, filepath):
        """Check if file should be skipped based on patterns"""
        for pattern in self.skip_patterns:
            if fnmatch.fnmatch(filepath.lower(), pattern.lower()):
                return True
            # Handle directory patterns
            if pattern.endswith('/**'):
                dir_pattern = pattern[:-3]
                path_parts = Path(filepath).parts
                for i in range(len(path_parts)):
                    if fnmatch.fnmatch(str(Path(*path_parts[:i+1])), dir_pattern):
                        return True
        return False

    def _handle_collision(self, file_path, archive_path, archive):
        """Handle file collision based on strategy"""
        if not self._file_exists_in_archive(archive_path, archive):
            return archive_path

        if self.collision_strategy == 'Skip existing files':
            return None
        elif self.collision_strategy == 'Overwrite existing files':
            return archive_path
        elif self.collision_strategy == 'Keep newer files':
            file_time = os.path.getmtime(file_path)
            archive_time = self._get_archive_file_time(archive_path, archive)
            return archive_path if file_time > archive_time else None
        elif self.collision_strategy == 'Keep larger files':
            file_size = os.path.getsize(file_path)
            archive_size = self._get_archive_file_size(archive_path, archive)
            return archive_path if file_size > archive_size else None
        elif self.collision_strategy == 'Keep both files':
            # Generate a new unique name
            base, ext = os.path.splitext(archive_path)
            counter = 1
            while self._file_exists_in_archive(f"{base}_{counter}{ext}", archive):
                counter += 1
            return f"{base}_{counter}{ext}"
        elif self.collision_strategy == 'Ask for each file':
            # This should be handled by the UI thread
            self.status.emit(f"Collision: {archive_path}")
            return None
        else:
            # Default to skip
            return None

    def _file_exists_in_archive(self, path, archive):
        """Check if file exists in archive"""
        try:
            if self.archive_type == '.7z':
                return path in [f['path'] for f in archive.list_contents()]
            elif self.archive_type == '.zip':
                return path in archive.namelist()
            elif self.archive_type in ('.tar', '.tar.gz', '.tgz', '.tar.bz2'):
                return path in archive.getnames()
            elif self.archive_type == '.rar':
                return path in [f.filename for f in archive.infolist()]
            return False
        except Exception:
            return False

    def _get_archive_file_time(self, path, archive):
        """Get file modification time from archive"""
        try:
            if self.archive_type == '.7z':
                info = next((f for f in archive.list_contents() if f['path'] == path), None)
                return info.get('modified', 0) if info else 0
            elif self.archive_type == '.zip':
                return archive.getinfo(path).date_time
            elif self.archive_type in ('.tar', '.tar.gz', '.tgz', '.tar.bz2'):
                return archive.getmember(path).mtime
            elif self.archive_type == '.rar':
                return archive.getinfo(path).date_time
            return 0
        except Exception:
            return 0

    def _get_archive_file_size(self, path, archive):
        """Get file size from archive"""
        try:
            if self.archive_type == '.7z':
                info = next((f for f in archive.list_contents() if f['path'] == path), None)
                return info.get('size', 0) if info else 0
            elif self.archive_type == '.zip':
                return archive.getinfo(path).file_size
            elif self.archive_type in ('.tar', '.tar.gz', '.tgz', '.tar.bz2'):
                return archive.getmember(path).size
            elif self.archive_type == '.rar':
                return archive.getinfo(path).file_size
            return 0
        except Exception:
            return 0

    def _add_to_archive(self, archive, src_path, arc_path):
        """Add a file to the archive and emit its info"""
        try:
            # Get file info before adding
            stat = os.stat(src_path)
            is_dir = os.path.isdir(src_path)
            
            # Create index entry
            entry = {
                'name': os.path.basename(arc_path),
                'path': arc_path,
                'path_parts': [p for p in arc_path.split('/') if p],
                'size': 0 if is_dir else stat.st_size,
                'compressed': 0,  # Will be updated after compression if available
                'is_dir': is_dir
            }
            
            # Add to archive
            if isinstance(archive, zipfile.ZipFile):
                if not is_dir:
                    archive.write(src_path, arc_path)
                    info = archive.getinfo(arc_path)
                    entry['compressed'] = info.compress_size
            elif isinstance(archive, tarfile.TarFile):
                archive.add(src_path, arc_path)
                entry['compressed'] = entry['size']  # No compression in tar
            elif isinstance(archive, rarfile.RarFile):
                archive.write(src_path, arc_path)
                info = archive.getinfo(arc_path)
                entry['compressed'] = info.compress_size
            elif isinstance(archive, SevenZipHandler):
                archive.write(src_path, arc_path)
                # 7z sizes will be available after closing
            
            # Emit index entry
            self.index_entry.emit(entry)
            
        except Exception as e:
            print(f"Error adding {src_path}: {e}")
            raise

    def _save_index(self, index_data):
        """Save index data alongside archive"""
        try:
            index_path = self.archive_name + '.arindex'
            with open(index_path, 'w') as f:
                f.write(str(index_data))
        except Exception as e:
            print(f"Warning: Could not save index: {e}")

    def _create_zip_archive(self, files):
        """Create a ZIP archive"""
        try:
            compression = zipfile.ZIP_DEFLATED
            if self.password:
                # Use ZIP_ENCRYPTED when password is provided
                compression |= zipfile.ZIP_ENCRYPTED
                
            with zipfile.ZipFile(self.archive_name, 'w', compression=compression, compresslevel=self.compression_level) as archive:
                if self.password:
                    archive.setpassword(self.password.encode())
                    
                for file_path, base_dir in files:
                    if self._cancelled:
                        break
                        
                    rel_path = os.path.relpath(file_path, base_dir)
                    first_dir = rel_path.split(os.sep)[0]
                    
                    self.status.emit(f"Adding to {first_dir}: {self._processed_files:,}/{self._total_files:,}")
                    arc_path = self._handle_collision(file_path, rel_path, archive)
                    if arc_path:
                        self._add_to_archive(archive, file_path, arc_path)
                    self._processed_files += 1
                    if self._processed_files % 10 == 0:  # Update progress more frequently
                        self.progress.emit(int((self._processed_files / self._total_files) * 100))
                    
        except Exception as e:
            raise Exception(f"Failed to create archive: {str(e)}")

    def _create_tar_archive(self, files):
        """Create TAR archive"""
        try:
            mode = 'w:gz' if self.archive_type in ('.tar.gz', '.tgz') else 'w:bz2' if self.archive_type == '.tar.bz2' else 'w'
            index_data = {'files': [], 'total_size': 0, 'compressed_size': 0}
            
            with tarfile.open(self.archive_name, mode) as archive:
                for file_path, base_dir in files:
                    if self._cancelled:
                        break
                        
                    rel_path = os.path.relpath(file_path, base_dir)
                    first_dir = rel_path.split(os.sep)[0]
                    
                    self.status.emit(f"Adding to {first_dir}: {self._processed_files:,}/{self._total_files:,}")
                    arc_path = self._handle_collision(file_path, rel_path, archive)
                    if arc_path:
                        archive.add(file_path, arc_path)
                        
                        entry = {
                            'name': os.path.basename(rel_path),
                            'path': rel_path,
                            'size': os.path.getsize(file_path),
                            'compressed': os.path.getsize(file_path),  # TAR doesn't store compressed size
                            'is_dir': False
                        }
                        index_data['files'].append(entry)
                        index_data['total_size'] += os.path.getsize(file_path)
                        index_data['compressed_size'] += os.path.getsize(file_path)
                    
                    self._processed_files += 1
                    if self._processed_files % 10 == 0:  # Update progress more frequently
                        self.progress.emit(int((self._processed_files / self._total_files) * 100))
                
                if not self._cancelled:
                    self.status.emit("Saving archive index...")
                    self._save_index(index_data)
                    
        except Exception as e:
            raise Exception(f"Failed to create archive: {str(e)}")

    def _create_7z_archive(self, files):
        """Create 7Z archive"""
        try:
            # Create 7z handler with indexing enabled
            archive = SevenZipHandler(self.archive_name, index_store=True)
            if self.password:
                archive.password = self.password
            
            # Add files to archive
            for file_path, base_dir in files:
                if self._cancelled:
                    break
                    
                # Calculate relative path from base directory
                rel_path = os.path.relpath(file_path, base_dir)
                first_dir = rel_path.split(os.sep)[0]
                
                self.status.emit(f"Adding from {first_dir}: {self._processed_files:,}/{self._total_files:,}")
                arc_path = self._handle_collision(file_path, rel_path, archive)
                if arc_path:
                    archive.write(file_path, arc_path)
                self._processed_files += 1
                if self._processed_files % 10 == 0:  # Update progress more frequently
                    self.progress.emit(int((self._processed_files / self._total_files) * 100))
            
            archive.close()
                
        except Exception as e:
            raise Exception(f"Failed to create archive: {str(e)}")

    def _create_rar_archive(self, files):
        """Create RAR archive"""
        with rarfile.RarFile(self.archive_name, 'w') as archive:
            if self.password:
                archive.setpassword(self.password)
            self._add_files_to_archive(archive, files)

    def _add_files_to_archive(self, archive, files):
        """Add files to the archive"""
        for file_path, base_dir in files:
            if self._cancelled:
                break

            rel_path = os.path.relpath(file_path, base_dir)
            arc_path = self._handle_collision(file_path, rel_path, archive)
            if arc_path:
                self.status.emit(f"Adding: {rel_path}")
                archive.write(file_path, arc_path)
            self._processed_files += 1
            self.progress.emit(int((self._processed_files / self._total_files) * 100))

    def _create_directory_archive(self, files):
        """Create a directory structure by copying files"""
        import shutil
        
        os.makedirs(self.archive_name, exist_ok=True)
        
        for src_path, base_dir in files:
            if self._cancelled:
                break
                
            # Calculate relative path from base directory
            rel_path = os.path.relpath(src_path, base_dir)
            # Create target path in new directory
            target_path = os.path.join(self.archive_name, rel_path)
            
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Copy the file, preserving metadata
            shutil.copy2(src_path, target_path)
            
            # Update progress
            self._processed_files += 1
            self.progress.emit(int((self._processed_files / self._total_files) * 100))
            self.status.emit(f"Copying: {rel_path}")
            
            # Emit index entry for the file
            self.index_entry.emit({
                'name': rel_path,
                'size': os.path.getsize(src_path),
                'mtime': os.path.getmtime(src_path)
            })
