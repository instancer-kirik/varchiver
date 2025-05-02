"""Configuration settings for the application."""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional

# Default configuration structure
DEFAULT_CONFIG = {
    'database': {
        'type': 'postgresql',
        'host': 'localhost',
        'port': 5432,
        'dbname': 'varchiver',
        'user': 'postgres',
        'password': ''  # Should be set by user
    },
    'variable_calendar': {
        'default_view': 'calendar',  # or 'list'
        'date_format': '%Y-%m-%d',
        'time_format': '%H:%M:%S',
        'auto_refresh': True,
        'refresh_interval': 60  # seconds
    },
    'supabase_connections': [], # List of connection profiles
    'active_supabase_connection_name': None # Name of the currently active profile
}

# Example structure for a profile within 'supabase_connections':
# {
#     "name": "My Project",
#     "url": "https://...".supabase.co",
#     "anon_key": "ey...",
#     "service_role_key": "ey..."
# }

class Config:
    """Configuration manager."""
    
    def __init__(self):
        """Initialize configuration."""
        self.config_dir = Path.home() / '.config' / 'varchiver'
        self.config_file = self.config_dir / 'config.json'
        self.config = {} # Start empty, load will merge with defaults
        self.load_config() # Load first, then ensure defaults exist
        self._ensure_defaults()
        
    def _ensure_defaults(self):
        """Ensure all default keys exist in the loaded config."""
        for key, default_value in DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = default_value
            elif isinstance(default_value, dict):
                # Ensure nested defaults exist too
                for sub_key, sub_default_value in default_value.items():
                    if sub_key not in self.config[key]:
                        self.config[key][sub_key] = sub_default_value
        self.save_config() # Save if defaults were added
        
    def load_config(self):
        """Load configuration from file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                # If no config file, start with defaults
                self.config = DEFAULT_CONFIG.copy()
                self.save_config()
        except json.JSONDecodeError:
            print("Error decoding config file. Starting with defaults.")
            self.config = DEFAULT_CONFIG.copy()
            self.save_config()
        except Exception as e:
            print(f"Error loading config: {e}. Starting with defaults.")
            self.config = DEFAULT_CONFIG.copy()
            # No save here to avoid overwriting potentially recoverable file

    def save_config(self):
        """Save configuration to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
            
    def get_database_config(self):
        """Get database configuration."""
        return self.config.get('database', DEFAULT_CONFIG['database'])
        
    def set_database_config(self, **kwargs):
        """Set database configuration parameters."""
        if 'database' not in self.config:
             self.config['database'] = {}
        self.config['database'].update(kwargs)
        self.save_config()
        
    def get_variable_calendar_config(self):
        """Get variable calendar configuration."""
        return self.config.get('variable_calendar', DEFAULT_CONFIG['variable_calendar'])
        
    def set_variable_calendar_config(self, **kwargs):
        """Set variable calendar configuration parameters."""
        if 'variable_calendar' not in self.config:
             self.config['variable_calendar'] = {}
        self.config['variable_calendar'].update(kwargs)
        self.save_config()

    # --- Supabase Connection Management ---
    
    def get_supabase_connections(self) -> List[Dict]:
        """Get the list of all Supabase connection profiles."""
        return self.config.get('supabase_connections', [])

    def get_supabase_connection_by_name(self, name: str) -> Optional[Dict]:
        """Find a specific Supabase connection profile by its name."""
        for profile in self.get_supabase_connections():
            if profile.get('name') == name:
                return profile
        return None

    def add_supabase_connection(self, profile: Dict) -> bool:
        """Add a new Supabase connection profile. Returns False if name exists."""
        connections = self.get_supabase_connections()
        profile_name = profile.get('name')
        if not profile_name:
            raise ValueError("Profile must have a 'name'.")
        if self.get_supabase_connection_by_name(profile_name):
            return False # Name already exists
            
        connections.append(profile)
        self.config['supabase_connections'] = connections
        # If it's the first one added, make it active
        if len(connections) == 1:
            self.set_active_supabase_connection_name(profile_name)
        self.save_config()
        return True

    def update_supabase_connection(self, name: str, updated_profile: Dict) -> bool:
        """Update an existing Supabase connection profile. Returns False if not found."""
        connections = self.get_supabase_connections()
        found = False
        for i, profile in enumerate(connections):
            if profile.get('name') == name:
                # Ensure the name isn't changed to conflict with another existing name
                new_name = updated_profile.get('name', name)
                if new_name != name and self.get_supabase_connection_by_name(new_name):
                    raise ValueError(f"Cannot rename profile to '{new_name}', name already exists.")
                connections[i] = updated_profile
                found = True
                break
        if found:
            self.config['supabase_connections'] = connections
            # Update active name if the updated profile was the active one and its name changed
            active_name = self.get_active_supabase_connection_name()
            if active_name == name and updated_profile.get('name') != name:
                self.set_active_supabase_connection_name(updated_profile.get('name'))
            self.save_config()
            return True
        return False

    def delete_supabase_connection(self, name: str) -> bool:
        """Delete a Supabase connection profile by name. Returns False if not found."""
        connections = self.get_supabase_connections()
        original_length = len(connections)
        connections = [p for p in connections if p.get('name') != name]
        
        if len(connections) < original_length:
            self.config['supabase_connections'] = connections
            # If the deleted profile was active, unset the active profile
            if self.get_active_supabase_connection_name() == name:
                self.set_active_supabase_connection_name(None)
            self.save_config()
            return True
        return False

    def get_active_supabase_connection_name(self) -> Optional[str]:
        """Get the name of the currently active Supabase connection profile."""
        return self.config.get('active_supabase_connection_name')

    def set_active_supabase_connection_name(self, name: Optional[str]) -> bool:
        """Set the active Supabase connection profile by name. Returns False if name not found (unless name is None)."""
        if name is None:
             self.config['active_supabase_connection_name'] = None
             self.save_config()
             return True
        elif self.get_supabase_connection_by_name(name):
            self.config['active_supabase_connection_name'] = name
            self.save_config()
            return True
        return False
        
    def get_active_supabase_connection(self) -> Optional[Dict]:
        """Get the details of the currently active Supabase connection profile."""
        active_name = self.get_active_supabase_connection_name()
        if active_name:
            return self.get_supabase_connection_by_name(active_name)
        # If no active one, maybe return the first one? Or None.
        connections = self.get_supabase_connections()
        if connections: # Return first one if no specific active one is set
             # self.set_active_supabase_connection_name(connections[0].get('name')) # Optionally set it active too
             # return connections[0]
             pass
        return None 