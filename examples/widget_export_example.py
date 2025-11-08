#!/usr/bin/env python3
"""
Widget Export and Merging Example

This example demonstrates how to export Supabase project state for widget merging.
Shows different export formats and how to prepare data for merging two widget projects.

Usage:
    python widget_export_example.py --help
    python widget_export_example.py --export-widget1
    python widget_export_example.py --export-widget2 --format json
    python widget_export_example.py --merge-widgets
"""

import asyncio
import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Import your Supabase export functionality
import sys

sys.path.append(str(Path(__file__).parent.parent))

from varchiver.supamerge.export import (
    SupabaseExporter,
    ExportOptions,
    export_supabase_project,
)
from varchiver.supamerge.core import SourceConfig
from varchiver.utils.env_manager import EnvManager


class WidgetProjectManager:
    """Manages widget project exports and merging."""

    def __init__(self):
        self.env_manager = EnvManager()
        self.export_dir = Path("widget_exports")
        self.export_dir.mkdir(exist_ok=True)

    def get_project_config(self, profile_name: str) -> SourceConfig:
        """Get Supabase configuration for a profile."""
        credentials = self.env_manager.get_env_vars_for_profile(profile_name)

        if not credentials:
            raise ValueError(
                f"Profile '{profile_name}' not found. Available profiles: {list(self.env_manager.get_all_supabase_profiles().keys())}"
            )

        return SourceConfig(
            project_ref=credentials.get("project_ref", profile_name),
            db_url=f"postgresql://postgres.{credentials['project_ref']}:{credentials['service_key']}@aws-0-us-west-1.pooler.supabase.com:5432/postgres",
            supabase_url=credentials["url"],
            anon_key=credentials["anon_key"],
            service_role_key=credentials["service_key"],
        )

    async def export_widget_project(
        self, profile_name: str, export_format: str = "dump", include_data: bool = True
    ) -> Dict[str, any]:
        """Export a widget project in the specified format."""

        print(f"🚀 Exporting widget project '{profile_name}' as {export_format}")

        try:
            # Get project configuration
            source_config = self.get_project_config(profile_name)

            # Create export options
            export_options = ExportOptions(
                output_format=export_format,
                output_dir=str(self.export_dir),
                include_schema=True,
                include_data=include_data,
                include_policies=True,
                include_storage=False,  # Usually not needed for widgets
                schemas=["public"],
                tables=[],  # Export all tables
            )

            # Perform export
            exporter = SupabaseExporter(source_config)
            result = await exporter.export_project_state(export_options)

            if result.success:
                print(f"✅ Export completed successfully!")
                print(f"⏱️  Time taken: {result.execution_time:.2f} seconds")
                print(f"📁 Files created:")
                for file_path in result.export_files:
                    file_size = os.path.getsize(file_path) / 1024  # KB
                    print(f"   - {Path(file_path).name} ({file_size:.1f} KB)")

                return {
                    "success": True,
                    "files": result.export_files,
                    "metadata": result.metadata,
                }
            else:
                print(f"❌ Export failed: {result.message}")
                return {"success": False, "error": result.message}

        except Exception as e:
            print(f"❌ Export error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def compare_widget_schemas(
        self, profile1: str, profile2: str
    ) -> Dict[str, any]:
        """Compare schemas between two widget projects."""

        print(f"🔍 Comparing schemas between '{profile1}' and '{profile2}'")

        # Export both projects as JSON for comparison
        result1 = await self.export_widget_project(profile1, "json", include_data=False)
        result2 = await self.export_widget_project(profile2, "json", include_data=False)

        if not (result1["success"] and result2["success"]):
            return {"success": False, "error": "Failed to export one or both projects"}

        # Load schema files
        schema_files = {}
        for result, name in [(result1, profile1), (result2, profile2)]:
            schema_file = next((f for f in result["files"] if "schema" in f), None)
            if schema_file:
                with open(schema_file, "r") as f:
                    schema_files[name] = json.load(f)

        # Compare schemas
        comparison = {
            "profiles": [profile1, profile2],
            "common_tables": [],
            "unique_to_profile1": [],
            "unique_to_profile2": [],
            "conflicting_columns": {},
            "success": True,
        }

        if "public" in schema_files[profile1] and "public" in schema_files[profile2]:
            tables1 = set(schema_files[profile1]["public"]["tables"].keys())
            tables2 = set(schema_files[profile2]["public"]["tables"].keys())

            comparison["common_tables"] = list(tables1 & tables2)
            comparison["unique_to_profile1"] = list(tables1 - tables2)
            comparison["unique_to_profile2"] = list(tables2 - tables1)

            # Check for column conflicts in common tables
            for table in comparison["common_tables"]:
                cols1 = {
                    col["name"]: col
                    for col in schema_files[profile1]["public"]["tables"][table][
                        "columns"
                    ]
                }
                cols2 = {
                    col["name"]: col
                    for col in schema_files[profile2]["public"]["tables"][table][
                        "columns"
                    ]
                }

                conflicts = []
                for col_name in cols1:
                    if col_name in cols2:
                        if cols1[col_name]["type"] != cols2[col_name]["type"]:
                            conflicts.append(
                                {
                                    "column": col_name,
                                    f"{profile1}_type": cols1[col_name]["type"],
                                    f"{profile2}_type": cols2[col_name]["type"],
                                }
                            )

                if conflicts:
                    comparison["conflicting_columns"][table] = conflicts

        # Print comparison results
        print("\n📊 Schema Comparison Results:")
        print(f"   Common tables: {len(comparison['common_tables'])}")
        print(
            f"   Tables unique to {profile1}: {len(comparison['unique_to_profile1'])}"
        )
        print(
            f"   Tables unique to {profile2}: {len(comparison['unique_to_profile2'])}"
        )
        print(
            f"   Tables with column conflicts: {len(comparison['conflicting_columns'])}"
        )

        if comparison["conflicting_columns"]:
            print("\n⚠️  Column Conflicts Detected:")
            for table, conflicts in comparison["conflicting_columns"].items():
                print(f"   Table '{table}':")
                for conflict in conflicts:
                    print(
                        f"     - {conflict['column']}: {conflict[f'{profile1}_type']} vs {conflict[f'{profile2}_type']}"
                    )

        # Save comparison report
        report_file = (
            self.export_dir / f"schema_comparison_{profile1}_vs_{profile2}.json"
        )
        with open(report_file, "w") as f:
            json.dump(comparison, f, indent=2)
        print(f"\n📄 Comparison report saved: {report_file}")

        return comparison

    def create_merge_strategy(self, comparison: Dict[str, any]) -> Dict[str, any]:
        """Create a merging strategy based on schema comparison."""

        profile1, profile2 = comparison["profiles"]

        strategy = {
            "merge_plan": {
                "copy_unique_tables": {
                    f"from_{profile1}": comparison["unique_to_profile1"],
                    f"from_{profile2}": comparison["unique_to_profile2"],
                },
                "merge_common_tables": {
                    "strategy": "union",  # or "priority", "manual"
                    "tables": comparison["common_tables"],
                },
                "handle_conflicts": {
                    "column_conflicts": comparison["conflicting_columns"],
                    "resolution": "rename_conflicting",  # or "priority", "manual"
                },
            },
            "migration_steps": [
                f"1. Backup target database",
                f"2. Import unique tables from {profile1}",
                f"3. Import unique tables from {profile2}",
                f"4. Merge common tables with conflict resolution",
                f"5. Update RLS policies",
                f"6. Verify data integrity",
            ],
            "estimated_complexity": "medium"
            if comparison["conflicting_columns"]
            else "low",
        }

        # Save merge strategy
        strategy_file = (
            self.export_dir / f"merge_strategy_{profile1}_to_{profile2}.yaml"
        )
        with open(strategy_file, "w") as f:
            yaml.dump(strategy, f, default_flow_style=False, indent=2)

        print(f"\n📋 Merge strategy created: {strategy_file}")
        return strategy

    async def prepare_widget_merge(
        self, source_profile: str, target_profile: str
    ) -> Dict[str, any]:
        """Prepare everything needed for merging two widget projects."""

        print(f"🔧 Preparing merge from '{source_profile}' to '{target_profile}'")

        # Step 1: Compare schemas
        comparison = await self.compare_widget_schemas(source_profile, target_profile)

        if not comparison["success"]:
            return comparison

        # Step 2: Export both projects in multiple formats
        print("\n📦 Exporting source project...")
        source_dump = await self.export_widget_project(
            source_profile, "dump", include_data=True
        )
        source_json = await self.export_widget_project(
            source_profile, "json", include_data=True
        )

        print("\n📦 Exporting target project (backup)...")
        target_backup = await self.export_widget_project(
            target_profile, "dump", include_data=True
        )

        # Step 3: Create merge strategy
        strategy = self.create_merge_strategy(comparison)

        # Step 4: Generate merge instructions
        instructions_file = (
            self.export_dir
            / f"MERGE_INSTRUCTIONS_{source_profile}_to_{target_profile}.md"
        )
        with open(instructions_file, "w") as f:
            f.write(f"# Widget Project Merge Instructions\n\n")
            f.write(f"**Source Project:** {source_profile}\n")
            f.write(f"**Target Project:** {target_profile}\n")
            f.write(f"**Generated:** {asyncio.get_event_loop().time()}\n\n")

            f.write("## Prerequisites\n\n")
            f.write("- [ ] Both projects backed up\n")
            f.write("- [ ] Target project access confirmed\n")
            f.write("- [ ] Merge strategy reviewed\n\n")

            f.write("## Files Generated\n\n")
            f.write("### Source Project Exports\n")
            if source_dump["success"]:
                for file_path in source_dump["files"]:
                    f.write(f"- `{Path(file_path).name}` - PostgreSQL dump\n")
            if source_json["success"]:
                for file_path in source_json["files"]:
                    f.write(f"- `{Path(file_path).name}` - JSON data\n")

            f.write("\n### Target Project Backup\n")
            if target_backup["success"]:
                for file_path in target_backup["files"]:
                    f.write(f"- `{Path(file_path).name}` - Backup dump\n")

            f.write("\n## Migration Commands\n\n")
            f.write("Use the Supamerge tool to perform the actual migration:\n\n")
            f.write("```bash\n")
            f.write("# Option 1: Use configuration file\n")
            f.write(
                "supamerge migrate --config merge_config.yaml --backup --dry-run\n\n"
            )
            f.write("# Option 2: Use environment variables\n")
            f.write(
                f"supamerge migrate --from-env {source_profile.upper()} --to-env {target_profile.upper()} --backup --include-data\n"
            )
            f.write("```\n\n")

            f.write("## Manual Steps (if needed)\n\n")
            if comparison["conflicting_columns"]:
                f.write("### Resolve Column Conflicts\n\n")
                for table, conflicts in comparison["conflicting_columns"].items():
                    f.write(f"**Table: {table}**\n")
                    for conflict in conflicts:
                        f.write(
                            f"- Column `{conflict['column']}`: Choose between `{conflict[f'{source_profile}_type']}` and `{conflict[f'{target_profile}_type']}`\n"
                        )
                    f.write("\n")

        print(f"📋 Merge instructions created: {instructions_file}")

        result = {
            "success": True,
            "message": "Widget merge preparation completed",
            "files": {
                "instructions": str(instructions_file),
                "strategy": str(
                    self.export_dir
                    / f"merge_strategy_{source_profile}_to_{target_profile}.yaml"
                ),
                "comparison": str(
                    self.export_dir
                    / f"schema_comparison_{source_profile}_vs_{target_profile}.json"
                ),
                "source_exports": source_dump["files"]
                if source_dump["success"]
                else [],
                "target_backup": target_backup["files"]
                if target_backup["success"]
                else [],
            },
            "next_steps": [
                "Review merge strategy and instructions",
                "Test migration with --dry-run flag",
                "Execute migration using supamerge",
                "Verify merged data integrity",
            ],
        }

        print(f"\n✅ Widget merge preparation completed!")
        print(f"📁 All files saved to: {self.export_dir}")

        return result


