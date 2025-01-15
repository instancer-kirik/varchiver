from PyQt6.QtCore import QThread, pyqtSignal
import os
import time
import zipfile
import tarfile
import rarfile
from threading import Lock
from ..utils.archive_utils import get_archive_type
from ..sevenz import SevenZipHandler

class BrowseThread(QThread):
    """Thread for browsing archive contents"""
    contents_ready = pyqtSignal(list)  # Emits the final tree structure
    error = pyqtSignal(str)  # Emits error messages
    progress = pyqtSignal(int)  # Emits progress percentage (0-100)
    status = pyqtSignal(str)  # Emits status messages

    # Class-level cache and lock
    _cache_lock = Lock()
    _archive_cache = {}

    def __init__(self, archive_path, password=None):
        super().__init__()
        self.archive_path = archive_path
        self.password = password
        self._cancelled = False
        self.cache_key = f"{archive_path}_{os.path.getmtime(archive_path)}"

    def _get_cached_info(self):
        """Get cached archive info if available"""
        with self._cache_lock:
            if self.cache_key in self._archive_cache:
                return self._archive_cache[self.cache_key]
        return None

    def _cache_info(self, contents):
        """Cache archive info"""
        with self._cache_lock:
            self._archive_cache[self.cache_key] = contents

    def _get_index_info(self):
        """Try to load index file if it exists"""
        try:
            index_path = self.archive_path + '.arindex'
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    index_str = f.read()
                    # Convert string representation to dict
                    index_data = eval(index_str)  # Safe since we created the file
                    return index_data.get('files', [])
            return None
        except Exception as e:
            print(f"Warning: Could not load index: {e}")
            return None

    def run(self):
        """Run the thread"""
        try:
            self.status.emit("Opening archive...")
            self.progress.emit(0)

            # Try cache first
            cached_contents = self._get_cached_info()
            if cached_contents:
                self.status.emit("Using cached contents...")
                self.progress.emit(90)
                self._process_files(cached_contents)
                self.progress.emit(100)
                return

            # Get archive type
            archive_type = get_archive_type(self.archive_path)
            files = []

            # Handle different archive types
            if archive_type == '.zip':
                self.status.emit("Reading ZIP archive...")
                with zipfile.ZipFile(self.archive_path, 'r') as archive:
                    if self.password:
                        archive.setpassword(self.password.encode())
                    files = [{'path': info.filename, 'size': info.file_size, 'is_dir': info.filename.endswith('/')} 
                            for info in archive.infolist()]

            elif archive_type in ('.tar', '.tar.gz', '.tgz', '.tar.bz2'):
                self.status.emit("Reading TAR archive...")
                with tarfile.open(self.archive_path, 'r:*') as archive:
                    files = [{'path': member.name, 'size': member.size, 'is_dir': member.isdir()} 
                            for member in archive.getmembers()]

            elif archive_type == '.rar':
                self.status.emit("Reading RAR archive...")
                with rarfile.RarFile(self.archive_path, 'r') as archive:
                    if self.password:
                        archive.setpassword(self.password)
                    files = [{'path': info.filename, 'size': info.file_size, 'is_dir': info.isdir} 
                            for info in archive.infolist()]

            elif archive_type == '.7z':
                self.status.emit("Reading 7z archive...")
                self.progress.emit(10)
                archive = None
                try:
                    archive = SevenZipHandler(self.archive_path)
                    if self.password:
                        archive.password = self.password
                    
                    # Get file list from archive
                    self.status.emit("Listing archive contents...")
                    self.progress.emit(30)
                    files = archive.list_contents()
                    if files:
                        # Convert files to standard format
                        files = [{'path': f['path'], 
                                'size': f.get('size', 0), 
                                'is_dir': f.get('is_dir', False),
                                'modified': f.get('modified', '')} 
                               for f in files]
                        self._cache_info(files)  # Cache for future use
                    
                    if not files:
                        raise Exception("No files found in archive")
                        
                except Exception as e:
                    self.error.emit(f"Error reading 7z archive: {str(e)}")
                    return
                finally:
                    if archive:
                        archive.close()

            # Process files and update progress
            if files:
                self.status.emit("Processing files...")
                self.progress.emit(60)
                self._process_files(files)
                self.progress.emit(100)
            else:
                self.error.emit("No files found in archive")
                
        except Exception as e:
            self.error.emit(str(e))

    def _process_files(self, files):
        """Process list of files and emit results"""
        try:
            if self._cancelled:
                return

            total_files = len(files)
            self.status.emit(f"Processing {total_files} files...")

            # Build tree structure
            tree = []
            processed = 0

            for file_entry in files:
                if self._cancelled:
                    return

                filepath = file_entry['path']
                is_dir = file_entry.get('is_dir', filepath.endswith('/'))

                # Normalize path separators
                filepath = filepath.replace('\\', '/')

                # Skip if path starts with . or ..
                if filepath.startswith('.') or filepath.startswith('..'):
                    continue

                parts = filepath.split('/')
                current = tree

                # Build path
                for i, part in enumerate(parts):
                    # Skip empty parts
                    if not part:
                        continue

                    # Find or create node
                    node = next((n for n in current if n['name'] == part), None)
                    if node is None:
                        node = {
                            'name': part,
                            'path': '/'.join(parts[:i+1]),
                            'is_dir': i < len(parts) - 1 or (i == len(parts) - 1 and is_dir),
                            'children': []
                        }
                        if 'size' in file_entry:
                            node['size'] = file_entry['size']
                        current.append(node)
                    current = node['children']

                processed += 1
                progress = int(processed * 100 / total_files) if total_files > 0 else 100
                self.progress.emit(progress)

            self.status.emit("Finalizing...")
            self.contents_ready.emit(tree)
            self.progress.emit(100)
            self.status.emit("Ready")

        except Exception as e:
            self.error.emit(f"Error processing files: {str(e)}")

    def cancel(self):
        """Cancel the operation"""
        self._cancelled = True
