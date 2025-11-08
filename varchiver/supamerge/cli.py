"""
Command-line interface for Supamerge.
Provides standalone CLI access to Supabase project migration functionality.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from .core import Supamerge, SourceConfig, TargetConfig, MigrationOptions
from .config import SupamergeConfig
from .export import SupabaseExporter, ExportOptions


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="supamerge",
        description="Migrate or mirror schema/data/policies between Supabase projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a configuration template
  supamerge template --output config.yaml

  # Run migration from config file
  supamerge migrate --config config.yaml

  # Dry run migration
  supamerge migrate --config config.yaml --dry-run

  # Quick migration with environment variables
  supamerge migrate --from-env SOURCE --to-env TARGET --include-data --backup

Environment Variables:
  For --from-env and --to-env options, set these variables:

  {PREFIX}_PROJECT_REF      - Project reference ID
  {PREFIX}_DB_URL          - PostgreSQL connection URL
  {PREFIX}_SUPABASE_URL    - Supabase project URL
  {PREFIX}_ANON_KEY        - Supabase anonymous key
  {PREFIX}_SERVICE_KEY     - Supabase service role key

  Example: SOURCE_DB_URL, TARGET_PROJECT_REF, etc.
        """,
    )
    parser.add_argument("--version", action="version", version="Supamerge 1.0.0")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Template command
    template_parser = subparsers.add_parser(
        "template", help="Create configuration template"
    )
    template_parser.add_argument(
        "--output",
        "-o",
        default="supamerge.yaml",
        help="Output file path (default: supamerge.yaml)",
    )

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Run migration")

    # Config file option
    migrate_parser.add_argument(
        "--config",
        "-c",
        help="Path to configuration YAML file",
    )

    # Environment-based quick setup
    migrate_parser.add_argument(
        "--from-env",
        help="Source environment variable prefix (e.g., SOURCE)",
    )
    migrate_parser.add_argument(
        "--to-env",
        help="Target environment variable prefix (e.g., TARGET)",
    )

    # Migration options
    migrate_parser.add_argument(
        "--include-data",
        action="store_true",
        help="Include table data in migration",
    )
    migrate_parser.add_argument(
        "--include-storage",
        action="store_true",
        help="Include storage buckets in migration",
    )
    migrate_parser.add_argument(
        "--include-policies",
        action="store_true",
        help="Include RLS policies in migration",
    )
    migrate_parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup target database before migration",
    )
    migrate_parser.add_argument(
        "--schemas",
        default="public",
        help="Comma-separated list of schemas to migrate (default: public)",
    )
    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without making changes",
    )
    migrate_parser.add_argument(
        "--no-remap",
        action="store_true",
        help="Don't remap conflicting table names",
    )

    # Output options
    migrate_parser.add_argument(
        "--manifest",
        help="Save migration manifest to specified file",
    )
    migrate_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    # Export command
    export_parser = subparsers.add_parser(
        "export", help="Export Supabase project state"
    )

    # Export source config
    export_parser.add_argument(
        "--config",
        "-c",
        help="Path to configuration YAML file",
    )
    export_parser.add_argument(
        "--from-env",
        help="Source environment variable prefix (e.g., SOURCE)",
    )

    # Export options
    export_parser.add_argument(
        "--format",
        "-f",
        choices=["dump", "sql", "json", "yaml"],
        default="dump",
        help="Export format (default: dump)",
    )
    export_parser.add_argument(
        "--output",
        "-o",
        help="Output directory (default: current directory)",
    )
    export_parser.add_argument(
        "--include-data",
        action="store_true",
        default=True,
        help="Include table data in export (default: true)",
    )
    export_parser.add_argument(
        "--no-data",
        action="store_true",
        help="Exclude table data from export",
    )
    export_parser.add_argument(
        "--include-policies",
        action="store_true",
        default=True,
        help="Include RLS policies in export (default: true)",
    )
    export_parser.add_argument(
        "--include-storage",
        action="store_true",
        help="Include storage buckets in export",
    )
    export_parser.add_argument(
        "--schemas",
        default="public",
        help="Comma-separated list of schemas to export (default: public)",
    )
    export_parser.add_argument(
        "--tables",
        help="Comma-separated list of specific tables to export",
    )
    export_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration")
    validate_parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to configuration YAML file",
    )

    return parser


def load_env_config(prefix: str) -> dict:
    """Load configuration from environment variables with given prefix."""
    config = {}

    required_vars = [
        "PROJECT_REF",
        "DB_URL",
        "SUPABASE_URL",
        "ANON_KEY",
        "SERVICE_KEY",
    ]

    for var in required_vars:
        env_var = f"{prefix}_{var}"
        value = os.getenv(env_var)
        if not value:
            raise ValueError(f"Required environment variable not set: {env_var}")

        # Map to config keys
        key_mapping = {
            "PROJECT_REF": "project_ref",
            "DB_URL": "db_url",
            "SUPABASE_URL": "supabase_url",
            "ANON_KEY": "anon_key",
            "SERVICE_KEY": "service_role_key",
        }

        config[key_mapping[var]] = value

    return config