async def main():
    """Main function for the widget export example."""

    parser = argparse.ArgumentParser(
        description="Widget Export and Merging Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export widget project as PostgreSQL dump
  python widget_export_example.py --export widget1

  # Export as JSON for analysis
  python widget_export_example.py --export widget2 --format json

  # Compare two widget projects
  python widget_export_example.py --compare widget1 widget2

  # Prepare complete merge from widget1 to widget2
  python widget_export_example.py --prepare-merge widget1 widget2

  # List available Supabase profiles
  python widget_export_example.py --list-profiles
        """,
    )

    # Action options
    parser.add_argument("--export", help="Export a widget project by profile name")
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("PROFILE1", "PROFILE2"),
        help="Compare two widget projects",
    )
    parser.add_argument(
        "--prepare-merge",
        nargs=2,
        metavar=("SOURCE", "TARGET"),
        help="Prepare merge from source to target",
    )
    parser.add_argument(
        "--list-profiles", action="store_true", help="List available Supabase profiles"
    )

    # Export options
    parser.add_argument(
        "--format",
        choices=["dump", "sql", "json", "yaml"],
        default="dump",
        help="Export format (default: dump)",
    )
    parser.add_argument(
        "--no-data", action="store_true", help="Export schema only, no data"
    )
    parser.add_argument(
        "--output-dir", help="Output directory (default: ./widget_exports)"
    )

    args = parser.parse_args()

    manager = WidgetProjectManager()

    # Override output directory if specified
    if args.output_dir:
        manager.export_dir = Path(args.output_dir)
        manager.export_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.list_profiles:
            profiles = manager.env_manager.get_all_supabase_profiles()
            print("🔗 Available Supabase Profiles:")
            if profiles:
                for profile_name, details in profiles.items():
                    print(f"   - {profile_name}: {details.get('url', 'No URL')}")
            else:
                print(
                    "   No profiles found. Add profiles using Varchiver's connection manager."
                )
                print(
                    "   Or set environment variables like SUPABASE_MYPROJECT_URL, etc."
                )

        elif args.export:
            include_data = not args.no_data
            result = await manager.export_widget_project(
                args.export, args.format, include_data
            )
            if not result["success"]:
                return 1

        elif args.compare:
            profile1, profile2 = args.compare
            comparison = await manager.compare_widget_schemas(profile1, profile2)
            if not comparison["success"]:
                return 1

        elif args.prepare_merge:
            source_profile, target_profile = args.prepare_merge
            result = await manager.prepare_widget_merge(source_profile, target_profile)
            if not result["success"]:
                print(
                    f"❌ Merge preparation failed: {result.get('error', 'Unknown error')}"
                )
                return 1

            print(f"\n🎯 Next Steps:")
            for step in result["next_steps"]:
                print(f"   - {step}")

        else:
            parser.print_help()
            return 1

        return 0

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
