"""Utility for managing Supabase connection based on active profile."""

from supabase import create_client, Client
from ..utils.config import Config
from typing import Optional
import os

class SupabaseConnector:
    """Manages the connection to Supabase based on the active profile in config."""
    
    def __init__(self):
        """Initialize connector by loading active profile config."""
        self.config = Config()
        self.client: Client | None = None
        self.active_profile: dict | None = None
        self._initialize_client()

    def _initialize_client(self):
        """(Re)Initializes the Supabase client based on the currently active profile."""
        self.active_profile = self.config.get_active_supabase_connection()
        self.client = None # Reset client
        
        if self.active_profile:
            url = self.active_profile.get('url')
            anon_key = self.active_profile.get('anon_key')
            
            if url and anon_key:
                try:
                    self.client = create_client(url, anon_key)
                    print(f"SupabaseConnector initialized for profile: {self.active_profile.get('name')}")
                except Exception as e:
                    print(f"Error initializing Supabase client for profile '{self.active_profile.get('name')}': {e}")
            else:
                print(f"Supabase URL or Anon Key missing in active profile: {self.active_profile.get('name')}")
        else:
            print("No active Supabase profile set in config.")

    def get_client(self) -> Client | None:
        """Return the Supabase client instance for the active profile.
           Will attempt to re-initialize if the client is None or if the active profile changed.
        """
        current_active_profile = self.config.get_active_supabase_connection()
        # Re-initialize if no client, or if the active profile in config differs from the one used for the current client
        if self.client is None or self.active_profile != current_active_profile:
             print("Re-initializing Supabase client due to change in active profile or null client...")
             self._initialize_client()
             
        return self.client

    def get_service_client(self) -> Client | None:
        """Return a Supabase client instance initialized with the service key 
           for the *currently active* profile.
        """
        active_profile = self.config.get_active_supabase_connection()
        if not active_profile:
             print("Cannot get service client: No active Supabase profile.")
             return None
             
        url = active_profile.get('url')
        service_key = active_profile.get('service_role_key')
        
        if url and service_key:
            try:
                # Create a separate client instance for service role operations
                service_client = create_client(url, service_key)
                return service_client
            except Exception as e:
                print(f"Error initializing Supabase service client for profile '{active_profile.get('name')}': {e}")
                return None
        else:
            print(f"Supabase URL or Service Role Key not found in active profile: '{active_profile.get('name')}'")
            return None

# Note: This is no longer a singleton in the traditional sense.
# Each time you need a connector, you instantiate it, and it reads the *current* active config.
# If you need long-lived instances that *don't* automatically update when the config changes,
# you might need a different pattern (e.g., passing the connector instance around).
# For this UI structure, creating a new connector instance when needed is often simpler.

# Example of how it might be used (no longer a global singleton function):
# connector = SupabaseConnector()
# client = connector.get_client()
# if client:
#     # use client
#     pass 