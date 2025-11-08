"""
Supabase State Export Utility for Widget Merging

This module provides functionality to export complete Supabase project state
in various formats suitable for merging widget projects or creating backups.

Supported formats:
- .dump (PostgreSQL custom format) - Most complete
- .sql (Plain SQL format) - Human readable
- .json (Structured data export) - API-friendly
- .yaml (Configuration + metadata) - Configuration management
"""

import asyncio
import json
import yaml
import os
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2 import sql
from supabase import Client, create_client

from .core import SupamergeError, SourceConfig


@dataclass
class ExportOptions:
    """Options for exporting Supabase project state."""

    include_schema: bool = True
    include_data: bool = True
    include_policies: bool = True
    include_storage: bool = True
    include_auth: bool = False
    schemas: List[str] = None
    tables: List[str] = None
    output_format: str = "dump"  # dump, sql, json, yaml
    output_dir: str = None

    def __post_init__(self):
        if self.schemas is None:
            self.schemas = ["public"]
        if self.tables is None:
            self.tables = []
        if self.output_dir is None:
            self.output_dir = os.getcwd()


@dataclass
class ExportResult:
    """Results of an export operation."""

    success: bool
    message: str
    export_files: List[str] = None
    metadata: Dict[str, Any] = None
    execution_time: float = 0.0

    def __post_init__(self):
        if self.export_files is None:
            self.export_files = []
        if self.metadata is None:
            self.metadata = {}


