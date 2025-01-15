import os
import subprocess
import hashlib
import hmac
import base64
import time
from typing import Dict, List, Optional, Tuple, Set, Any
import shutil
import json
import configparser
from pathlib import Path
from .project_constants import SENSITIVE_PATTERNS

class GitSecurityError(Exception):
    """Raised for Git security-related issues."""
    pass

class GitConfigHandler:
    FINGERPRINT_VERSION = 1
    FINGERPRINT_SALT_FILE = '.git_fingerprint_salt'
    GIT_CONFIG_BACKUP_DIR = '.git_config_backup'
    SENSITIVE_PATTERNS = SENSITIVE_PATTERNS
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.git_dir = os.path.join(project_path, '.git')
        
    def is_git_repo(self) -> bool:
        """Check if the directory is a Git repository."""
        if os.path.isfile(self.git_dir):  # Handle Git submodules
            try:
                with open(self.git_dir, 'r') as f:
                    content = f.read().strip()
                if content.startswith('gitdir:'):
                    self.git_dir = os.path.join(self.project_path, content.split(':', 1)[1].strip())
                    return os.path.exists(self.git_dir)
            except (IOError, OSError):
                return False
        return os.path.exists(self.git_dir) and os.path.isdir(self.git_dir)
    
    def _generate_salt(self) -> bytes:
        """Generate a cryptographically secure salt."""
        return os.urandom(32)

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create a new one."""
        salt_path = os.path.join(self.git_dir, self.FINGERPRINT_SALT_FILE)
        try:
            if os.path.exists(salt_path):
                with open(salt_path, 'rb') as f:
                    return f.read()
            else:
                salt = self._generate_salt()
                with open(salt_path, 'wb') as f:
                    f.write(salt)
                return salt
        except (IOError, OSError) as e:
            raise GitSecurityError(f"Failed to handle salt: {e}")

    def _compute_file_hash(self, filepath: str) -> str:
        """Compute a secure hash of a file's contents."""
        try:
            if os.path.isdir(filepath):
                # For directories, hash their path and existence
                return hashlib.sha256(filepath.encode('utf-8')).hexdigest()
                
            sha256 = hashlib.sha256()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (IOError, OSError) as e:
            raise GitSecurityError(f"Failed to hash file {filepath}: {e}")

    def _get_git_files(self) -> List[str]:
        """Get list of all Git-tracked files."""
        try:
            result = subprocess.run(
                ['git', 'ls-files', '-z'],
                cwd=self.project_path,
                capture_output=True,
                check=True
            )
            return [f for f in result.stdout.decode('utf-8').split('\0') if f]
        except subprocess.SubprocessError as e:
            raise GitSecurityError(f"Failed to list Git files: {e}")

    def generate_fingerprint(self) -> Dict:
        """
        Generate a secure fingerprint of the Git repository state.
        This includes:
        - File hashes of all tracked files
        - Git configuration state
        - Repository structure
        - Submodule states
        """
        if not self.is_git_repo():
            raise GitSecurityError("Not a Git repository")

        try:
            # Get repository salt
            salt = self._get_or_create_salt()
            
            # Get all tracked files and their hashes
            files_data = {}
            for filepath in self._get_git_files():
                abs_path = os.path.join(self.project_path, filepath)
                if os.path.exists(abs_path):
                    files_data[filepath] = self._compute_file_hash(abs_path)

            # Get repository state
            repo_state = {
                'head': self._get_head_ref(),
                'config': self._get_local_config(),
                'remotes': self._get_remotes(),
                'branches': self._get_branches(),
                'submodules': self._get_submodules(),
            }

            # Create composite fingerprint
            fingerprint_data = {
                'version': self.FINGERPRINT_VERSION,
                'timestamp': int(time.time()),
                'files': files_data,
                'repo_state': repo_state
            }

            # Generate HMAC of the fingerprint data
            data_bytes = json.dumps(fingerprint_data, sort_keys=True).encode('utf-8')
            hmac_obj = hmac.new(salt, data_bytes, hashlib.sha256)
            
            fingerprint = {
                'data': fingerprint_data,
                'hmac': base64.b64encode(hmac_obj.digest()).decode('utf-8')
            }

            return fingerprint

        except Exception as e:
            raise GitSecurityError(f"Failed to generate fingerprint: {e}")

    def verify_fingerprint(self, fingerprint: Dict) -> bool:
        """
        Verify a repository fingerprint.
        Returns True if the fingerprint is valid and matches the current state.
        """
        if not self.is_git_repo():
            return False

        try:
            # Verify fingerprint structure
            if not isinstance(fingerprint, dict) or 'data' not in fingerprint or 'hmac' not in fingerprint:
                return False

            # Get salt
            salt = self._get_or_create_salt()

            # Verify HMAC
            data_bytes = json.dumps(fingerprint['data'], sort_keys=True).encode('utf-8')
            expected_hmac = base64.b64decode(fingerprint['hmac'])
            hmac_obj = hmac.new(salt, data_bytes, hashlib.sha256)
            
            try:
                hmac.compare_digest(hmac_obj.digest(), expected_hmac)
            except Exception:
                return False

            # Generate current fingerprint for comparison
            current = self.generate_fingerprint()
            
            # Compare relevant fields (excluding timestamp)
            old_data = fingerprint['data']
            new_data = current['data']
            
            # Compare version
            if old_data['version'] != new_data['version']:
                return False
                
            # Compare files
            if old_data['files'] != new_data['files']:
                return False
                
            # Compare repository state
            if old_data['repo_state'] != new_data['repo_state']:
                return False

            return True

        except Exception:
            return False

    def get_git_config(self) -> Dict:
        """Extract Git configuration including remotes, branches, and submodules."""
        if not self.is_git_repo():
            return {}
            
        config = {
            'remotes': self._get_remotes(),
            'branches': self._get_branches(),
            'config': self._get_local_config(),
            'head': self._get_head_ref(),
            'hooks': self._get_hooks(),
            'submodules': self._get_submodules(),
            'modules': self._get_modules(),
            'gitignores': {}  # Store all .gitignore files
        }

        # Add .gitignore content if it exists
        for root, _, files in os.walk(self.project_path):
            # Skip deps directories
            if 'deps' in root.split(os.sep):
                continue

            if '.gitignore' in files:
                gitignore_path = os.path.join(root, '.gitignore')
                try:
                    with open(gitignore_path, 'r') as f:
                        rel_path = os.path.relpath(root, self.project_path)
                        config['gitignores'][rel_path] = f.read()
                except (IOError, OSError):
                    pass

        return config
        
    def _get_remotes(self) -> Dict[str, str]:
        """Get all configured remotes and their URLs."""
        try:
            result = subprocess.run(
                ['git', 'remote', '-v'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            remotes = {}
            for line in result.stdout.splitlines():
                if '(fetch)' in line:  # Only process fetch lines
                    name, url, _ = line.split()
                    remotes[name] = url
            return remotes
        except subprocess.SubprocessError:
            return {}
            
    def _get_branches(self) -> Dict[str, str]:
        """Get all local branches and their tracking remotes."""
        try:
            result = subprocess.run(
                ['git', 'branch', '-vv'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            branches = {}
            for line in result.stdout.splitlines():
                if line.strip():
                    # Parse branch info
                    parts = line.strip().split()
                    name = parts[1] if line.startswith('*') else parts[0]
                    tracking = None
                    for part in parts:
                        if '[' in part and ']' in part:
                            tracking = part[1:-1].split(':')[0]
                    branches[name] = tracking
            return branches
        except subprocess.SubprocessError:
            return {}
            
    def _get_local_config(self) -> Dict:
        """Get repository-specific Git configuration."""
        try:
            result = subprocess.run(
                ['git', 'config', '--local', '--list'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            config = {}
            for line in result.stdout.splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key] = value
            return config
        except subprocess.SubprocessError:
            return {}
            
    def _get_head_ref(self) -> Optional[str]:
        """Get the current HEAD reference."""
        head_file = os.path.join(self.git_dir, 'HEAD')
        try:
            with open(head_file, 'r') as f:
                return f.read().strip()
        except (IOError, OSError):
            return None
            
    def _get_hooks(self) -> Dict[str, str]:
        """Get all Git hooks and their contents."""
        hooks_dir = os.path.join(self.git_dir, 'hooks')
        hooks = {}
        if os.path.exists(hooks_dir):
            for hook in os.listdir(hooks_dir):
                if not hook.endswith('.sample'):
                    hook_path = os.path.join(hooks_dir, hook)
                    try:
                        with open(hook_path, 'r') as f:
                            hooks[hook] = f.read()
                    except (IOError, OSError):
                        continue
        return hooks

    def _get_submodules(self) -> Dict[str, Dict]:
        """Get all submodules and their configurations."""
        submodules = {}
        gitmodules_path = os.path.join(self.project_path, '.gitmodules')
        
        if os.path.exists(gitmodules_path):
            config = configparser.ConfigParser()
            try:
                config.read(gitmodules_path)
                for section in config.sections():
                    if section.startswith('submodule'):
                        name = section.split('"')[1]
                        submodules[name] = {
                            'path': config.get(section, 'path'),
                            'url': config.get(section, 'url'),
                            'branch': config.get(section, 'branch', fallback=None)
                        }
                        
                        # Get submodule commit
                        submodule_path = os.path.join(self.project_path, config.get(section, 'path'))
                        if os.path.exists(submodule_path):
                            try:
                                result = subprocess.run(
                                    ['git', 'rev-parse', 'HEAD'],
                                    cwd=submodule_path,
                                    capture_output=True,
                                    text=True
                                )
                                if result.returncode == 0:
                                    submodules[name]['commit'] = result.stdout.strip()
                            except subprocess.SubprocessError:
                                pass
            except (configparser.Error, IOError):
                pass
                
        return submodules

    def _get_modules(self) -> Dict[str, Dict]:
        """Get all Git modules (separate Git repos in subdirectories)."""
        modules = {}
        for root, dirs, _ in os.walk(self.project_path):
            if '.git' in dirs and root != self.project_path and not self._is_submodule(root):
                rel_path = os.path.relpath(root, self.project_path)
                handler = GitConfigHandler(root)
                if handler.is_git_repo():
                    modules[rel_path] = handler.get_git_config()
        return modules

    def _is_submodule(self, path: str) -> bool:
        """Check if a path is a Git submodule."""
        git_file = os.path.join(path, '.git')
        if os.path.isfile(git_file):
            try:
                with open(git_file, 'r') as f:
                    return f.read().strip().startswith('gitdir:')
            except (IOError, OSError):
                pass
        return False
        
    def save_config(self, output_path: str):
        """Save Git configuration to a JSON file."""
        config = self.get_git_config()
        if config:
            with open(output_path, 'w') as f:
                json.dump(config, f, indent=2)
                
    @staticmethod
    def restore_config(config_path: str, target_dir: str) -> bool:
        """Restore Git configuration from a saved JSON file."""
        try:
            # Skip deps directories
            if 'deps' in target_dir.split(os.sep):
                return True  # Return success since we intentionally skip deps
                
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Initialize Git repository
            subprocess.run(['git', 'init'], cwd=target_dir, check=True)
            
            # Restore remotes
            for name, url in config.get('remotes', {}).items():
                subprocess.run(
                    ['git', 'remote', 'add', name, url],
                    cwd=target_dir
                )
                
            # Restore local config
            for key, value in config.get('config', {}).items():
                subprocess.run(
                    ['git', 'config', '--local', key, value],
                    cwd=target_dir
                )
                
            # Restore .gitignore if it exists in the backup
            if 'gitignores' in config:
                for rel_path, content in config['gitignores'].items():
                    # Skip deps directories
                    if 'deps' in rel_path.split(os.sep):
                        continue
                    gitignore_path = os.path.join(target_dir, rel_path, '.gitignore')
                    os.makedirs(os.path.dirname(gitignore_path), exist_ok=True)
                    try:
                        with open(gitignore_path, 'w') as f:
                            f.write(content)
                    except (IOError, OSError):
                        pass
            # Restore hooks
            hooks_dir = os.path.join(target_dir, '.git', 'hooks')
            os.makedirs(hooks_dir, exist_ok=True)
            for hook_name, content in config.get('hooks', {}).items():
                hook_path = os.path.join(hooks_dir, hook_name)
                with open(hook_path, 'w') as f:
                    f.write(content)
                os.chmod(hook_path, 0o755)  # Make hook executable

            # Restore submodules
            if config.get('submodules'):
                gitmodules_path = os.path.join(target_dir, '.gitmodules')
                with open(gitmodules_path, 'w') as f:
                    for name, submodule in config['submodules'].items():
                        f.write(f'[submodule "{name}"]\n')
                        f.write(f'\tpath = {submodule["path"]}\n')
                        f.write(f'\turl = {submodule["url"]}\n')
                        if submodule.get('branch'):
                            f.write(f'\tbranch = {submodule["branch"]}\n')
                        f.write('\n')
                
                # Initialize and update submodules
                subprocess.run(['git', 'submodule', 'init'], cwd=target_dir)
                subprocess.run(['git', 'submodule', 'update'], cwd=target_dir)

                # Checkout specific commits if available
                for name, submodule in config['submodules'].items():
                    if submodule.get('commit'):
                        submodule_path = os.path.join(target_dir, submodule['path'])
                        subprocess.run(
                            ['git', 'checkout', submodule['commit']],
                            cwd=submodule_path
                        )

            # Restore nested modules
            for rel_path, module_config in config.get('modules', {}).items():
                module_path = os.path.join(target_dir, rel_path)
                os.makedirs(module_path, exist_ok=True)
                
                # Create temporary config file for module
                temp_config = os.path.join(module_path, 'temp_git_config.json')
                with open(temp_config, 'w') as f:
                    json.dump(module_config, f, indent=2)
                    
                # Restore module configuration
                success = GitConfigHandler.restore_config(temp_config, module_path)
                os.unlink(temp_config)
                
                if not success:
                    print(f"Warning: Failed to restore Git module at {rel_path}")
                
            return True
        except Exception as e:
            print(f"Error restoring Git config: {e}")
            return False
            
    @staticmethod
    def verify_archive_structure(archive_dir: str) -> bool:
        """
        Verify that an archive has the expected Git configuration structure.
        """
        try:
            backup_dir = os.path.join(archive_dir, GitConfigHandler.GIT_CONFIG_BACKUP_DIR)
            if not os.path.exists(backup_dir):
                return False
                
            # Check for essential files
            required_files = ['fingerprint.json', 'config.json']
            for file in required_files:
                if not os.path.exists(os.path.join(backup_dir, file)):
                    return False
                    
            # Verify fingerprint structure
            with open(os.path.join(backup_dir, 'fingerprint.json'), 'r') as f:
                fingerprint = json.load(f)
                if not isinstance(fingerprint, dict) or 'data' not in fingerprint or 'hmac' not in fingerprint:
                    return False
                    
            return True
        except Exception:
            return False
            
    @staticmethod
    def extract_from_archive(archive_dir: str, target_dir: str, verify: bool = True) -> Tuple[bool, str]:
        """
        Extract and verify Git configuration from an archive.
        Returns (success, message).
        """
        try:
            backup_dir = os.path.join(archive_dir, GitConfigHandler.GIT_CONFIG_BACKUP_DIR)
            if not os.path.exists(backup_dir):
                return False, "Git configuration backup not found in archive"
                
            # Load fingerprint
            try:
                with open(os.path.join(backup_dir, 'fingerprint.json'), 'r') as f:
                    fingerprint = json.load(f)
            except Exception as e:
                return False, f"Failed to load fingerprint: {e}"
                
            # Load configuration
            try:
                with open(os.path.join(backup_dir, 'config.json'), 'r') as f:
                    config = json.load(f)
            except Exception as e:
                return False, f"Failed to load configuration: {e}"
                
            # Initialize Git repository
            if not os.path.exists(os.path.join(target_dir, '.git')):
                try:
                    subprocess.run(['git', 'init'], cwd=target_dir, check=True)
                except subprocess.SubprocessError as e:
                    return False, f"Failed to initialize Git repository: {e}"
                    
            handler = GitConfigHandler(target_dir)
            
            # Restore configuration
            success = handler.restore_config(os.path.join(backup_dir, 'config.json'), target_dir)
            if not success:
                return False, "Failed to restore Git configuration"
                
            if verify:
                # Generate new fingerprint and compare
                try:
                    current_fingerprint = handler.generate_fingerprint()
                    if not handler.verify_fingerprint(fingerprint):
                        return False, "Repository state verification failed"
                except GitSecurityError as e:
                    return False, f"Security verification failed: {e}"
                    
            return True, "Git configuration successfully restored"
            
        except Exception as e:
            return False, f"Failed to extract Git configuration: {e}"
            
    def update_from_archive(self, archive_dir: str, force: bool = False) -> Tuple[bool, str]:
        """
        Update existing Git repository from archive configuration.
        Returns (success, message).
        """
        if not self.is_git_repo():
            return False, "Not a Git repository"
            
        try:
            backup_dir = os.path.join(archive_dir, self.GIT_CONFIG_BACKUP_DIR)
            if not os.path.exists(backup_dir):
                return False, "Git configuration backup not found in archive"
                
            # Load archive fingerprint
            try:
                with open(os.path.join(backup_dir, 'fingerprint.json'), 'r') as f:
                    archive_fingerprint = json.load(f)
            except Exception as e:
                return False, f"Failed to load archive fingerprint: {e}"
                
            # Generate current fingerprint
            try:
                current_fingerprint = self.generate_fingerprint()
            except GitSecurityError as e:
                return False, f"Failed to generate current fingerprint: {e}"
                
            # Compare fingerprints
            if not force:
                archive_state = archive_fingerprint['data']['repo_state']
                current_state = current_fingerprint['data']['repo_state']
                
                # Check for conflicts
                conflicts = []
                
                # Check remotes
                for name, url in current_state['remotes'].items():
                    if name in archive_state['remotes'] and url != archive_state['remotes'][name]:
                        conflicts.append(f"Remote '{name}' has different URL")
                        
                # Check branches
                for name, tracking in current_state['branches'].items():
                    if name in archive_state['branches'] and tracking != archive_state['branches'][name]:
                        conflicts.append(f"Branch '{name}' has different tracking")
                        
                if conflicts:
                    return False, "Conflicts detected: " + "; ".join(conflicts)
                    
            # Backup current configuration
            timestamp = int(time.time())
            backup_path = os.path.join(self.git_dir, f'config.backup.{timestamp}.json')
            try:
                with open(backup_path, 'w') as f:
                    json.dump(current_fingerprint, f, indent=2)
            except Exception as e:
                return False, f"Failed to backup current configuration: {e}"
                
            # Restore configuration from archive
            try:
                success = self.restore_config(os.path.join(backup_dir, 'config.json'), self.project_path)
                if not success:
                    # Attempt to rollback
                    self.restore_config(backup_path, self.project_path)
                    return False, "Failed to restore archive configuration"
            except Exception as e:
                # Attempt to rollback
                self.restore_config(backup_path, self.project_path)
                return False, f"Failed to update configuration: {e}"
                
            return True, "Git configuration successfully updated"
            
        except Exception as e:
            return False, f"Failed to update from archive: {str(e)}"

    def check_gitignore_security(self) -> Tuple[bool, List[str]]:
        """
        Check if .gitignore contains necessary security patterns.
        Returns (is_secure, missing_patterns).
        """
        if not self.is_git_repo():
            return False, ["Not a Git repository"]
            
        # Get all gitignore patterns
        patterns = set()
        
        # Check repository .gitignore
        gitignore_path = os.path.join(self.project_path, '.gitignore')
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            patterns.add(line)
            except Exception as e:
                return False, [f"Failed to read .gitignore: {e}"]
                
        # Check global gitignore if available
        try:
            result = subprocess.run(
                ['git', 'config', '--global', '--get', 'core.excludesfile'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                global_gitignore = os.path.expanduser(result.stdout.strip())
                if os.path.exists(global_gitignore):
                    with open(global_gitignore, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                patterns.add(line)
        except Exception:
            # Ignore errors reading global gitignore
            pass
            
        # Check which sensitive patterns are missing
        missing = []
        for sensitive in self.SENSITIVE_PATTERNS:
            if not any(self._pattern_matches(sensitive, p) for p in patterns):
                missing.append(sensitive)
                
        return len(missing) == 0, missing
        
    def _pattern_matches(self, sensitive: str, gitignore: str) -> bool:
        """Check if a gitignore pattern covers a sensitive pattern"""
        # Convert gitignore pattern to regex
        regex = gitignore.replace('.', r'\.')
        regex = regex.replace('*', '.*')
        regex = regex.replace('?', '.')
        regex = f"^{regex}$"
        
        import re
        try:
            return bool(re.match(regex, sensitive))
        except re.error:
            return False

    def _get_nested_git_dirs(self) -> List[str]:
        """Get all git directories, including those in subdirectories."""
        git_dirs = []
        
        # First add the main .git directory if it exists
        if self.is_git_repo():
            git_dirs.append(self.git_dir)
            
        # Then look for git directories in subdirectories
        for root, dirs, _ in os.walk(self.project_path):
            # Skip deps directories
            if 'deps' in root.split(os.sep):
                continue

            if '.git' in dirs:
                git_dir = os.path.join(root, '.git')
                # Check if it's a real git dir or just a submodule reference
                if os.path.isdir(git_dir):
                    git_dirs.append(git_dir)
                else:
                    try:
                        with open(git_dir, 'r') as f:
                            content = f.read().strip()
                        if content.startswith('gitdir:'):
                            actual_git_dir = os.path.join(root, content.split(':', 1)[1].strip())
                            if os.path.exists(actual_git_dir):
                                git_dirs.append(actual_git_dir)
                    except (IOError, OSError):
                        continue
                        
        return git_dirs

    def serialize_git_files(self) -> Dict:
        """
        Serialize all git-related files into a dictionary that can be stored.
        Returns a dictionary containing:
        - files: Dict[str, bytes] - all git file contents
        - config: Dict - git configuration
        - fingerprint: Dict - repository fingerprint
        - nested_git_configs: List[Dict] - configurations from nested git repositories
        """
        try:
            # Get all git directories
            git_dirs = self._get_nested_git_dirs()
            
            # Process main repository
            result = {
                'files': {},
                'config': self.get_git_config(),
                'fingerprint': self.generate_fingerprint(),
                'nested_git_configs': []
            }
            
            # Add files from main .git directory
            if self.is_git_repo():
                for root, _, files in os.walk(self.git_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.git_dir)
                        try:
                            with open(file_path, 'rb') as f:
                                result['files'][rel_path] = base64.b64encode(f.read()).decode('utf-8')
                        except (IOError, OSError):
                            continue
            
            # Process nested git repositories
            for git_dir in git_dirs:
                if git_dir == self.git_dir:
                    continue  # Skip main repository as it's already processed
                    
                repo_path = os.path.dirname(git_dir)
                nested_handler = GitConfigHandler(repo_path)
                
                nested_config = {
                    'path': os.path.relpath(repo_path, self.project_path),
                    'files': {},
                    'config': nested_handler.get_git_config(),
                    'fingerprint': nested_handler.generate_fingerprint()
                }
                
                # Add files from nested .git directory
                for root, _, files in os.walk(git_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, git_dir)
                        try:
                            with open(file_path, 'rb') as f:
                                nested_config['files'][rel_path] = base64.b64encode(f.read()).decode('utf-8')
                        except (IOError, OSError):
                            continue
                            
                result['nested_git_configs'].append(nested_config)
            
            return result
            
        except Exception as e:
            raise GitSecurityError(f"Failed to serialize git files: {e}")

    def restore_git_files(self, backup_path: str) -> bool:
        """
        Restore git files from a serialized backup.
        Returns True if successful.
        """
        try:
            with open(backup_path, 'r') as f:
                data = json.load(f)
                
            # Process main repository files
            for rel_path, content in data.get('files', {}).items():
                file_path = os.path.join(self.git_dir, rel_path)
                # Skip deps directories
                if 'deps' in file_path.split(os.sep):
                    continue
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb') as f:
                        f.write(base64.b64decode(content))
                except (IOError, OSError):
                    continue
            
            # Process nested repositories
            for nested_config in data.get('nested_git_configs', []):
                repo_path = os.path.join(self.project_path, nested_config['path'])
                # Skip deps directories
                if 'deps' in repo_path.split(os.sep):
                    continue
                git_dir = os.path.join(repo_path, '.git')
                
                for rel_path, content in nested_config.get('files', {}).items():
                    file_path = os.path.join(git_dir, rel_path)
                    try:
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'wb') as f:
                            f.write(base64.b64decode(content))
                    except (IOError, OSError):
                        continue
            
            return True
            
        except Exception as e:
            raise GitSecurityError(f"Failed to restore git files: {e}")

    def remove_git_files(self, backup_path: Optional[str] = None) -> bool:
        """
        Remove all git-related files from the repository.
        If backup_path is provided, first save the serialized git files there.
        Returns True if successful.
        """
        try:
            # First backup if requested
            if backup_path:
                serialized = self.serialize_git_files()
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                with open(backup_path, 'w') as f:
                    json.dump(serialized, f, indent=2)
            
            # Get all git directories
            git_dirs = self._get_nested_git_dirs()
            
            # Remove all git directories
            for git_dir in git_dirs:
                # Skip deps directories
                if 'deps' in git_dir.split(os.sep):
                    continue
                try:
                    if os.path.exists(git_dir):
                        shutil.rmtree(git_dir)
                except (IOError, OSError) as e:
                    print(f"Warning: Failed to remove {git_dir}: {e}")
                    
            # Also remove .gitignore files
            for root, _, files in os.walk(self.project_path):
                # Skip deps directories
                if 'deps' in root.split(os.sep):
                    continue
                if '.gitignore' in files:
                    try:
                        os.remove(os.path.join(root, '.gitignore'))
                    except (IOError, OSError) as e:
                        print(f"Warning: Failed to remove {root}/.gitignore: {e}")
                    
            return True
            
        except Exception as e:
            raise GitSecurityError(f"Failed to remove git files: {e}")
        
def backup_git_configs(source_dir: str, backup_dir: str, visited: Optional[Set[str]] = None) -> List[str]:
    """
    Scan directory for Git repositories and backup their configurations.
    Returns list of backed up config paths.
    """
    if visited is None:
        visited = set()
        
    config_paths = []
    for root, dirs, _ in os.walk(source_dir):
        if '.git' in dirs and root not in visited:
            visited.add(root)
            repo_path = root
            handler = GitConfigHandler(repo_path)
            if handler.is_git_repo():
                relative_path = os.path.relpath(repo_path, source_dir)
                config_file = os.path.join(backup_dir, f"{relative_path.replace(os.sep, '_')}_git.json")
                os.makedirs(os.path.dirname(config_file), exist_ok=True)
                handler.save_config(config_file)
                config_paths.append(config_file)
                
                # Process submodules
                submodules = handler.get_git_config().get('submodules', {})
                for submodule in submodules.values():
                    submodule_path = os.path.join(repo_path, submodule['path'])
                    if os.path.exists(submodule_path) and submodule_path not in visited:
                        sub_configs = backup_git_configs(submodule_path, backup_dir, visited)
                        config_paths.extend(sub_configs)
                        
    return config_paths
    
def restore_git_configs(backup_dir: str, target_dir: str) -> List[Tuple[str, bool]]:
    """
    Restore Git configurations from backup directory.
    Returns list of (config_path, success) tuples.
    """
    results = []
    for root, _, files in os.walk(backup_dir):
        for file in files:
            if file.endswith('_git.json'):
                config_path = os.path.join(root, file)
                # Extract original repo path from filename
                repo_name = file[:-9]  # Remove '_git.json'
                repo_path = os.path.join(target_dir, repo_name.replace('_', os.sep))
                success = GitConfigHandler.restore_config(config_path, repo_path)
                results.append((config_path, success))
    return results
