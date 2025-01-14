import subprocess
import re
import os
import tempfile
from typing import List, Dict, Optional, Any
import fnmatch
from pathlib import Path
from PyQt6.QtWidgets import QInputDialog, QLineEdit
import sys

class SevenZipHandler:
    """Handler for 7z archives using 7z command-line tool"""
    def __init__(self, archive_path: str, index_store: bool = False):
        """Initialize SevenZipHandler
        
        Args:
            archive_path: Path to archive
            index_store: If True, store archive index in a .idx file for faster loading
        """
        self.archive_path = os.path.abspath(archive_path)
        self._password = None
        self._index_store = index_store
        self._index_path = os.path.splitext(self.archive_path)[0] + '.idx'
        self._check_7z()
        
    @property
    def password(self) -> Optional[str]:
        """Get password"""
        return self._password
        
    @password.setter
    def password(self, value: Optional[str]):
        """Set password"""
        self._password = value
        
    def _check_7z(self) -> None:
        """Check if 7z command is available"""
        try:
            result = subprocess.run(['7z', '--help'], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("7z command is not working properly")
        except FileNotFoundError:
            raise Exception("7z command not found. Please install p7zip.")
            
    def _run_7z_command(self, cmd: List[str]) -> str:
        """Run 7z command and handle common errors"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check for common errors
            if result.returncode != 0:
                stderr = result.stderr.strip()
                if 'Wrong password' in stderr or 'password is incorrect' in stderr:
                    raise Exception("Incorrect password")
                elif 'No such file or directory' in stderr:
                    raise FileNotFoundError(f"Archive not found: {self.archive_path}")
                elif stderr:
                    raise Exception(f"7z command failed: {stderr}")
                else:
                    raise Exception("Unknown 7z error")
            
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to run 7z command: {e}")

    def namelist(self) -> List[str]:
        """Get list of file names in the archive"""
        contents = self.list_contents()
        return [entry['path'] for entry in contents]
        
    def getinfo(self, name: str) -> Optional[Dict[str, Any]]:
        """Get info for a specific file"""
        contents = self.list_contents()
        for entry in contents:
            if entry['path'] == name:
                return entry
        return None

    def write(self, filename: str, arcname: Optional[str] = None) -> None:
        """Add a file or directory to the archive"""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Path not found: {filename}")
            
        arcname = arcname or os.path.basename(filename)
        
        # Check skip patterns
        if self._should_skip(arcname):
            print(f"Skipping {arcname} (matches skip pattern)")
            return
            
        # Use 'a' command to add files
        cmd = ['7z', 'a']
        if self._get_password():
            cmd.extend(['-p' + self._get_password()])
            
        # Handle directories by adding recursive flag
        if os.path.isdir(filename):
            cmd.extend(['-r'])
            
        cmd.extend([self.archive_path, filename])
            
        try:
            self._run_7z_command(cmd)
        except Exception as e:
            if os.path.isdir(filename):
                raise Exception(f"Failed to add directory '{filename}' to archive: {str(e)}")
            else:
                raise Exception(f"Failed to add file '{filename}' to archive: {str(e)}")

    def read(self, name: str) -> bytes:
        """Read file from archive"""
        if not os.path.exists(self.archive_path):
            raise FileNotFoundError(f"Archive not found: {self.archive_path}")
            
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = ['7z', 'e', '-so', self.archive_path, name]
            if self._get_password():
                cmd.extend(['-p' + self._get_password()])
                
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                raise Exception(f"Failed to extract file: {result.stderr.decode()}")
            return result.stdout

    def extract(self, member: str, path: Optional[str] = None) -> None:
        """Extract a member from the archive"""
        if not os.path.exists(self.archive_path):
            raise FileNotFoundError(f"Archive not found: {self.archive_path}")
            
        # Check skip patterns
        if self._should_skip(member):
            print(f"Skipping {member} (matches skip pattern)")
            return
            
        if path is None:
            path = os.getcwd()
            
        # Use 'x' command to extract
        cmd = ['7z', 'x']
        if self._get_password():
            cmd.extend(['-p' + self._get_password()])
        cmd.extend(['-o' + path, self.archive_path, member])
            
        self._run_7z_command(cmd)
        
    def extractall(self, path: Optional[str] = None) -> None:
        """Extract all files from the archive"""
        if not os.path.exists(self.archive_path):
            raise FileNotFoundError(f"Archive not found: {self.archive_path}")
            
        cmd = ['7z', 'x']
        if self._get_password():
            cmd.extend(['-p' + self._get_password()])
        if path:
            cmd.extend(['-o' + path])
            
        cmd.append(self.archive_path)
        self._run_7z_command(cmd)
        
    def writeall(self, filenames: List[str], base_dir: Optional[str] = None) -> None:
        """Add multiple files to the archive"""
        if not filenames:
            raise ValueError("No files to add")
            
        # Build 7z command
        cmd = ['7z', 'a', '-t7z']  
        if self._get_password():
            cmd.extend(['-p' + self._get_password()])
            
        # Add archive path
        cmd.append(self.archive_path)
        
        # Convert all paths to absolute
        abs_files = [os.path.abspath(f) for f in filenames]
        
        # If base_dir is specified, use it for relative paths
        if base_dir:
            abs_base = os.path.abspath(base_dir)
            # Change to base directory for proper relative paths
            current_dir = os.getcwd()
            os.chdir(abs_base)
            try:
                # Add files with paths relative to base_dir
                for file in abs_files:
                    try:
                        rel_path = os.path.relpath(file, abs_base)
                        if os.path.exists(file):  # Verify file exists
                            cmd.append(rel_path)
                    except ValueError as e:
                        # Handle case where file is on different drive
                        if "path is on mount" in str(e):
                            cmd.append(file)
                self._run_7z_command(cmd)
            finally:
                os.chdir(current_dir)
        else:
            # Add files with absolute paths
            for file in abs_files:
                if os.path.exists(file):  # Verify file exists
                    cmd.append(file)
            if not any(os.path.exists(f) for f in abs_files):
                raise ValueError("No valid files to add")
            self._run_7z_command(cmd)
            
    def write_str(self, data: str, arcname: str) -> None:
        """Write a string to a file in the archive"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
            temp.write(data)
            temp_name = temp.name
            
        try:
            # Add the temp file to the archive with the desired name
            self.write(temp_name, arcname)
        finally:
            # Clean up the temp file
            os.unlink(temp_name)
            
    def close(self) -> None:
        """Close the archive (no-op for command-line tool)"""
        pass
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def infolist(self) -> List[Dict[str, Any]]:
        """Get list of FileInfo objects for files in the archive"""
        return self.list_contents()

    def open(self, name: str, mode: str = 'r') -> Any:
        """Open a file in the archive"""
        if mode not in ['r', 'rb']:
            raise ValueError("Invalid mode")
            
        return self.read(name)

    def _load_index(self) -> Optional[List[Dict[str, Any]]]:
        """Load archive index from .idx file if it exists and is newer than archive"""
        if not self._index_store:
            return None
            
        try:
            if not os.path.exists(self._index_path):
                return None
                
            # Check if index is newer than archive
            archive_mtime = os.path.getmtime(self.archive_path)
            index_mtime = os.path.getmtime(self._index_path)
            if index_mtime < archive_mtime:
                return None
                
            # Load index
            with open(self._index_path, 'r') as f:
                import json
                return json.load(f)
                
        except Exception as e:
            print(f"Error loading index: {e}")
            return None
            
    def _save_index(self, entries: List[Dict[str, Any]]) -> None:
        """Save archive index to .idx file"""
        if not self._index_store:
            return
            
        try:
            with open(self._index_path, 'w') as f:
                import json
                json.dump(entries, f)
        except Exception as e:
            print(f"Error saving index: {e}")
            
    def list_contents(self) -> List[Dict[str, Any]]:
        """List contents of the archive"""
        print("Starting list_contents")
        sys.stdout.flush()
        
        if not os.path.exists(self.archive_path):
            print(f"Archive not found: {self.archive_path}")
            sys.stdout.flush()
            raise FileNotFoundError(f"Archive not found: {self.archive_path}")

        try:
            # Use 'l' command to list contents with technical info
            cmd = ['7z', 'l', self.archive_path]
            print("Built base command")
            sys.stdout.flush()
            
            password = self._get_password()
            print("Got password result")
            sys.stdout.flush()
            
            if password:
                print("Adding password to command")
                sys.stdout.flush()
                cmd.extend(['-p' + password])

            print(f"Running command: {' '.join(cmd)}")
            sys.stdout.flush()
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(f"Command completed with return code: {result.returncode}")
            sys.stdout.flush()
            
            if result.returncode != 0:
                stderr = result.stderr.strip()
                if "Wrong password" in stderr:
                    raise Exception("Incorrect password")
                elif "Can not open" in stderr:
                    raise FileNotFoundError(f"Cannot open archive: {self.archive_path}")
                else:
                    raise Exception(f"Error reading archive: {stderr}")

            entries = []
            reading_files = False
            found_summary = False  # Track if we've hit the summary line
            
            print("Starting to parse output")
            sys.stdout.flush()
            
            print("Output lines:")
            for line in result.stdout.splitlines():
                print(f"  > {line}")
            sys.stdout.flush()
            
            for line in result.stdout.splitlines():
                line = line.rstrip()
                
                # Look for the header line
                if 'Date' in line and 'Time' in line and 'Attr' in line:
                    print(f"Found header line: {line}")
                    sys.stdout.flush()
                    reading_files = True
                    continue
                    
                # Skip until we find the header
                if not reading_files:
                    continue
                    
                # Skip separator lines and empty lines
                if not line.strip() or line.startswith('-------------------'):
                    continue
                    
                # Check if we've hit the summary line (contains "files")
                if ' files' in line and line.startswith('20'):
                    print(f"Found summary line: {line}")
                    sys.stdout.flush()
                    found_summary = True
                    continue
                    
                # Skip if we've hit the summary
                if found_summary:
                    continue
                    
                # Parse line like: "2024-11-29 18:36:33 ....A        22914         6864  poetry.lock"
                try:
                    parts = line.split(None, 5)  # Split by whitespace, max 6 parts
                    print(f"Parsing line: {line}")
                    print(f"Parts: {parts}")
                    sys.stdout.flush()
                    
                    if len(parts) == 6:
                        date, time, attr, size, packed, name = parts
                        print(f"Parsing file: {name} (size={size}, packed={packed})")
                        sys.stdout.flush()
                        
                        try:
                            size = int(size)
                            packed = int(packed)
                        except ValueError:
                            size = 0
                            packed = 0
                            
                        entry = {
                            'path': name,
                            'name': os.path.basename(name.rstrip('/')),
                            'size': size,
                            'compressed_size': packed,
                            'modified': f"{date} {time}",
                            'attributes': attr,
                            'is_dir': name.endswith('/') or 'D' in attr
                        }
                        entries.append(entry)
                        print(f"Added entry: {entry}")
                        sys.stdout.flush()
                except Exception as e:
                    print(f"Error parsing line: {e}")
                    sys.stdout.flush()
                    continue

            print(f"Finished parsing, found {len(entries)} entries")
            sys.stdout.flush()
            return entries

        except Exception as e:
            print(f"Error in list_contents: {e}")
            sys.stdout.flush()
            raise Exception(f"Error listing archive contents: {str(e)}")
            
    def _parse_list_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse 7z list command output"""
        entries = []
        current_entry = {}
        
        try:
            lines = output.splitlines()
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and headers
                if not line or line.startswith('--'):
                    if current_entry and 'Path' in current_entry:
                        self._process_entry(current_entry, entries)
                    current_entry = {}
                    continue
                    
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'Path':
                        if not value:  # Skip entries with empty paths
                            continue
                        current_entry['path'] = value
                        current_entry['name'] = os.path.basename(value)
                        current_entry['is_dir'] = value.endswith('/') or value.endswith('\\')
                    elif key == 'Size':
                        try:
                            current_entry['size'] = int(value) if value else 0
                        except ValueError:
                            current_entry['size'] = 0
                    elif key == 'Packed Size':
                        try:
                            current_entry['compressed_size'] = int(value) if value else 0
                        except ValueError:
                            current_entry['compressed_size'] = 0
                    elif key == 'Modified':
                        current_entry['modified'] = value
                    elif key == 'Attributes':
                        current_entry['attributes'] = value
                        if 'D' in value:  # Directory attribute
                            current_entry['is_dir'] = True
                        
            # Add the last entry if it exists
            if current_entry and 'Path' in current_entry:
                self._process_entry(current_entry, entries)
                
            return entries
            
        except Exception as e:
            print(f"Error parsing output: {e}")
            raise Exception(f"Error parsing archive listing: {str(e)}")

    def _process_entry(self, entry: Dict[str, Any], entries: List[Dict[str, Any]]) -> None:
        """Process and validate a single entry before adding to entries list"""
        # Ensure required fields exist
        if 'path' not in entry:
            return
            
        # Set defaults for missing fields
        entry.setdefault('size', 0)
        entry.setdefault('compressed_size', entry['size'])
        entry.setdefault('is_dir', False)
        entry.setdefault('modified', '')
        entry.setdefault('attributes', '')
        
        # Clean up path
        entry['path'] = entry['path'].replace('\\', '/')
        
        # Add to entries list
        entries.append(entry)

    def _get_password(self) -> Optional[str]:
        """Get password from environment or prompt user"""
        print("Getting password")
        sys.stdout.flush()
        
        # First try the stored password
        if self._password:
            print("Using stored password")
            sys.stdout.flush()
            return self._password
            
        # Then try environment variable
        env_pass = os.environ.get('SEVENZIP_PASSWORD')
        if env_pass:
            print("Using environment password")
            sys.stdout.flush()
            self._password = env_pass
            return env_pass
            
        print("No password found")
        sys.stdout.flush()
        return None

    def _should_skip(self, filepath):
        """Check if file should be skipped based on patterns"""
        if not self.skip_patterns:
            return False
            
        for pattern in self.skip_patterns:
            if pattern.startswith('**/'):
                # Match anywhere in path
                if fnmatch.fnmatch(filepath, pattern[3:]):
                    return True
            elif pattern.endswith('/**'):
                # Match directory and all contents
                dir_pattern = pattern[:-3]
                path_parts = Path(filepath).parts
                for i in range(len(path_parts)):
                    if fnmatch.fnmatch(str(Path(*path_parts[:i+1])), dir_pattern):
                        return True
            else:
                # Match from start of path
                if fnmatch.fnmatch(filepath, pattern):
                    return True
        return False

class FileInfo:
    """Simple file info class to match zipfile/rarfile interface"""
    def __init__(self, size: int, compressed_size: Optional[int] = None):
        self.file_size = size
        self.compress_size = compressed_size if compressed_size is not None else size
        self.mode = 0o644  # Default mode for extracted files