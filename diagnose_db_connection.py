#!/usr/bin/env python3
"""
Supabase Database Connection Diagnostic Tool

This tool helps diagnose and find the correct database connection string format
for your Supabase projects. It tries various connection methods and provides
detailed feedback on what works and what doesn't.

Usage:
    uv run python diagnose_db_connection.py --profile development
    uv run python diagnose_db_connection.py --url https://abc123.supabase.co --service-key eyJ...
"""

import sys
import argparse
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# Add the varchiver module to the path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    import psycopg2
    from psycopg2 import sql
    from varchiver.utils.env_manager import EnvManager
    from varchiver.utils.config import Config
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run with: uv run python diagnose_db_connection.py")
    sys.exit(1)


class DatabaseConnectionDiagnostic:
    """Diagnostic tool for Supabase database connections."""

    def __init__(self):
        self.env_manager = EnvManager()
        self.config = Config()

    def get_profile_credentials(self, profile_name: str) -> Optional[Dict[str, str]]:
        """Get credentials for a profile from either environment or GUI config."""
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
        """Generate various connection string formats to test."""
        connection_formats = [
            # Session pooler (recommended for persistent connections)
            {
                "name": "Session Pooler (6543) - us-west-1",
                "url": f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-west-1.pooler.supabase.com:6543/postgres",
                "type": "session_pooler",
            },
            {
                "name": "Session Pooler (6543) - us-east-1",
                "url": f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-east-1.pooler.supabase.com:6543/postgres",
                "type": "session_pooler",
            },
            {
                "name": "Session Pooler (6543) - eu-west-1",
                "url": f"postgresql://postgres.{project_ref}:{service_key}@aws-0-eu-west-1.pooler.supabase.com:6543/postgres",
                "type": "session_pooler",
            },
            # Transaction pooler (for serverless)
            {
                "name": "Transaction Pooler (5432) - us-west-1",
                "url": f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-west-1.pooler.supabase.com:5432/postgres",
                "type": "transaction_pooler",
            },
            {
                "name": "Transaction Pooler (5432) - us-east-1",
                "url": f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-east-1.pooler.supabase.com:5432/postgres",
                "type": "transaction_pooler",
            },
            # Direct connection (requires IPv6 or IPv4 add-on)
            {
                "name": "Direct Connection",
                "url": f"postgresql://postgres.{project_ref}:{service_key}@db.{project_ref}.supabase.co:5432/postgres",
                "type": "direct",
            },
            # Alternative formats
            {
                "name": "Alternative Format 1",
                "url": f"postgresql://postgres:{service_key}@aws-0-us-west-1.pooler.supabase.com:6543/postgres?user=postgres.{project_ref}",
                "type": "alternative",
            },
            {
                "name": "Alternative Format 2",
                "url": f"postgresql://postgres:{service_key}@db.{project_ref}.supabase.co:6543/postgres",
                "type": "alternative",
            },
        ]

        return connection_formats

    def test_connection(
        self, connection_string: str, timeout: int = 5
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Test a database connection and return success status, error, and info."""
        try:
            print(f"    🔍 Testing connection (timeout: {timeout}s)...")

            start_time = time.time()
            conn = psycopg2.connect(connection_string, connect_timeout=timeout)
            connect_time = time.time() - start_time

            # Get some basic database info
            cur = conn.cursor()
            cur.execute("SELECT version();")
            postgres_version = cur.fetchone()[0]

            cur.execute(
                "SELECT current_database(), current_user, inet_server_addr(), inet_server_port();"
            )
            db_info = cur.fetchone()

            cur.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
            )
            table_count = cur.fetchone()[0]

            info = {
                "connect_time": round(connect_time, 3),
                "postgres_version": postgres_version,
                "database": db_info[0],
                "user": db_info[1],
                "server_addr": db_info[2],
                "server_port": db_info[3],
                "public_table_count": table_count,
            }

            cur.close()
            conn.close()

            return True, None, info

        except psycopg2.OperationalError as e:
            error_msg = str(e).strip()
            return False, error_msg, None
        except Exception as e:
            return False, f"Unexpected error: {str(e)}", None

    def diagnose_profile(self, profile_name: str, verbose: bool = False) -> bool:
        """Diagnose database connection for a profile."""
        print(f"🔍 Diagnosing database connection for profile: '{profile_name}'")
        print("=" * 60)

        # Get credentials
        credentials = self.get_profile_credentials(profile_name)
        if not credentials:
            print(f"❌ Profile '{profile_name}' not found or missing credentials")
            return False

        url = credentials["url"]
        service_key = credentials["service_key"]
        project_ref = self.extract_project_ref(url)

        print(f"📋 Profile Information:")
        print(f"   Project URL: {url}")
        print(f"   Project Ref: {project_ref}")
        print(f"   Service Key: {service_key[:20]}...")
        print()

        # Generate connection strings to test
        connection_formats = self.generate_connection_strings(project_ref, service_key)

        successful_connections = []
        failed_connections = []

        print(f"🧪 Testing {len(connection_formats)} connection formats...")
        print()

        for i, conn_format in enumerate(connection_formats, 1):
            name = conn_format["name"]
            conn_url = conn_format["url"]
            conn_type = conn_format["type"]

            print(f"{i}. {name} ({conn_type})")
            if verbose:
                print(f"   URL: {conn_url}")

            success, error, info = self.test_connection(conn_url)

            if success:
                print(f"   ✅ SUCCESS!")
                print(f"   📊 Connection time: {info['connect_time']}s")
                print(f"   🗄️  Database: {info['database']}")
                print(f"   👤 User: {info['user']}")
                print(f"   🌐 Server: {info['server_addr']}:{info['server_port']}")
                print(f"   📋 Public tables: {info['public_table_count']}")

                successful_connections.append({**conn_format, "info": info})
            else:
                print(f"   ❌ FAILED")
                print(f"   💥 Error: {error}")

                failed_connections.append({**conn_format, "error": error})

            print()

        # Summary
        print("=" * 60)
        print(f"📊 DIAGNOSIS SUMMARY")
        print("=" * 60)
        print(f"✅ Successful connections: {len(successful_connections)}")
        print(f"❌ Failed connections: {len(failed_connections)}")
        print()

        if successful_connections:
            print("🎉 WORKING CONNECTION STRINGS:")
            print()
            for i, conn in enumerate(successful_connections, 1):
                print(f"{i}. {conn['name']}")
                print(f"   Type: {conn['type']}")
                print(f"   URL: {conn['url']}")
                print(
                    f"   Performance: {conn['info']['connect_time']}s connection time"
                )
                print()

            # Recommend the best connection
            best_conn = min(
                successful_connections, key=lambda x: x["info"]["connect_time"]
            )
            print(f"🏆 RECOMMENDED CONNECTION:")
            print(f"   {best_conn['name']}")
            print(f"   URL: {best_conn['url']}")
            print()

            return True
        else:
            print("😞 No working connections found.")
            print()
            print("💡 TROUBLESHOOTING SUGGESTIONS:")
            print("   1. Verify your service role key is correct")
            print("   2. Check that your Supabase project is active (not paused)")
            print("   3. Ensure your project supports the connection methods tested")
            print(
                "   4. Try getting the connection string directly from Supabase Dashboard:"
            )
            print("      → Settings → Database → Connection string")
            print("   5. Check if your project requires IPv4 add-on")
            print(
                "   6. Verify your network allows outbound connections on ports 5432/6543"
            )
            print()

            # Analyze common error patterns
            common_errors = {}
            for conn in failed_connections:
                error = conn["error"]
                if "FATAL" in error:
                    key = "Authentication/Permission"
                elif "timeout" in error.lower():
                    key = "Network/Timeout"
                elif "host" in error.lower():
                    key = "DNS/Host Resolution"
                else:
                    key = "Other"

                common_errors[key] = common_errors.get(key, 0) + 1

            print("📈 ERROR ANALYSIS:")
            for error_type, count in common_errors.items():
                print(f"   {error_type}: {count} occurrences")
            print()

            return False

    def diagnose_manual(
        self, url: str, service_key: str, verbose: bool = False
    ) -> bool:
        """Diagnose database connection with manual credentials."""
        project_ref = self.extract_project_ref(url)

        print(f"🔍 Diagnosing database connection with manual credentials")
        print("=" * 60)
        print(f"   Project URL: {url}")
        print(f"   Project Ref: {project_ref}")
        print(f"   Service Key: {service_key[:20]}...")
        print()

        # Test the connection formats
        connection_formats = self.generate_connection_strings(project_ref, service_key)

        # Same testing logic as diagnose_profile
        successful_connections = []

        for conn_format in connection_formats:
            success, error, info = self.test_connection(conn_format["url"])
            if success:
                successful_connections.append({**conn_format, "info": info})

        return len(successful_connections) > 0


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Supabase Database Connection Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Diagnose a configured profile
  uv run python diagnose_db_connection.py --profile development

  # Diagnose with manual credentials
  uv run python diagnose_db_connection.py \\
    --url https://abc123.supabase.co \\
    --service-key eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

  # List available profiles
  uv run python diagnose_db_connection.py --list-profiles

  # Verbose output
  uv run python diagnose_db_connection.py --profile development --verbose
        """,
    )

    parser.add_argument("--profile", "-p", help="Profile name to diagnose")
    parser.add_argument("--url", help="Supabase project URL (for manual diagnosis)")
    parser.add_argument(
        "--service-key", help="Supabase service role key (for manual diagnosis)"
    )
    parser.add_argument(
        "--list-profiles", action="store_true", help="List available Supabase profiles"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return 1

    diagnostic = DatabaseConnectionDiagnostic()

    try:
        if args.list_profiles:
            # List available profiles
            env_profiles = diagnostic.env_manager.get_all_supabase_profiles()
            gui_profiles = diagnostic.config.get_supabase_connections()

            print("🔗 Available Supabase Profiles:")

            if env_profiles:
                print("   📁 Environment Profiles:")
                for profile_name in env_profiles:
                    credentials = diagnostic.env_manager.get_env_vars_for_profile(
                        profile_name
                    )
                    url = credentials.get("url", "No URL")
                    print(f"     • {profile_name}: {url}")

            if gui_profiles:
                print("   🖥️  GUI Profiles:")
                for profile in gui_profiles:
                    profile_name = profile.get("name", "Unnamed")
                    url = profile.get("url", "No URL")
                    print(f"     • {profile_name}: {url}")

            if not env_profiles and not gui_profiles:
                print("   No profiles found.")

            return 0

        elif args.profile:
            # Diagnose profile
            success = diagnostic.diagnose_profile(args.profile, args.verbose)
            return 0 if success else 1

        elif args.url and args.service_key:
            # Manual diagnosis
            success = diagnostic.diagnose_manual(
                args.url, args.service_key, args.verbose
            )
            return 0 if success else 1

        else:
            print("❌ Error: Must specify --profile or both --url and --service-key")
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\n❌ Diagnosis cancelled by user")
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
    sys.exit(main())
