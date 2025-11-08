#!/usr/bin/env python3
"""
Simple Supabase Export CLI Wrapper

A convenient command-line tool for exporting Supabase projects in various formats
for widget merging, backups, or migration purposes.

Usage:
    python export_supabase.py --help
    python export_supabase.py --profile myproject --format dump
    python export_supabase.py --profile widget1 --format json --output ./exports
    python export_supabase.py --list-profiles
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# Add the varchiver module to the path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "varchiver"))

try:
    from varchiver.supamerge.export import SupabaseExporter, ExportOptions
    from varchiver.supamerge.core import SourceConfig
    from varchiver.utils.env_manager import EnvManager
    from varchiver.utils.config import Config
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Solutions:")
    print("1. Run with: uv run python export_supabase.py --list-profiles")
    print("2. Or activate your virtual environment first")
    print("3. Make sure you're in the varchiver directory")
    print("4. Install dependencies: uv sync or pip install -e .")
    sys.exit(1)


class SimpleExporter:
    """Simple wrapper for Supabase exports."""

    def __init__(self):
        self.env_manager = EnvManager()
        self.config = Config()

    def list_profiles(self):
        """List available Supabase profiles."""
        # Get environment-based profiles
        env_profiles = self.env_manager.get_all_supabase_profiles()

        # Get GUI-configured profiles
        gui_profiles = self.config.get_supabase_connections()

        print("🔗 Available Supabase Profiles:")

        total_profiles = 0

        # Show environment profiles
        if env_profiles:
            print("   📁 Environment Profiles:")
            for profile_name in env_profiles:
                credentials = self.env_manager.get_env_vars_for_profile(profile_name)
                url = credentials.get("url", "No URL")
                print(f"     • {profile_name}: {url}")
                total_profiles += 1

        # Show GUI profiles
        if gui_profiles:
            print("   🖥️  GUI Profiles:")
            for profile in gui_profiles:
                profile_name = profile.get("name", "Unnamed")
                url = profile.get("url", "No URL")
                print(f"     • {profile_name}: {url}")
                total_profiles += 1

        if total_profiles == 0:
            print("   No profiles found.")
            print("\n💡 To add profiles:")
            print("   1. Use Varchiver's connection manager (recommended)")
            print("   2. Or set environment variables like:")
            print("      SUPABASE_MYPROJECT_URL=https://abc123.supabase.co")
            print("      SUPABASE_MYPROJECT_ANON_KEY=eyJ...")
            print("      SUPABASE_MYPROJECT_SERVICE_KEY=eyJ...")

    def _build_database_url(self, project_ref: str, service_key: str) -> str:
        """Build Supabase database URL with multiple pooler options."""
        # Try different common pooler configurations
        pooler_options = [
            f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-west-1.pooler.supabase.com:6543/postgres",
            f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-east-1.pooler.supabase.com:6543/postgres",
            f"postgresql://postgres.{project_ref}:{service_key}@db.{project_ref}.supabase.co:5432/postgres",
            f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-west-1.pooler.supabase.com:5432/postgres",
        ]

        # Return the first option for now, but we could add connection testing here
        return pooler_options[0]

    def _test_connection(self, db_url: str) -> bool:
        """Test if a database connection works."""
        try:
            import psycopg2

            conn = psycopg2.connect(db_url, connect_timeout=5)
            conn.close()
            return True
        except Exception:
            return False

    def get_source_config(self, profile_name: str) -> SourceConfig:
        """Get source configuration for a profile."""
        # Try environment variables first
        env_credentials = self.env_manager.get_env_vars_for_profile(profile_name)

        if (
            env_credentials
            and env_credentials.get("url")
            and env_credentials.get("service_key")
        ):
            # Use environment profile
            url = env_credentials["url"]
            service_key = env_credentials["service_key"]

            # Extract project ref from URL
            if "supabase.co" in url:
                project_ref = url.split("//")[1].split(".")[0]
            else:
                project_ref = env_credentials.get("project_ref", profile_name.lower())

            # Build connection string
            db_url = self._build_database_url(project_ref, service_key)

            return SourceConfig(
                project_ref=project_ref,
                db_url=db_url,
                supabase_url=url,
                anon_key=env_credentials["anon_key"],
                service_role_key=service_key,
            )

        # Try GUI profile
        gui_profile = self.config.get_supabase_connection_by_name(profile_name)
        if gui_profile:
            url = gui_profile.get("url")
            anon_key = gui_profile.get("anon_key") or gui_profile.get("publishable_key")
            service_key = gui_profile.get("service_role_key") or gui_profile.get(
                "secret_key"
            )

            if url and service_key:
                # Extract project ref from URL
                if "supabase.co" in url:
                    project_ref = url.split("//")[1].split(".")[0]
                else:
                    project_ref = profile_name.lower().replace(" ", "_")

                # Build connection string
                db_url = self._build_database_url(project_ref, service_key)

                return SourceConfig(
                    project_ref=project_ref,
                    db_url=db_url,
                    supabase_url=url,
                    anon_key=anon_key,
                    service_role_key=service_key,
                )

        # Profile not found
        env_profiles = self.env_manager.get_all_supabase_profiles()
        gui_profiles = [
            p.get("name", "Unnamed") for p in self.config.get_supabase_connections()
        ]
        all_available = env_profiles + gui_profiles

        raise ValueError(
            f"Profile '{profile_name}' not found. Available: {all_available}"
        )

    async def export_project(
        self,
        profile_name: str,
        output_format: str = "dump",
        output_dir: str = None,
        include_data: bool = True,
        schemas: list = None,
        tables: list = None,
    ) -> bool:
        """Export a Supabase project."""

        try:
            print(f"🚀 Starting export of '{profile_name}' as {output_format.upper()}")

            # Get configuration
            source_config = self.get_source_config(profile_name)

            # Set up output directory
            if not output_dir:
                output_dir = f"./exports/{profile_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Create export options
            export_options = ExportOptions(
                output_format=output_format,
                output_dir=str(output_path),
                include_schema=True,
                include_data=include_data,
                include_policies=True,
                include_storage=False,
                schemas=schemas or ["public"],
                tables=tables or [],
            )

            # Perform export
            exporter = SupabaseExporter(source_config)
            result = await exporter.export_project_state(export_options)

            if result.success:
                print(f"✅ Export completed successfully!")
                print(f"⏱️  Time taken: {result.execution_time:.2f} seconds")
                print(f"📁 Output directory: {output_path}")
                print(f"📄 Files created:")

                for file_path in result.export_files:
                    file_name = Path(file_path).name
                    file_size = os.path.getsize(file_path) / 1024  # KB
                    print(f"   • {file_name} ({file_size:.1f} KB)")

                return True
            else:
                print(f"❌ Export failed: {result.message}")
                return False

        except Exception as e:
            print(f"❌ Export error: {str(e)}")
            return False


def create_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Simple Supabase Export Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available profiles
  python export_supabase.py --list-profiles

  # Export as PostgreSQL dump (default)
  python export_supabase.py --profile myproject

  # Export as JSON
  python export_supabase.py --profile widget1 --format json

  # Export specific schemas only
  python export_supabase.py --profile myproject --schemas public,auth

  # Export schema only (no data)
  python export_supabase.py --profile myproject --no-data

  # Export to specific directory
  python export_supabase.py --profile myproject --output ./my_exports
        """,
    )

    # Profile selection
    parser.add_argument("--profile", "-p", help="Supabase profile name to export")

    parser.add_argument(
        "--list-profiles",
        "-l",
        action="store_true",
        help="List available Supabase profiles",
    )

    # Export options
    parser.add_argument(
        "--format",
        "-f",
        choices=["dump", "sql", "json", "yaml"],
        default="dump",
        help="Export format (default: dump)",
    )

    parser.add_argument(
        "--output", "-o", help="Output directory (default: ./exports/PROFILE_TIMESTAMP)"
    )

    parser.add_argument(
        "--no-data", action="store_true", help="Export schema only, exclude data"
    )

    parser.add_argument(
        "--schemas", help="Comma-separated list of schemas (default: public)"
    )

    parser.add_argument(
        "--tables", help="Comma-separated list of specific tables to export"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    return parser


async def main():
    """Main function."""
    parser = create_parser()
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return 1

    exporter = SimpleExporter()

    try:
        # List profiles
        if args.list_profiles:
            exporter.list_profiles()
            return 0

        # Validate required arguments
        if not args.profile:
            print("❌ Error: --profile is required for export operations")
            parser.print_help()
            return 1

        # Parse optional lists
        schemas = None
        if args.schemas:
            schemas = [s.strip() for s in args.schemas.split(",") if s.strip()]

        tables = None
        if args.tables:
            tables = [t.strip() for t in args.tables.split(",") if t.strip()]

        # Perform export
        success = await exporter.export_project(
            profile_name=args.profile,
            output_format=args.format,
            output_dir=args.output,
            include_data=not args.no_data,
            schemas=schemas,
            tables=tables,
        )

        if success:
            print("\n🎉 Export completed successfully!")
            print("\n💡 What you can do with these files:")

            if args.format == "dump":
                print("   • Restore with: pg_restore -d database file.dump")
                print("   • Use with Supamerge for migration")
            elif args.format == "sql":
                print("   • Restore with: psql -d database < file.sql")
                print("   • Edit manually if needed")
            elif args.format == "json":
                print("   • Use for data analysis")
                print("   • Import with custom scripts")
                print("   • Compare with other exports")
            elif args.format == "yaml":
                print("   • Human-readable configuration format")
                print("   • Edit and customize as needed")

            print("   • Use for widget project merging")
            print("   • Keep as backup before migrations")

            return 0
        else:
            return 1

    except KeyboardInterrupt:
        print("\n❌ Export cancelled by user")
        return 1
    except Exception as e:
        if args.verbose:
            import traceback

            traceback.print_exc()
        else:
            print(f"❌ Unexpected error: {str(e)}")
            print("💡 Use --verbose for detailed error information")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Interrupted")
        sys.exit(1)