class SupabaseExporter:
    """Main class for exporting Supabase project state."""

    def __init__(
        self, source_config: SourceConfig, logger: Optional[logging.Logger] = None
    ):
        self.source = source_config
        self.logger = logger or self._setup_logger()
        self.temp_dir = None

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for export operations."""
        logger = logging.getLogger(f"supabase_exporter_{id(self)}")
        logger.setLevel(logging.INFO)

        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # File handler
        log_file = log_dir / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    async def export_project_state(self, options: ExportOptions) -> ExportResult:
        """
        Export complete Supabase project state in the specified format.

        Args:
            options: Export configuration options

        Returns:
            ExportResult with details of the export operation
        """
        start_time = datetime.now()

        try:
            # Create temporary directory for operations
            self.temp_dir = tempfile.mkdtemp(prefix="supabase_export_")
            self.logger.info(f"Starting export with temp directory: {self.temp_dir}")

            # Validate configuration
            self._validate_configuration()

            # Create output directory if it doesn't exist
            output_dir = Path(options.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            export_files = []
            metadata = {}

            # Generate timestamp for file naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = self.source.project_ref

            # Export based on format
            if options.output_format == "dump":
                files, meta = await self._export_as_dump(
                    options, timestamp, project_name
                )
                export_files.extend(files)
                metadata.update(meta)

            elif options.output_format == "sql":
                files, meta = await self._export_as_sql(
                    options, timestamp, project_name
                )
                export_files.extend(files)
                metadata.update(meta)

            elif options.output_format == "json":
                files, meta = await self._export_as_json(
                    options, timestamp, project_name
                )
                export_files.extend(files)
                metadata.update(meta)

            elif options.output_format == "yaml":
                files, meta = await self._export_as_yaml(
                    options, timestamp, project_name
                )
                export_files.extend(files)
                metadata.update(meta)

            else:
                raise SupamergeError(
                    f"Unsupported export format: {options.output_format}"
                )

            # Create export manifest
            manifest_file = await self._create_export_manifest(
                export_files, metadata, options, timestamp, project_name
            )
            export_files.append(manifest_file)

            execution_time = (datetime.now() - start_time).total_seconds()

            self.logger.info(
                f"Export completed successfully in {execution_time:.2f} seconds"
            )

            return ExportResult(
                success=True,
                message=f"Project state exported successfully as {options.output_format}",
                export_files=export_files,
                metadata=metadata,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Export failed: {str(e)}"
            self.logger.error(error_msg)

            return ExportResult(
                success=False, message=error_msg, execution_time=execution_time
            )

        finally:
            # Cleanup temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil

                shutil.rmtree(self.temp_dir)

    def _validate_configuration(self):
        """Validate the source configuration."""
        required_fields = ["project_ref", "db_url", "supabase_url"]
        for field in required_fields:
            if not getattr(self.source, field, None):
                raise SupamergeError(f"Missing required source configuration: {field}")

    async def _export_as_dump(
        self, options: ExportOptions, timestamp: str, project_name: str
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Export project as PostgreSQL dump format (.dump)."""
        self.logger.info("Exporting as PostgreSQL dump format...")

        dump_file = os.path.join(
            options.output_dir, f"{project_name}_export_{timestamp}.dump"
        )

        cmd = [
            "pg_dump",
            self.source.db_url,
            "--no-owner",
            "--no-privileges",
            "--format=custom",
        ]

        # Add schema filters
        if options.schemas and options.schemas != ["public"]:
            for schema in options.schemas:
                cmd.extend(["--schema", schema])

        # Add table filters
        if options.tables:
            for table in options.tables:
                cmd.extend(["--table", table])

        # Data options
        if not options.include_data:
            cmd.append("--schema-only")

        cmd.extend(["-f", dump_file])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise SupamergeError(f"pg_dump failed: {result.stderr}")

        metadata = {
            "format": "dump",
            "includes_data": options.include_data,
            "schemas": options.schemas,
            "tables": options.tables,
        }

        return [dump_file], metadata

    async def _export_as_sql(
        self, options: ExportOptions, timestamp: str, project_name: str
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Export project as plain SQL format (.sql)."""
        self.logger.info("Exporting as SQL format...")

        sql_file = os.path.join(
            options.output_dir, f"{project_name}_export_{timestamp}.sql"
        )

        cmd = [
            "pg_dump",
            self.source.db_url,
            "--no-owner",
            "--no-privileges",
            "--format=plain",
        ]

        # Add schema filters
        if options.schemas and options.schemas != ["public"]:
            for schema in options.schemas:
                cmd.extend(["--schema", schema])

        # Add table filters
        if options.tables:
            for table in options.tables:
                cmd.extend(["--table", table])

        # Data options
        if not options.include_data:
            cmd.append("--schema-only")

        cmd.extend(["-f", sql_file])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise SupamergeError(f"pg_dump failed: {result.stderr}")

        metadata = {
            "format": "sql",
            "includes_data": options.include_data,
            "schemas": options.schemas,
            "tables": options.tables,
        }

        return [sql_file], metadata

    async def _export_as_json(
        self, options: ExportOptions, timestamp: str, project_name: str
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Export project as JSON format (.json)."""
        self.logger.info("Exporting as JSON format...")

        export_files = []

        # Export schema as JSON
        if options.include_schema:
            schema_file = os.path.join(
                options.output_dir, f"{project_name}_schema_{timestamp}.json"
            )
            schema_data = await self._get_schema_as_json(options.schemas)
            with open(schema_file, "w") as f:
                json.dump(schema_data, f, indent=2, default=str)
            export_files.append(schema_file)

        # Export data as JSON
        if options.include_data:
            data_file = os.path.join(
                options.output_dir, f"{project_name}_data_{timestamp}.json"
            )
            data = await self._get_data_as_json(options.schemas, options.tables)
            with open(data_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
            export_files.append(data_file)

        # Export policies as JSON
        if options.include_policies:
            policies_file = os.path.join(
                options.output_dir, f"{project_name}_policies_{timestamp}.json"
            )
            policies = await self._get_policies_as_json(options.schemas)
            with open(policies_file, "w") as f:
                json.dump(policies, f, indent=2, default=str)
            export_files.append(policies_file)

        metadata = {
            "format": "json",
            "includes_schema": options.include_schema,
            "includes_data": options.include_data,
            "includes_policies": options.include_policies,
            "schemas": options.schemas,
            "tables": options.tables,
        }

        return export_files, metadata

    async def _export_as_yaml(
        self, options: ExportOptions, timestamp: str, project_name: str
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Export project as YAML format (.yaml)."""
        self.logger.info("Exporting as YAML format...")

        export_files = []

        # Create comprehensive export structure
        export_data = {
            "project_info": {
                "project_ref": self.source.project_ref,
                "export_timestamp": timestamp,
                "export_options": asdict(options),
            }
        }

        # Add schema
        if options.include_schema:
            export_data["schema"] = await self._get_schema_as_json(options.schemas)

        # Add data
        if options.include_data:
            export_data["data"] = await self._get_data_as_json(
                options.schemas, options.tables
            )

        # Add policies
        if options.include_policies:
            export_data["policies"] = await self._get_policies_as_json(options.schemas)

        yaml_file = os.path.join(
            options.output_dir, f"{project_name}_export_{timestamp}.yaml"
        )

        with open(yaml_file, "w") as f:
            yaml.dump(export_data, f, default_flow_style=False, indent=2, default=str)

        export_files.append(yaml_file)

        metadata = {
            "format": "yaml",
            "includes_schema": options.include_schema,
            "includes_data": options.include_data,
            "includes_policies": options.include_policies,
            "schemas": options.schemas,
            "tables": options.tables,
        }

        return export_files, metadata

    async def _get_schema_as_json(self, schemas: List[str]) -> Dict[str, Any]:
        """Get database schema information as JSON."""
        schema_info = {}

        # Try direct database connection first
        try:
            conn = psycopg2.connect(self.source.db_url)
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

                    tables[table_name] = {"type": table_type, "columns": columns}

                schema_info[schema] = {"tables": tables}

            cur.close()
            conn.close()

        except Exception as db_error:
            self.logger.warning(f"Database connection failed: {db_error}")
            self.logger.info("Attempting to extract schema via REST API...")

            # Fallback to REST API approach
            try:
                schema_info = await self._get_schema_via_rest_api(schemas)
            except Exception as api_error:
                self.logger.warning(
                    f"Could not extract schema info via REST API: {api_error}"
                )

        return schema_info

    async def _get_data_as_json(
        self, schemas: List[str], tables: List[str] = None
    ) -> Dict[str, Any]:
        """Get table data as JSON."""
        data_info = {}

        # Try direct database connection first
        try:
            conn = psycopg2.connect(self.source.db_url)
            cur = conn.cursor()

            for schema in schemas:
                # Get table list
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
                    # Get column names
                    cur.execute(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s
                        ORDER BY ordinal_position
                    """,
                        (schema, table_name),
                    )

                    columns = [row[0] for row in cur.fetchall()]

                    # Get data
                    cur.execute(
                        sql.SQL("SELECT * FROM {}.{}").format(
                            sql.Identifier(schema), sql.Identifier(table_name)
                        )
                    )

                    rows = cur.fetchall()
                    table_data = []
                    for row in rows:
                        row_dict = {}
                        for i, value in enumerate(row):
                            row_dict[columns[i]] = value
                        table_data.append(row_dict)

                    schema_data[table_name] = table_data

                data_info[schema] = schema_data

            cur.close()
            conn.close()

        except Exception as db_error:
            self.logger.warning(f"Database connection failed: {db_error}")
            self.logger.info("Attempting to extract data via REST API...")

            # Fallback to REST API approach
            try:
                data_info = await self._get_data_via_rest_api(schemas, tables)
            except Exception as api_error:
                self.logger.warning(f"Could not extract data via REST API: {api_error}")

        return data_info

    async def _get_policies_as_json(self, schemas: List[str]) -> Dict[str, Any]:
        """Get RLS policies as JSON."""
        policies_info = {}

        try:
            conn = psycopg2.connect(self.source.db_url)
            cur = conn.cursor()

            for schema in schemas:
                cur.execute(
                    """
                    SELECT schemaname, tablename, policyname, permissive,
                           roles, cmd, qual, with_check
                    FROM pg_policies
                    WHERE schemaname = %s
                """,
                    (schema,),
                )

                schema_policies = {}
                for row in cur.fetchall():
                    (
                        schema_name,
                        table_name,
                        policy_name,
                        permissive,
                        roles,
                        cmd,
                        qual,
                        with_check,
                    ) = row

                    if table_name not in schema_policies:
                        schema_policies[table_name] = []

                    schema_policies[table_name].append(
                        {
                            "name": policy_name,
                            "permissive": permissive,
                            "roles": roles,
                            "command": cmd,
                            "qualifier": qual,
                            "with_check": with_check,
                        }
                    )

                policies_info[schema] = schema_policies

            cur.close()
            conn.close()

        except Exception as e:
            self.logger.warning(f"Could not extract policies: {e}")

        return policies_info

    async def _create_export_manifest(
        self,
        export_files: List[str],
        metadata: Dict[str, Any],
        options: ExportOptions,
        timestamp: str,
        project_name: str,
    ) -> str:
        """Create an export manifest file."""
        manifest_file = os.path.join(
            options.output_dir, f"{project_name}_manifest_{timestamp}.json"
        )

        manifest = {
            "export_info": {
                "project_ref": self.source.project_ref,
                "timestamp": timestamp,
                "format": options.output_format,
                "version": "1.0",
            },
            "options": asdict(options),
            "files": export_files,
            "metadata": metadata,
            "instructions": {
                "restore_dump": "Use pg_restore to restore .dump files",
                "restore_sql": "Use psql < file.sql to restore .sql files",
                "restore_json": "Use custom scripts to import JSON data",
                "restore_yaml": "Use custom scripts to import YAML data",
            },
        }

        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2, default=str)

        return manifest_file

    async def _get_schema_via_rest_api(self, schemas: List[str]) -> Dict[str, Any]:
        """Get schema information using Supabase REST API."""
        schema_info = {}

        try:
            # Create Supabase client
            supabase = create_client(
                self.source.supabase_url, self.source.service_role_key
            )

            for schema in schemas:
                if schema == "public":  # Only public schema is accessible via REST API
                    # Get table information via REST API
                    # This is a simplified approach - get actual table data to infer structure
                    tables = {}

                    # Try to get a list of tables by querying information_schema if available
                    # Note: This is limited compared to direct DB access
                    self.logger.info(
                        f"Extracting {schema} schema via REST API (limited)"
                    )
                    schema_info[schema] = {
                        "tables": tables,
                        "note": "Limited schema extraction via REST API",
                    }

        except Exception as e:
            self.logger.warning(f"REST API schema extraction failed: {e}")

        return schema_info

    async def _get_data_via_rest_api(
        self, schemas: List[str], tables: List[str] = None
    ) -> Dict[str, Any]:
        """Get table data using Supabase REST API."""
        data_info = {}

        try:
            # Create Supabase client
            supabase = create_client(
                self.source.supabase_url, self.source.service_role_key
            )

            for schema in schemas:
                if schema == "public":  # Only public schema accessible via REST API
                    schema_data = {}

                    # If specific tables requested, try those
                    if tables:
                        for table_name in tables:
                            try:
                                result = (
                                    supabase.table(table_name).select("*").execute()
                                )
                                schema_data[table_name] = result.data
                                self.logger.info(
                                    f"Extracted {len(result.data)} rows from {table_name}"
                                )
                            except Exception as e:
                                self.logger.warning(
                                    f"Could not extract data from table {table_name}: {e}"
                                )

                    data_info[schema] = schema_data

        except Exception as e:
            self.logger.warning(f"REST API data extraction failed: {e}")

        return data_info


# Convenience functions for easy usage
async def export_supabase_project(
    source_config: SourceConfig,
    output_format: str = "dump",
    output_dir: str = None,
    include_data: bool = True,
) -> ExportResult:
    """
    Convenience function to export a Supabase project.

    Args:
        source_config: Source project configuration
        output_format: Export format (dump, sql, json, yaml)
        output_dir: Output directory (defaults to current directory)
        include_data: Whether to include table data

    Returns:
        ExportResult with operation details
    """
    options = ExportOptions(
        output_format=output_format,
        output_dir=output_dir or os.getcwd(),
        include_data=include_data,
    )

    exporter = SupabaseExporter(source_config)
    return await exporter.export_project_state(options)


def create_export_config_template(output_path: str = "export_config.yaml"):
    """Create a template configuration file for exports."""
    template = {
        "source": {
            "project_ref": "your-project-ref",
            "db_url": "postgresql://postgres:password@db.project.supabase.co:5432/postgres",
            "supabase_url": "https://your-project.supabase.co",
            "anon_key": "your-anon-key",
            "service_role_key": "your-service-key",
        },
        "export_options": {
            "output_format": "dump",  # dump, sql, json, yaml
            "output_dir": "./exports",
            "include_schema": True,
            "include_data": True,
            "include_policies": True,
            "include_storage": False,
            "schemas": ["public"],
            "tables": [],  # Empty means all tables
        },
    }

    with open(output_path, "w") as f:
        yaml.dump(template, f, default_flow_style=False, indent=2)

    print(f"Export configuration template created: {output_path}")