async def run_template_command(args) -> int:
    """Execute the template command."""
    try:
        config_manager = SupamergeConfig()
        config_manager.create_template_config(args.output)
        print(f"✅ Configuration template created: {args.output}")
        print(f"📝 Edit the file with your project details, then run:")
        print(f"   supamerge migrate --config {args.output}")
        return 0
    except Exception as e:
        print(f"❌ Error creating template: {e}")
        return 1


async def run_validate_command(args) -> int:
    """Execute the validate command."""
    try:
        supamerge = Supamerge()
        supamerge.load_config(args.config)
        supamerge.validate_configuration()
        print("✅ Configuration is valid!")
        return 0
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return 1


async def run_export_command(args) -> int:
    """Execute the export command."""
    try:
        # Load source configuration
        if args.config:
            config_manager = SupamergeConfig()
            config_manager.load_config(args.config)
            source_config = config_manager.get_source_config()
        elif args.from_env:
            env_config = load_env_config(args.from_env)
            source_config = SourceConfig(**env_config)
        else:
            raise ValueError("Must specify either --config or --from-env")

        # Parse schemas and tables
        schemas = [s.strip() for s in args.schemas.split(",") if s.strip()]
        tables = []
        if args.tables:
            tables = [t.strip() for t in args.tables.split(",") if t.strip()]

        # Create export options
        include_data = args.include_data and not args.no_data
        export_options = ExportOptions(
            output_format=args.format,
            output_dir=args.output or os.getcwd(),
            include_data=include_data,
            include_policies=args.include_policies,
            include_storage=args.include_storage,
            schemas=schemas,
            tables=tables,
        )

        # Create exporter and run export
        exporter = SupabaseExporter(source_config)
        result = await exporter.export_project_state(export_options)

        if result.success:
            print(f"✅ {result.message}")
            print(f"⏱️  Execution time: {result.execution_time:.2f} seconds")
            print(f"📁 Exported files:")
            for file_path in result.export_files:
                print(f"   - {file_path}")
        else:
            print(f"❌ Export failed: {result.message}")
            return 1

        return 0

    except Exception as e:
        print(f"❌ Export error: {e}")
        return 1


async def run_migrate_command(args) -> int:
    """Execute the migrate command."""
    try:
        supamerge = Supamerge()

        # Load configuration
        if args.config:
            supamerge.load_config(args.config)
        elif args.from_env and args.to_env:
            # Build config from environment variables
            source_config = SourceConfig(**load_env_config(args.from_env))
            target_config = TargetConfig(**load_env_config(args.to_env))
            supamerge.set_source(source_config)
            supamerge.set_target(target_config)
        else:
            print(
                "❌ Error: Must specify either --config or both --from-env and --to-env"
            )
            return 1

        # Set migration options from CLI args
        schemas = [s.strip() for s in args.schemas.split(",")]
        options = MigrationOptions(
            backup_target_first=args.backup,
            include_data=args.include_data,
            include_storage=args.include_storage,
            include_policies=args.include_policies,
            remap_conflicts=not args.no_remap,
            schemas=schemas,
            dry_run=args.dry_run,
        )
        supamerge.set_options(options)

        # Validate configuration
        supamerge.validate_configuration()

        if args.dry_run:
            print("🔍 Running in dry-run mode - no changes will be made")
        else:
            print("⚠️  This will modify the target database!")
            response = input("Do you want to continue? (y/N): ").strip().lower()
            if response not in ["y", "yes"]:
                print("❌ Migration cancelled by user")
                return 1

        print("🚀 Starting migration...")

        # Run migration
        result = await supamerge.migrate()

        if result.success:
            print("\n✅ Migration completed successfully!")
            print(f"⏱️  Execution time: {result.execution_time:.2f} seconds")

            if result.backup_files:
                print(f"💾 Backup files created: {len(result.backup_files)}")
                for backup in result.backup_files:
                    print(f"   - {backup}")

            if result.conflicts:
                print(f"⚠️  Conflicts detected: {len(result.conflicts)}")
                for conflict in result.conflicts:
                    print(f"   - {conflict}")

            if result.skipped_items:
                print(f"⏭️  Items skipped: {len(result.skipped_items)}")
                for skipped in result.skipped_items:
                    print(f"   - {skipped}")

            if result.log_file:
                print(f"📋 Full log available at: {result.log_file}")

        else:
            print(f"\n❌ Migration failed: {result.message}")
            if result.log_file:
                print(f"📋 Check log file for details: {result.log_file}")
            return 1

        # Save manifest if requested
        if args.manifest:
            supamerge.generate_manifest(args.manifest)
            print(f"📄 Migration manifest saved: {args.manifest}")

        return 0

    except Exception as e:
        print(f"❌ Migration error: {e}")
        return 1


async def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Set up logging level
    if hasattr(args, "verbose") and args.verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    try:
        if args.command == "template":
            return await run_template_command(args)
        elif args.command == "validate":
            return await run_validate_command(args)
        elif args.command == "migrate":
            return await run_migrate_command(args)
        elif args.command == "export":
            return await run_export_command(args)
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


def cli_entry_point():
    """Entry point for console script."""
    return asyncio.run(main())


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
