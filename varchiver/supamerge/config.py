"""
Configuration utilities for Supamerge.
Handles loading, saving, and validating migration configurations.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from .core import SourceConfig, TargetConfig, MigrationOptions, ConfigurationError


class SupamergeConfig:
    """Manages Supamerge configuration files and templates."""

    def __init__(self):
        self.config_dir = Path.home() / ".config" / "supamerge"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def create_template_config(self, output_path: str) -> None:
        """Create a template configuration file."""
        template = {
            "source": {
                "project_ref": "your-source-project-ref",
                "db_url": "$SUPABASE_DB_URL_SOURCE",
                "supabase_url": "https://your-source-project.supabase.co",
                "anon_key": "$SUPABASE_ANON_KEY_SOURCE",
                "service_role_key": "$SUPABASE_SERVICE_KEY_SOURCE",
            },
            "target": {
                "project_ref": "your-target-project-ref",
                "db_url": "$SUPABASE_DB_URL_TARGET",
                "supabase_url": "https://your-target-project.supabase.co",
                "anon_key": "$SUPABASE_ANON_KEY_TARGET",
                "service_role_key": "$SUPABASE_SERVICE_KEY_TARGET",
            },
            "include": {
                "schemas": ["public"],
                "include_data": True,
                "include_policies": True,
                "include_storage": True,
            },
            "options": {
                "backup_target_first": True,
                "remap_conflicts": True,
                "skip_auth": False,
                "dry_run": False,
            },
        }

        with open(output_path, "w") as f:
            yaml.dump(template, f, default_flow_style=False, indent=2)

    def expand_environment_variables(
        self, config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Expand environment variables in configuration values."""

        def expand_value(value):
            if isinstance(value, str) and value.startswith("$"):
                env_var = value[1:]  # Remove the $ prefix
                return os.getenv(env_var, value)  # Return original if env var not found
            elif isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand_value(item) for item in value]
            return value

        return expand_value(config_data)

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load and validate configuration from YAML file."""
        if not os.path.exists(config_path):
            raise ConfigurationError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in config file: {e}")

        # Expand environment variables
        config_data = self.expand_environment_variables(config_data)

        # Validate required sections
        self._validate_config_structure(config_data)

        return config_data

    def _validate_config_structure(self, config_data: Dict[str, Any]) -> None:
        """Validate the basic structure of configuration data."""
        required_sections = ["source", "target"]
        for section in required_sections:
            if section not in config_data:
                raise ConfigurationError(f"Missing required section: {section}")

        # Validate source configuration
        source = config_data["source"]
        required_source_fields = ["project_ref", "db_url", "supabase_url"]
        for field in required_source_fields:
            if field not in source or not source[field]:
                raise ConfigurationError(f"Missing required source field: {field}")

        # Check that either format of API keys are provided
        has_legacy_keys = source.get("anon_key") and source.get("service_role_key")
        has_new_keys = source.get("publishable_key") and source.get("secret_key")
        if not has_legacy_keys and not has_new_keys:
            raise ConfigurationError(
                "Source must have either (anon_key + service_role_key) or (publishable_key + secret_key)"
            )

        # Validate target configuration
        target = config_data["target"]
        required_target_fields = ["project_ref", "db_url", "supabase_url"]
        for field in required_target_fields:
            if field not in target or not target[field]:
                raise ConfigurationError(f"Missing required target field: {field}")

        # Check that either format of API keys are provided
        has_legacy_keys = target.get("anon_key") and target.get("service_role_key")
        has_new_keys = target.get("publishable_key") and target.get("secret_key")
        if not has_legacy_keys and not has_new_keys:
            raise ConfigurationError(
                "Target must have either (anon_key + service_role_key) or (publishable_key + secret_key)"
            )

    def parse_source_config(self, config_data: Dict[str, Any]) -> SourceConfig:
        """Parse source configuration from config data."""
        source_data = config_data["source"]

        # Handle both new (sb_) and legacy (JWT) key formats
        anon_key = source_data.get("anon_key", "") or source_data.get(
            "publishable_key", ""
        )
        service_key = source_data.get("service_role_key", "") or source_data.get(
            "secret_key", ""
        )

        return SourceConfig(
            project_ref=source_data["project_ref"],
            db_url=source_data["db_url"],
            supabase_url=source_data["supabase_url"],
            anon_key=anon_key,
            service_role_key=service_key,
        )

    def parse_target_config(self, config_data: Dict[str, Any]) -> TargetConfig:
        """Parse target configuration from config data."""
        target_data = config_data["target"]

        # Handle both new (sb_) and legacy (JWT) key formats
        anon_key = target_data.get("anon_key", "") or target_data.get(
            "publishable_key", ""
        )
        service_key = target_data.get("service_role_key", "") or target_data.get(
            "secret_key", ""
        )

        return TargetConfig(
            project_ref=target_data["project_ref"],
            db_url=target_data["db_url"],
            supabase_url=target_data["supabase_url"],
            anon_key=anon_key,
            service_role_key=service_key,
        )

    def parse_migration_options(self, config_data: Dict[str, Any]) -> MigrationOptions:
        """Parse migration options from config data."""
        options_data = config_data.get("options", {})
        include_data = config_data.get("include", {})

        # Merge include section into options
        merged_options = {**options_data}

        # Map include fields to option fields
        if "schemas" in include_data:
            merged_options["schemas"] = include_data["schemas"]
        if "include_data" in include_data:
            merged_options["include_data"] = include_data["include_data"]
        if "include_policies" in include_data:
            merged_options["include_policies"] = include_data["include_policies"]
        if "include_storage" in include_data:
            merged_options["include_storage"] = include_data["include_storage"]

        return MigrationOptions(**merged_options)

    def save_config(self, config_data: Dict[str, Any], output_path: str) -> None:
        """Save configuration to YAML file."""
        try:
            with open(output_path, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def list_saved_configs(self) -> list[str]:
        """List saved configuration files in the config directory."""
        config_files = []
        if self.config_dir.exists():
            for file_path in self.config_dir.glob("*.yaml"):
                config_files.append(str(file_path))
            for file_path in self.config_dir.glob("*.yml"):
                config_files.append(str(file_path))
        return sorted(config_files)

    def get_config_template(self) -> Dict[str, Any]:
        """Get a basic configuration template as a dictionary."""
        return {
            "source": {
                "project_ref": "",
                "db_url": "",
                "supabase_url": "",
                "publishable_key": "",  # or anon_key for legacy format
                "secret_key": "",  # or service_role_key for legacy format
            },
            "target": {
                "project_ref": "",
                "db_url": "",
                "supabase_url": "",
                "publishable_key": "",  # or anon_key for legacy format
                "secret_key": "",  # or service_role_key for legacy format
            },
            "include": {
                "schemas": ["public"],
                "include_data": True,
                "include_policies": True,
                "include_storage": True,
            },
            "options": {
                "backup_target_first": True,
                "remap_conflicts": True,
                "skip_auth": False,
                "dry_run": False,
            },
        }

    def validate_connection_string(self, db_url: str) -> bool:
        """Validate a PostgreSQL connection string format."""
        if not db_url:
            return False

        # Basic validation - should start with postgresql:// or postgres://
        if not (db_url.startswith("postgresql://") or db_url.startswith("postgres://")):
            return False

        # Should contain essential components
        required_components = ["@", ":"]  # host separator and port separator
        return all(comp in db_url for comp in required_components)

    def validate_supabase_url(self, supabase_url: str) -> bool:
        """Validate a Supabase URL format."""
        if not supabase_url:
            return False

        return supabase_url.startswith("https://") and ".supabase.co" in supabase_url

    def validate_api_key(self, api_key: str) -> bool:
        """Basic validation for Supabase API keys."""
        if not api_key:
            return False

        # Supabase keys are typically JWT tokens starting with 'ey'
        return api_key.startswith("ey") and len(api_key) > 100
