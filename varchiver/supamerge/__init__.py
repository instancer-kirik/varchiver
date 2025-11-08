"""
Supamerge - Supabase Project Migration Tool

A comprehensive tool for migrating schema, data, and policies between Supabase projects.
Safely merge or mirror databases with backup and conflict resolution features.
"""

from .core import (
    Supamerge,
    SourceConfig,
    TargetConfig,
    MigrationOptions,
    MigrationResult,
    SupamergeError,
    ConfigurationError,
    MigrationError,
)

from .config import SupamergeConfig

__version__ = "0.1.0"
__author__ = "instancer-kirik"
__email__ = "kirik@instance.select"

__all__ = [
    "Supamerge",
    "SourceConfig",
    "TargetConfig",
    "MigrationOptions",
    "MigrationResult",
    "SupamergeError",
    "ConfigurationError",
    "MigrationError",
    "SupamergeConfig",
]
