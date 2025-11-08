"""Enhanced Supabase connector with integrated environment management."""

from supabase import create_client, Client
from .config import Config
from .env_manager import EnvManager
from typing import Optional
import os


class SupabaseConnector:
    """Enhanced Supabase connector that integrates with environment management."""

    def __init__(self):
        """Initialize connector with config and environment management."""
        self.config = Config()
        self.env_manager = EnvManager()
        self.client: Optional[Client] = None
        self.service_client: Optional[Client] = None
        self.active_profile: Optional[dict] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Supabase client based on the active profile."""
        self.active_profile = self.config.get_active_supabase_connection()
        self.client = None
        self.service_client = None

        if not self.active_profile:
            print("No active Supabase profile set in config.")
            return

        profile_name = self.active_profile.get("name", "unknown")

        try:
            # Get credentials based on profile type
            if self.active_profile.get("use_env"):
                # Load from environment variables
                env_vars = self.env_manager.get_env_vars_for_profile(profile_name)
                url = env_vars.get("url")
                anon_key = env_vars.get("anon_key")
                service_key = env_vars.get("service_key")
                source = "environment variables"
            else:
                # Load from profile configuration
                url = self.active_profile.get("url")
                anon_key = self.active_profile.get(
                    "anon_key"
                ) or self.active_profile.get("publishable_key")
                service_key = self.active_profile.get(
                    "service_role_key"
                ) or self.active_profile.get("secret_key")
                source = "profile configuration"

            # Initialize main client with anon key
            if url and anon_key:
                self.client = create_client(url, anon_key)
                print(
                    f"SupabaseConnector initialized for profile: {profile_name} (from {source})"
                )
            else:
                missing = []
                if not url:
                    missing.append("URL")
                if not anon_key:
                    missing.append("anon key")
                print(
                    f"Missing credentials for profile '{profile_name}': {', '.join(missing)}"
                )
                self._print_credential_help(
                    profile_name, self.active_profile.get("use_env", False)
                )

            # Initialize service client if service key is available
            if url and service_key:
                self.service_client = create_client(url, service_key)
                print(f"Service client initialized for profile: {profile_name}")

        except Exception as e:
            print(
                f"Error initializing Supabase client for profile '{profile_name}': {e}"
            )

    def _print_credential_help(self, profile_name: str, use_env: bool):
        """Print helpful messages about missing credentials."""
        if use_env:
            profile_upper = profile_name.upper()
            print(f"  Set environment variables:")
            print(f"    SUPABASE_{profile_upper}_URL=https://your-project.supabase.co")
            print(f"    SUPABASE_{profile_upper}_ANON_KEY=your-anon-key")
            print(f"    SUPABASE_{profile_upper}_SERVICE_KEY=your-service-key")
        else:
            print(f"  Configure credentials in the Supabase profile settings")

    def get_client(self) -> Optional[Client]:
        """Get the main Supabase client (anon key).

        Will re-initialize if the active profile has changed.

        Returns:
            Supabase client instance or None if not configured
        """
        current_active_profile = self.config.get_active_supabase_connection()

        # Re-initialize if profile changed or client is None
        if self.client is None or self.active_profile != current_active_profile:
            print("Re-initializing Supabase client due to profile change...")
            self._initialize_client()

        return self.client

    def get_service_client(self) -> Optional[Client]:
        """Get the service role Supabase client.

        Returns:
            Supabase service client instance or None if not configured
        """
        # Ensure main client is initialized first
        if self.get_client() is None:
            return None

        return self.service_client

    def test_connection(self, use_service_key: bool = False) -> tuple[bool, str]:
        """Test the Supabase connection.

        Args:
            use_service_key: Whether to test with service key instead of anon key

        Returns:
            Tuple of (success, message)
        """
        try:
            client = self.get_service_client() if use_service_key else self.get_client()
            if not client:
                return False, "No client available - check configuration"

            # Try a simple operation
            response = client.table("_test_connection_").select("*").limit(1).execute()
            return True, "Connection successful!"

        except Exception as e:
            error_msg = str(e)
            if "relation" in error_msg and "does not exist" in error_msg:
                return (
                    True,
                    "Connection successful! (Test table doesn't exist, but auth works)",
                )
            elif "Invalid API key" in error_msg or "unauthorized" in error_msg.lower():
                key_type = "service key" if use_service_key else "anon key"
                return False, f"Authentication failed - check your {key_type}"
            elif "not found" in error_msg.lower() or "404" in error_msg:
                return False, "Project not found - check your URL"
            else:
                return False, f"Connection failed: {error_msg}"

    def get_active_profile_name(self) -> Optional[str]:
        """Get the name of the currently active profile."""
        return self.active_profile.get("name") if self.active_profile else None

    def get_active_profile_info(self) -> dict:
        """Get information about the active profile.

        Returns:
            Dictionary with profile information
        """
        if not self.active_profile:
            return {"name": None, "status": "No active profile"}

        profile_name = self.active_profile.get("name", "Unknown")
        use_env = self.active_profile.get("use_env", False)

        info = {
            "name": profile_name,
            "use_env": use_env,
            "source": "environment variables" if use_env else "profile configuration",
            "has_client": self.client is not None,
            "has_service_client": self.service_client is not None,
        }

        # Add credential status
        if use_env:
            env_vars = self.env_manager.get_env_vars_for_profile(profile_name)
            info["credentials"] = {
                "url": bool(env_vars.get("url")),
                "anon_key": bool(env_vars.get("anon_key")),
                "service_key": bool(env_vars.get("service_key")),
            }
        else:
            info["credentials"] = {
                "url": bool(self.active_profile.get("url")),
                "anon_key": bool(
                    self.active_profile.get("anon_key")
                    or self.active_profile.get("publishable_key")
                ),
                "service_key": bool(
                    self.active_profile.get("service_role_key")
                    or self.active_profile.get("secret_key")
                ),
            }

        return info

    def refresh_connection(self):
        """Force refresh of the connection by re-initializing the client."""
        print("Refreshing Supabase connection...")
        self.env_manager.reload()  # Reload environment variables
        self._initialize_client()

    def get_connection_debug_info(self) -> dict:
        """Get detailed debug information about the current connection.

        Returns:
            Dictionary with debug information
        """
        debug_info = {
            "active_profile": self.active_profile,
            "client_status": {
                "main_client": "initialized" if self.client else "not initialized",
                "service_client": "initialized"
                if self.service_client
                else "not initialized",
            },
            "env_file": str(self.env_manager.get_env_file_path()),
            "env_file_exists": self.env_manager.get_env_file_path().exists(),
        }

        if self.active_profile:
            profile_name = self.active_profile.get("name", "")
            use_env = self.active_profile.get("use_env", False)

            debug_info["profile_name"] = profile_name
            debug_info["use_env"] = use_env

            if use_env:
                # Get environment variable information
                env_vars = self.env_manager.get_env_vars_for_profile(profile_name)
                profile_upper = profile_name.upper()

                debug_info["environment_variables"] = {
                    f"SUPABASE_{profile_upper}_URL": {
                        "set": bool(env_vars.get("url")),
                        "value_preview": env_vars.get("url", "")[:50] + "..."
                        if env_vars.get("url")
                        else None,
                    },
                    f"SUPABASE_{profile_upper}_ANON_KEY": {
                        "set": bool(env_vars.get("anon_key")),
                        "value_preview": "***...***"
                        if env_vars.get("anon_key")
                        else None,
                    },
                    f"SUPABASE_{profile_upper}_SERVICE_KEY": {
                        "set": bool(env_vars.get("service_key")),
                        "value_preview": "***...***"
                        if env_vars.get("service_key")
                        else None,
                    },
                }

        return debug_info


# Global connector instance
_connector_instance = None


def get_supabase_connector() -> SupabaseConnector:
    """Get the global Supabase connector instance.

    Returns:
        SupabaseConnector instance
    """
    global _connector_instance
    if _connector_instance is None:
        _connector_instance = SupabaseConnector()
    return _connector_instance


def refresh_supabase_connection():
    """Refresh the global Supabase connection."""
    global _connector_instance
    if _connector_instance:
        _connector_instance.refresh_connection()
    else:
        _connector_instance = SupabaseConnector()


# Convenience functions for backward compatibility
def get_supabase_client() -> Optional[Client]:
    """Get the main Supabase client (convenience function)."""
    return get_supabase_connector().get_client()


def get_supabase_service_client() -> Optional[Client]:
    """Get the service role Supabase client (convenience function)."""
    return get_supabase_connector().get_service_client()
