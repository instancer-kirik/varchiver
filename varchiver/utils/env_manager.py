"""Smart environment manager for handling .env files non-destructively."""

import os
import re
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dotenv import load_dotenv, find_dotenv, set_key, unset_key


class EnvManager:
    """Manages .env files with smart, non-destructive updates."""

    def __init__(self, env_path: Optional[str] = None):
        """Initialize the environment manager.

        Args:
            env_path: Path to .env file. If None, will search for .env in current directory
                     and parent directories.
        """
        self.env_path = Path(env_path) if env_path else self._find_or_create_env_file()
        self._load_env()

    def _find_or_create_env_file(self) -> Path:
        """Find existing .env file or create one in the project root."""
        # First try to find existing .env file
        existing_env = find_dotenv()
        if existing_env:
            return Path(existing_env)

        # If not found, create one in the current working directory
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            env_path.touch()
            # Add a header comment
            env_path.write_text(
                "# Environment variables for Varchiver\n# Auto-generated - do not edit manually unless you know what you're doing\n\n"
            )

        return env_path

    def _load_env(self):
        """Load the .env file into the environment."""
        if self.env_path.exists():
            print(f"DEBUG: Loading .env from {self.env_path}")
            load_dotenv(self.env_path, override=True)
        else:
            print(f"DEBUG: .env file doesn't exist at {self.env_path}")

    def get_env_vars_for_profile(self, profile_name: str) -> Dict[str, Optional[str]]:
        """Get all environment variables for a specific Supabase profile.

        Args:
            profile_name: Name of the Supabase profile

        Returns:
            Dictionary with keys: url, anon_key, service_key and their values
        """
        profile_upper = profile_name.upper()
        return {
            "url": os.getenv(f"SUPABASE_{profile_upper}_URL"),
            "anon_key": os.getenv(f"SUPABASE_{profile_upper}_ANON_KEY")
            or os.getenv(f"SUPABASE_{profile_upper}_PUBLISHABLE_KEY"),
            "service_key": os.getenv(f"SUPABASE_{profile_upper}_SERVICE_KEY")
            or os.getenv(f"SUPABASE_{profile_upper}_SECRET_KEY"),
        }

    def set_env_vars_for_profile(self, profile_name: str, credentials: Dict[str, str]):
        """Set environment variables for a Supabase profile in the .env file.

        Args:
            profile_name: Name of the Supabase profile
            credentials: Dictionary with keys like 'url', 'anon_key', 'service_key'
        """
        profile_upper = profile_name.upper()

        # Create a mapping of credential types to environment variable names
        env_mappings = {
            "url": f"SUPABASE_{profile_upper}_URL",
            "anon_key": f"SUPABASE_{profile_upper}_ANON_KEY",
            "publishable_key": f"SUPABASE_{profile_upper}_ANON_KEY",  # Map to anon_key
            "service_key": f"SUPABASE_{profile_upper}_SERVICE_KEY",
            "service_role_key": f"SUPABASE_{profile_upper}_SERVICE_KEY",  # Map to service_key
            "secret_key": f"SUPABASE_{profile_upper}_SERVICE_KEY",  # Map to service_key
        }

        # Set each credential if it has a value
        for cred_type, value in credentials.items():
            if cred_type in env_mappings and value and value.strip():
                env_var_name = env_mappings[cred_type]
                self._set_env_var(env_var_name, value.strip())

        # Add a comment section for this profile if it doesn't exist
        self._ensure_profile_section(profile_name)

        # Reload environment after changes
        print(
            f"DEBUG: Reloading environment after setting vars for profile {profile_name}"
        )
        self._load_env()

    def _set_env_var(self, key: str, value: str):
        """Set an environment variable in the .env file."""
        print(f"DEBUG: Setting {key}={value[:20]}... in {self.env_path}")
        set_key(str(self.env_path), key, value)
        print(f"DEBUG: Successfully set {key}")

    def _ensure_profile_section(self, profile_name: str):
        """Ensure there's a comment section for the profile in the .env file."""
        if not self.env_path.exists():
            return

        content = self.env_path.read_text()
        profile_comment = f"# {profile_name} Supabase Profile"

        # Check if the profile section already exists
        if profile_comment in content:
            return

        # Find where to insert the profile section
        profile_upper = profile_name.upper()
        pattern = f"SUPABASE_{profile_upper}_"

        lines = content.split("\n")
        insert_line = None

        # Find the first line with this profile's variables
        for i, line in enumerate(lines):
            if pattern in line:
                insert_line = i
                break

        if insert_line is not None:
            # Insert comment before the first variable
            lines.insert(insert_line, profile_comment)
            lines.insert(insert_line + 1, "")  # Add blank line

            # Write back to file
            self.env_path.write_text("\n".join(lines))

    def remove_profile_env_vars(self, profile_name: str):
        """Remove all environment variables for a specific profile from .env file.

        Args:
            profile_name: Name of the Supabase profile to remove
        """
        profile_upper = profile_name.upper()
        env_vars_to_remove = [
            f"SUPABASE_{profile_upper}_URL",
            f"SUPABASE_{profile_upper}_ANON_KEY",
            f"SUPABASE_{profile_upper}_PUBLISHABLE_KEY",
            f"SUPABASE_{profile_upper}_SERVICE_KEY",
            f"SUPABASE_{profile_upper}_SECRET_KEY",
        ]

        for env_var in env_vars_to_remove:
            if os.getenv(env_var):
                unset_key(str(self.env_path), env_var)

        # Remove the profile comment section
        self._remove_profile_section(profile_name)

        # Reload environment after changes
        self._load_env()

    def _remove_profile_section(self, profile_name: str):
        """Remove the comment section for a profile from the .env file."""
        if not self.env_path.exists():
            return

        content = self.env_path.read_text()
        lines = content.split("\n")

        # Find and remove the profile comment and following blank line
        profile_comment = f"# {profile_name} Supabase Profile"
        new_lines = []
        skip_next_blank = False

        for line in lines:
            if line == profile_comment:
                skip_next_blank = True
                continue
            elif skip_next_blank and line.strip() == "":
                skip_next_blank = False
                continue
            else:
                new_lines.append(line)
                skip_next_blank = False

        self.env_path.write_text("\n".join(new_lines))

    def get_all_supabase_profiles(self) -> List[str]:
        """Get a list of all Supabase profile names found in environment variables.

        Returns:
            List of profile names
        """
        profiles = set()
        supabase_pattern = re.compile(
            r"SUPABASE_([A-Z_]+)_(?:URL|ANON_KEY|SERVICE_KEY)"
        )

        for key in os.environ:
            match = supabase_pattern.match(key)
            if match:
                profile_name = match.group(1).lower()
                profiles.add(profile_name)

        return sorted(list(profiles))

    def get_all_supabase_profiles_dict(self) -> Dict[str, Dict[str, str]]:
        """Get all Supabase profiles as a dictionary with their details.

        Returns:
            Dictionary mapping profile names to their credential details
        """
        profiles_dict = {}
        profile_names = self.get_all_supabase_profiles()

        for profile_name in profile_names:
            credentials = self.get_env_vars_for_profile(profile_name)
            profiles_dict[profile_name] = credentials

        return profiles_dict

    def validate_profile_credentials(self, profile_name: str) -> Tuple[bool, List[str]]:
        """Validate that a profile has the minimum required credentials.

        Args:
            profile_name: Name of the Supabase profile

        Returns:
            Tuple of (is_valid, list_of_missing_credentials)
        """
        credentials = self.get_env_vars_for_profile(profile_name)
        missing = []

        if not credentials["url"]:
            missing.append("URL")
        if not credentials["anon_key"]:
            missing.append("Anon Key")

        return len(missing) == 0, missing

    def backup_env_file(self) -> Optional[Path]:
        """Create a backup of the current .env file.

        Returns:
            Path to the backup file, or None if backup failed
        """
        if not self.env_path.exists():
            return None

        try:
            backup_path = self.env_path.with_suffix(".env.backup")
            backup_path.write_text(self.env_path.read_text())
            return backup_path
        except Exception as e:
            print(f"Failed to create backup: {e}")
            return None

    def get_env_file_path(self) -> Path:
        """Get the path to the .env file being managed."""
        return self.env_path

    def reload(self):
        """Reload the .env file from disk."""
        self._load_env()
