#!/usr/bin/env python3
"""
Improved Supabase Export Tool - Hybrid Approach

This tool combines multiple strategies to export Supabase projects:
1. Auto-detect correct database connection format
2. Enhanced REST API-based export as fallback
3. Manual connection string override options
4. Better error handling and diagnostics

Usage:
    uv run python supabase_export_improved.py --profile development
    uv run python supabase_export_improved.py --profile widget1 --format json --tables users,posts
    uv run python supabase_export_improved.py --url https://abc.supabase.co --service-key eyJ... --format dump
"""

import asyncio
import argparse
import json
import yaml
import os
import sys
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging

# Add the varchiver module to the path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    import psycopg2
    from supabase import create_client
    from varchiver.utils.env_manager import EnvManager
    from varchiver.utils.config import Config
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run with: uv run python supabase_export_improved.py")
    sys.exit(1)


class ImprovedSupabaseExporter:
    """Enhanced Supabase exporter with multiple connection strategies."""

    def __init__(self, verbose: bool = False):
        self.env_manager = EnvManager()
        self.config = Config()
        self.verbose = verbose
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up logging."""
        logger = logging.getLogger(f"improved_exporter_{id(self)}")
        level = logging.DEBUG if self.verbose else logging.INFO
        logger.setLevel(level)

        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def get_profile_credentials(self, profile_name: str) -> Optional[Dict[str, str]]:
        """Get credentials for a profile from environment or GUI config."""
        # Try environment variables first
        env_credentials = self.env_manager.get_env_vars_for_profile(profile_name)
        if (
            env_credentials
            and env_credentials.get("url")
            and env_credentials.get("service_key")
        ):
            return env_credentials

        # Try GUI profile
        gui_profile = self.config.get_supabase_connection_by_name(profile_name)
        if gui_profile:
            url = gui_profile.get("url")
            anon_key = gui_profile.get("anon_key") or gui_profile.get("publishable_key")
            service_key = gui_profile.get("service_role_key") or gui_profile.get(
                "secret_key"
            )

            if url and service_key:
                return {
                    "url": url,
                    "anon_key": anon_key,
                    "service_key": service_key,
                }

        return None

    def extract_project_ref(self, url: str) -> str:
        """Extract project reference from Supabase URL."""
        if "supabase.co" in url:
            return url.split("//")[1].split(".")[0]
        return "unknown"

    def generate_connection_strings(
        self, project_ref: str, service_key: str
    ) -> List[Dict[str, str]]:
        """Generate various database connection string formats to test."""
        # Common regions and formats
        regions = ["us-west-1", "us-east-1", "eu-west-1", "ap-southeast-1"]
        formats = []

        for region in regions:
            # Session pooler (port 6543)
            formats.append(
                {
                    "name": f"Session Pooler - {region}",
                    "url": f"postgresql://postgres.{project_ref}:{service_key}@aws-0-{region}.pooler.supabase.com:6543/postgres",
                    "type": "session_pooler",
                    "region": region,
                }
            )

            # Transaction pooler (port 5432)
            formats.append(
                {
                    "name": f"Transaction Pooler - {region}",
                    "url": f"postgresql://postgres.{project_ref}:{service_key}@aws-0-{region}.pooler.supabase.com:5432/postgres",
                    "type": "transaction_pooler",
                    "region": region,
                }
            )

        # Direct connection
        formats.append(
            {
                "name": "Direct Connection",
                "url": f"postgresql://postgres.{project_ref}:{service_key}@db.{project_ref}.supabase.co:5432/postgres",
                "type": "direct",
                "region": "direct",
            }
        )

        return formats

    def test_connection(
        self, connection_string: str, timeout: int = 5
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Test a database connection and return success status."""
        try:
            conn = psycopg2.connect(connection_string, connect_timeout=timeout)

            # Get basic info
            cur = conn.cursor()
            cur.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
            )
            table_count = cur.fetchone()[0]

            info = {"table_count": table_count}

            cur.close()
            conn.close()

            return True, None, info

        except Exception as e:
            return False, str(e), None

    def find_working_connection(
        self, project_ref: str, service_key: str
    ) -> Optional[str]:
        """Try different connection formats and return the first working one."""
        self.logger.info("🔍 Testing database connection formats...")

        connection_formats = self.generate_connection_strings(project_ref, service_key)

        for conn_format in connection_formats:
            self.logger.debug(f"Testing {conn_format['name']}")

            success, error, info = self.test_connection(conn_format["url"], timeout=3)

            if success:
                self.logger.info(f"✅ Found working connection: {conn_format['name']}")
                self.logger.info(f"   Tables found: {info['table_count']}")
                return conn_format["url"]
            else:
                self.logger.debug(f"❌ {conn_format['name']}: {error}")

        self.logger.warning("No working database connection found")
        return None

    async def export_via_database(
        self,
        db_url: str,
        project_ref: str,
        output_dir: Path,
        format_type: str = "dump",
        include_data: bool = True,
        schemas: List[str] = None,
        tables: List[str] = None,
    ) -> List[str]:
        """Export using direct database connection."""
        if schemas is None:
            schemas = ["public"]

        export_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.logger.info(
            f"📊 Exporting via database connection as {format_type.upper()}"
        )

        if format_type in ["dump", "sql"]:
            # Use pg_dump
            output_file = output_dir / f"{project_ref}_export_{timestamp}.{format_type}"

            cmd = ["pg_dump", db_url, "--no-owner", "--no-privileges"]

            if format_type == "dump":
                cmd.append("--format=custom")
            else:
                cmd.append("--format=plain")

            # Add schema filters
            for schema in schemas:
                if schema != "public":  # public is default
                    cmd.extend(["--schema", schema])

            # Add table filters
            if tables:
                for table in tables:
                    cmd.extend(["--table", table])

            if not include_data:
                cmd.append("--schema-only")

            cmd.extend(["-f", str(output_file)])

            self.logger.debug(f"Running: {' '.join(cmd[:3])} ... [credentials hidden]")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"✅ Database export completed: {output_file.name}")
                export_files.append(str(output_file))
            else:
                self.logger.error(f"pg_dump failed: {result.stderr}")
                raise Exception(f"pg_dump failed: {result.stderr}")

        elif format_type == "json":
            # Extract via SQL queries
            schema_file = output_dir / f"{project_ref}_schema_{timestamp}.json"
            data_file = output_dir / f"{project_ref}_data_{timestamp}.json"

            schema_data = await self._extract_schema_via_db(db_url, schemas)
            data_data = (
                await self._extract_data_via_db(db_url, schemas, tables)
                if include_data
                else {}
            )

            with open(schema_file, "w") as f:
                json.dump(schema_data, f, indent=2, default=str)
            export_files.append(str(schema_file))

            with open(data_file, "w") as f:
                json.dump(data_data, f, indent=2, default=str)
            export_files.append(str(data_file))

            self.logger.info(f"✅ JSON export completed: {len(export_files)} files")

        return export_files

    async def _extract_schema_via_db(
        self, db_url: str, schemas: List[str]
    ) -> Dict[str, Any]:
        """Extract schema information via database connection."""
        schema_info = {}

        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        for schema in schemas:
            # Get tables
            cur.execute(
                """
                SELECT table_name, table_type
                FROM information_schema.tables
                WHERE table_schema = %s
            """,
                (schema,),
            )

            tables = {}
            for table_name, table_type in cur.fetchall():
                # Get columns
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """,
                    (schema, table_name),
                )

                columns = []
                for col_name, data_type, is_nullable, col_default in cur.fetchall():
                    columns.append(
                        {
                            "name": col_name,
                            "type": data_type,
                            "nullable": is_nullable == "YES",
                            "default": col_default,
                        }
                    )

                tables[table_name] = {
                    "type": table_type,
                    "columns": columns,
                }

            schema_info[schema] = {"tables": tables}

        cur.close()
        conn.close()

        return schema_info

    async def _extract_data_via_db(
        self, db_url: str, schemas: List[str], tables: List[str] = None
    ) -> Dict[str, Any]:
        """Extract data via database connection."""
        data_info = {}

        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        for schema in schemas:
            if tables:
                table_list = tables
            else:
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s AND table_type = 'BASE TABLE'
                """,
                    (schema,),
                )
                table_list = [row[0] for row in cur.fetchall()]

            schema_data = {}
            for table_name in table_list:
                try:
                    cur.execute(f'SELECT * FROM "{schema}"."{table_name}"')

                    # Get column names
                    columns = [desc[0] for desc in cur.description]

                    # Get data
                    rows = cur.fetchall()
                    table_data = []

                    for row in rows:
                        row_dict = {}
                        for i, value in enumerate(row):
                            row_dict[columns[i]] = value
                        table_data.append(row_dict)

                    schema_data[table_name] = table_data
                    self.logger.info(
                        f"📊 Extracted {len(table_data)} rows from {table_name}"
                    )

                except Exception as e:
                    self.logger.warning(
                        f"Could not extract data from {table_name}: {e}"
                    )

            data_info[schema] = schema_data

        cur.close()
        conn.close()

        return data_info

    async def export_via_rest_api(
        self,
        url: str,
        service_key: str,
        project_ref: str,
        output_dir: Path,
        format_type: str = "json",
        include_data: bool = True,
        tables: List[str] = None,
    ) -> List[str]:
        """Export using Supabase REST API as fallback."""
        self.logger.info("🌐 Exporting via REST API (fallback method)")

        export_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            # Create Supabase client
            supabase = create_client(url, service_key)

            # Get table list if not specified
            if not tables:
                tables = await self._discover_tables_via_api(supabase)

            if format_type == "json":
                # Schema extraction (limited)
                schema_file = output_dir / f"{project_ref}_schema_api_{timestamp}.json"
                schema_data = await self._extract_schema_via_api(supabase, tables)

                with open(schema_file, "w") as f:
                    json.dump(schema_data, f, indent=2, default=str)
                export_files.append(str(schema_file))

                # Data extraction
                if include_data:
                    data_file = output_dir / f"{project_ref}_data_api_{timestamp}.json"
                    data_data = await self._extract_data_via_api(supabase, tables)

                    with open(data_file, "w") as f:
                        json.dump(data_data, f, indent=2, default=str)
                    export_files.append(str(data_file))

                self.logger.info(
                    f"✅ REST API export completed: {len(export_files)} files"
                )

            else:
                self.logger.warning(
                    f"Format {format_type} not supported via REST API, using JSON"
                )
                return await self.export_via_rest_api(
                    url,
                    service_key,
                    project_ref,
                    output_dir,
                    "json",
                    include_data,
                    tables,
                )

        except Exception as e:
            self.logger.error(f"REST API export failed: {e}")
            raise

        return export_files

    async def _discover_tables_via_api(self, supabase) -> List[str]:
        """Discover ALL tables via OpenAPI schema introspection."""
        existing_tables = []

        try:
            # Use OpenAPI schema to discover all tables
            import requests
            from urllib.parse import urlparse

            # Extract base URL from supabase client
            base_url = supabase.supabase_url.rstrip("/")
            rest_url = f"{base_url}/rest/v1/"

            headers = {
                "apikey": supabase.supabase_key,
                "Authorization": f"Bearer {supabase.supabase_key}",
                "Accept": "application/openapi+json",
            }

            self.logger.info("🔍 Discovering tables via OpenAPI schema...")
            response = requests.get(rest_url, headers=headers, timeout=15)

            if response.status_code == 200:
                openapi_data = response.json()
                paths = openapi_data.get("paths", {})

                self.logger.info(f"📡 Found {len(paths)} API endpoints")

                for path, methods in paths.items():
                    # PostgREST creates paths like "/<table_name>"
                    if path.startswith("/") and len(path.split("/")) == 2:
                        table_name = path[1:]  # Remove leading slash
                        if table_name and not table_name.startswith("rpc"):
                            existing_tables.append(table_name)
                            self.logger.debug(f"Found table: {table_name}")

            else:
                self.logger.warning(f"OpenAPI request failed: {response.status_code}")
                # Fallback to common table discovery
                self.logger.info("Falling back to common table discovery...")
                common_tables = ["users", "profiles", "posts", "comments", "categories"]
                for table_name in common_tables:
                    try:
                        result = (
                            supabase.table(table_name).select("*").limit(1).execute()
                        )
                        existing_tables.append(table_name)
                    except:
                        pass

        except Exception as e:
            self.logger.warning(f"OpenAPI discovery failed: {e}")
            # Fallback to testing common table names
            self.logger.info("Falling back to common table discovery...")
            common_tables = [
                "users",
                "profiles",
                "posts",
                "comments",
                "categories",
                "settings",
            ]
            for table_name in common_tables:
                try:
                    result = supabase.table(table_name).select("*").limit(1).execute()
                    existing_tables.append(table_name)
                except:
                    pass

        self.logger.info(f"Discovered {len(existing_tables)} tables via API")
        return existing_tables

    async def _extract_schema_via_api(
        self, supabase, tables: List[str]
    ) -> Dict[str, Any]:
        """Extract schema info via REST API (limited)."""
        schema_info = {"public": {"tables": {}}}

        for table_name in tables:
            try:
                # Get one row to infer column structure
                result = supabase.table(table_name).select("*").limit(1).execute()

                if result.data:
                    columns = []
                    for col_name, value in result.data[0].items():
                        col_type = type(value).__name__
                        columns.append(
                            {
                                "name": col_name,
                                "type": col_type,
                                "inferred_from_api": True,
                            }
                        )

                    schema_info["public"]["tables"][table_name] = {
                        "type": "BASE TABLE",
                        "columns": columns,
                        "extraction_method": "REST API (limited)",
                    }

            except Exception as e:
                self.logger.debug(f"Could not get schema for {table_name}: {e}")

        return schema_info

    async def _extract_data_via_api(
        self, supabase, tables: List[str]
    ) -> Dict[str, Any]:
        """Extract data via REST API."""
        data_info = {"public": {}}

        for table_name in tables:
            try:
                result = supabase.table(table_name).select("*").execute()
                data_info["public"][table_name] = result.data
                self.logger.info(
                    f"📊 Extracted {len(result.data)} rows from {table_name} via API"
                )

            except Exception as e:
                self.logger.warning(f"Could not extract data from {table_name}: {e}")

        return data_info

    async def export_project(
        self,
        profile_name: str = None,
        manual_url: str = None,
        manual_service_key: str = None,
        output_format: str = "json",
        output_dir: str = None,
        include_data: bool = True,
        schemas: List[str] = None,
        tables: List[str] = None,
    ) -> Dict[str, Any]:
        """Main export function with hybrid approach."""

        # Get credentials
        if profile_name:
            credentials = self.get_profile_credentials(profile_name)
            if not credentials:
                raise ValueError(
                    f"Profile '{profile_name}' not found or missing credentials"
                )

            url = credentials["url"]
            service_key = credentials["service_key"]
            source_name = profile_name

        elif manual_url and manual_service_key:
            url = manual_url
            service_key = manual_service_key
            source_name = self.extract_project_ref(url)

        else:
            raise ValueError(
                "Must specify either --profile or both --url and --service-key"
            )

        project_ref = self.extract_project_ref(url)

        # Setup output directory
        if not output_dir:
            output_dir = (
                f"./exports/{source_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            f"🚀 Starting export of '{source_name}' as {output_format.upper()}"
        )
        self.logger.info(f"📁 Output directory: {output_path}")
        self.logger.info(f"🎯 Project: {url}")

        export_files = []
        export_method = "none"

        try:
            # Strategy 1: Try database connection
            db_url = self.find_working_connection(project_ref, service_key)

            if db_url:
                export_method = "database"
                export_files = await self.export_via_database(
                    db_url,
                    project_ref,
                    output_path,
                    output_format,
                    include_data,
                    schemas,
                    tables,
                )

            else:
                # Strategy 2: Fallback to REST API
                self.logger.info("🔄 Falling back to REST API export")
                export_method = "rest_api"
                export_files = await self.export_via_rest_api(
                    url,
                    service_key,
                    project_ref,
                    output_path,
                    output_format,
                    include_data,
                    tables,
                )

            # Create manifest
            manifest = {
                "export_info": {
                    "project_ref": project_ref,
                    "project_url": url,
                    "export_method": export_method,
                    "timestamp": datetime.now().isoformat(),
                    "format": output_format,
                },
                "options": {
                    "include_data": include_data,
                    "schemas": schemas or ["public"],
                    "tables": tables or [],
                },
                "files": export_files,
                "success": True,
            }

            manifest_file = output_path / f"{project_ref}_manifest.json"
            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)
            export_files.append(str(manifest_file))

            # Success summary
            total_size = sum(os.path.getsize(f) for f in export_files) / 1024  # KB

            self.logger.info("✅ Export completed successfully!")
            self.logger.info(f"📊 Method: {export_method}")
            self.logger.info(f"📁 Files: {len(export_files)}")
            self.logger.info(f"💾 Total size: {total_size:.1f} KB")

            for file_path in export_files:
                file_name = Path(file_path).name
                file_size = os.path.getsize(file_path) / 1024
                self.logger.info(f"   • {file_name} ({file_size:.1f} KB)")

            return {
                "success": True,
                "method": export_method,
                "files": export_files,
                "output_dir": str(output_path),
                "manifest": manifest,
            }

        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            self.logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "method": export_method,
                "output_dir": str(output_path),
            }


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Improved Supabase Export Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export configured profile
  uv run python supabase_export_improved.py --profile development

  # Export as PostgreSQL dump
  uv run python supabase_export_improved.py --profile widget1 --format dump

  # Export specific tables only
  uv run python supabase_export_improved.py --profile myapp --tables users,posts,comments

  # Export with manual credentials
  uv run python supabase_export_improved.py \\
    --url https://abc123.supabase.co \\
    --service-key eyJhbGciOiJIUzI1NiIs... \\
    --format json

  # Schema-only export
  uv run python supabase_export_improved.py --profile development --no-data

  # Verbose diagnostics
  uv run python supabase_export_improved.py --profile development --verbose
        """,
    )

    parser.add_argument("--profile", "-p", help="Profile name to export")
    parser.add_argument("--url", help="Supabase project URL (for manual export)")
    parser.add_argument(
        "--service-key", help="Supabase service role key (for manual export)"
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["dump", "sql", "json", "yaml"],
        default="json",
        help="Export format (default: json)",
    )
    parser.add_argument("--output", "-o", help="Output directory")

    parser.add_argument(
        "--no-data", action="store_true", help="Export schema only, exclude data"
    )
    parser.add_argument(
        "--schemas", help="Comma-separated list of schemas (default: public)"
    )
    parser.add_argument("--tables", help="Comma-separated list of specific tables")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--list-profiles", action="store_true", help="List available profiles"
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return 1

    exporter = ImprovedSupabaseExporter(verbose=args.verbose)

    try:
        if args.list_profiles:
            # List available profiles
            env_profiles = exporter.env_manager.get_all_supabase_profiles()
            gui_profiles = exporter.config.get_supabase_connections()

            print("🔗 Available Supabase Profiles:")
            total = 0

            if env_profiles:
                print("   📁 Environment Profiles:")
                for profile_name in env_profiles:
                    credentials = exporter.env_manager.get_env_vars_for_profile(
                        profile_name
                    )
                    url = credentials.get("url", "No URL")
                    print(f"     • {profile_name}: {url}")
                    total += 1

            if gui_profiles:
                print("   🖥️  GUI Profiles:")
                for profile in gui_profiles:
                    profile_name = profile.get("name", "Unnamed")
                    url = profile.get("url", "No URL")
                    print(f"     • {profile_name}: {url}")
                    total += 1

            if total == 0:
                print("   No profiles found.")

            return 0

        # Parse optional parameters
        schemas = None
        if args.schemas:
            schemas = [s.strip() for s in args.schemas.split(",") if s.strip()]

        tables = None
        if args.tables:
            tables = [t.strip() for t in args.tables.split(",") if t.strip()]

        # Run export
        result = asyncio.run(
            exporter.export_project(
                profile_name=args.profile,
                manual_url=args.url,
                manual_service_key=args.service_key,
                output_format=args.format,
                output_dir=args.output,
                include_data=not args.no_data,
                schemas=schemas,
                tables=tables,
            )
        )

        if result["success"]:
            print("\n🎉 Export completed successfully!")

            if args.format == "dump":
                print("💡 Restore with: pg_restore -d target_database file.dump")
            elif args.format == "sql":
                print("💡 Restore with: psql -d target_database < file.sql")
            elif args.format == "json":
                print("💡 Use for analysis, comparison, or custom import scripts")

            print(f"📁 Files saved to: {result['output_dir']}")
            return 0
        else:
            print(f"❌ Export failed: {result['error']}")
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
        return 1


if __name__ == "__main__":
    sys.exit(main())
