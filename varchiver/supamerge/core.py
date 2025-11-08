"""
Supamerge: Core migration logic for Supabase project merging.
Safely migrate schema, data, and policies between Supabase projects.
"""

import subprocess
import asyncio
import yaml
import json
import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2 import sql
from supabase import Client


@dataclass
class SourceConfig:
    """Source project configuration."""

    project_ref: str
    db_url: str
    supabase_url: str
    anon_key: str
    service_role_key: str


@dataclass
class TargetConfig:
    """Target project configuration."""

    project_ref: str
    db_url: str
    supabase_url: str
    anon_key: str
    service_role_key: str


@dataclass
class MigrationOptions:
    """Migration options and preferences."""

    backup_target_first: bool = True
    remap_conflicts: bool = True
    skip_auth: bool = False
    include_storage: bool = True
    include_policies: bool = True
    include_data: bool = True
    schemas: List[str] = None
    dry_run: bool = False

    def __post_init__(self):
        if self.schemas is None:
            self.schemas = ["public"]


@dataclass
class MigrationResult:
    """Results of a migration operation."""

    success: bool
    message: str
    backup_files: List[str] = None
    conflicts: List[str] = None
    skipped_items: List[str] = None
    execution_time: float = 0.0
    log_file: str = None

    def __post_init__(self):
        if self.backup_files is None:
            self.backup_files = []
        if self.conflicts is None:
            self.conflicts = []
        if self.skipped_items is None:
            self.skipped_items = []


class SupamergeError(Exception):
    """Base exception for Supamerge operations."""

    pass


class ConfigurationError(SupamergeError):
    """Raised when configuration is invalid."""

    pass


class MigrationError(SupamergeError):
    """Raised during migration operations."""

    pass


class Supamerge:
    """Main class for handling Supabase project migrations."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize Supamerge with optional config file."""
        self.config_path = config_path
        self.source: Optional[SourceConfig] = None
        self.target: Optional[TargetConfig] = None
        self.options: MigrationOptions = MigrationOptions()
        self.logger = self._setup_logging()
        self.temp_dir = None

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for migration operations."""
        logger = logging.getLogger("supamerge")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            # Create logs directory if it doesn't exist
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)

            # File handler
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"supamerge_{timestamp}.log"
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

    def load_config(self, config_path: str) -> None:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)

            # Parse source configuration
            source_data = config_data.get("source", {})
            self.source = SourceConfig(**source_data)

            # Parse target configuration
            target_data = config_data.get("target", {})
            self.target = TargetConfig(**target_data)

            # Parse options
            options_data = config_data.get("options", {})
            # Handle include section if present
            include_data = config_data.get("include", {})
            if include_data:
                options_data.update(include_data)

            self.options = MigrationOptions(**options_data)

            self.logger.info(f"Configuration loaded from {config_path}")

        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {config_path}: {e}")

    def set_source(self, source: SourceConfig) -> None:
        """Set source project configuration."""
        self.source = source

    def set_target(self, target: TargetConfig) -> None:
        """Set target project configuration."""
        self.target = target

    def set_options(self, options: MigrationOptions) -> None:
        """Set migration options."""
        self.options = options

    def validate_configuration(self) -> None:
        """Validate current configuration."""
        if not self.source:
            raise ConfigurationError("Source configuration not set")
        if not self.target:
            raise ConfigurationError("Target configuration not set")

        # Test connections
        try:
            self._test_db_connection(self.source.db_url, "source")
            self._test_db_connection(self.target.db_url, "target")
        except Exception as e:
            raise ConfigurationError(f"Database connection test failed: {e}")

    def _test_db_connection(self, db_url: str, name: str) -> None:
        """Test database connection."""
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            self.logger.info(f"Database connection test passed for {name}")
        except Exception as e:
            raise ConfigurationError(f"Failed to connect to {name} database: {e}")

    async def migrate(self) -> MigrationResult:
        """Execute the migration process."""
        start_time = datetime.now()

        try:
            self.validate_configuration()

            # Create temporary directory for operation
            self.temp_dir = tempfile.mkdtemp(prefix="supamerge_")
            self.logger.info(f"Using temporary directory: {self.temp_dir}")

            # Step 1: Backup target if requested
            backup_files = []
            if self.options.backup_target_first:
                backup_file = await self._backup_target()
                backup_files.append(backup_file)

            if self.options.dry_run:
                self.logger.info("Dry run mode - no actual changes will be made")
                return MigrationResult(
                    success=True,
                    message="Dry run completed successfully",
                    backup_files=backup_files,
                    execution_time=(datetime.now() - start_time).total_seconds(),
                )

            # Step 2: Dump source schema and data
            dump_file = await self._dump_source()

            # Step 3: Analyze and prepare migration
            conflicts = await self._analyze_conflicts(dump_file)

            # Step 4: Apply schema changes
            await self._migrate_schema(dump_file)

            # Step 5: Migrate data
            if self.options.include_data:
                await self._migrate_data(dump_file)

            # Step 6: Migrate storage if requested
            skipped_items = []
            if self.options.include_storage:
                storage_result = await self._migrate_storage()
                skipped_items.extend(storage_result)

            # Step 7: Migrate policies if requested
            if self.options.include_policies:
                policy_result = await self._migrate_policies()
                skipped_items.extend(policy_result)

            execution_time = (datetime.now() - start_time).total_seconds()

            return MigrationResult(
                success=True,
                message="Migration completed successfully",
                backup_files=backup_files,
                conflicts=conflicts,
                skipped_items=skipped_items,
                execution_time=execution_time,
                log_file=self.logger.handlers[0].baseFilename
                if self.logger.handlers
                else None,
            )

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()
            return MigrationResult(
                success=False,
                message=f"Migration failed: {e}",
                execution_time=execution_time,
            )
        finally:
            # Cleanup temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil

                shutil.rmtree(self.temp_dir)

    async def _backup_target(self) -> str:
        """Create backup of target database."""
        self.logger.info("Creating backup of target database...")
        backup_file = os.path.join(
            self.temp_dir,
            f"target_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dump",
        )

        cmd = [
            "pg_dump",
            self.target.db_url,
            "--no-owner",
            "--no-privileges",
            "--format=custom",
            "-f",
            backup_file,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise MigrationError(f"Backup failed: {result.stderr}")

        self.logger.info(f"Target backup created: {backup_file}")
        return backup_file

    async def _dump_source(self) -> str:
        """Dump source database schema and data."""
        self.logger.info("Dumping source database...")
        dump_file = os.path.join(
            self.temp_dir,
            f"source_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dump",
        )

        cmd = [
            "pg_dump",
            self.source.db_url,
            "--no-owner",
            "--no-privileges",
            "--format=custom",
        ]

        # Add schema filters if specified
        if self.options.schemas and self.options.schemas != ["public"]:
            for schema in self.options.schemas:
                cmd.extend(["--schema", schema])

        cmd.extend(["-f", dump_file])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise MigrationError(f"Source dump failed: {result.stderr}")

        self.logger.info(f"Source dump created: {dump_file}")
        return dump_file

    async def _analyze_conflicts(self, dump_file: str) -> List[str]:
        """Analyze potential conflicts in the migration."""
        self.logger.info("Analyzing potential conflicts...")
        conflicts = []

        # Get list of tables from dump
        cmd = ["pg_restore", "--list", dump_file]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Parse the list output to find table names
            lines = result.stdout.split("\n")
            source_tables = set()
            for line in lines:
                if "TABLE DATA" in line or "TABLE " in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        table_name = parts[-1]
                        source_tables.add(table_name)

            # Check for existing tables in target
            try:
                conn = psycopg2.connect(self.target.db_url)
                cur = conn.cursor()

                for schema in self.options.schemas:
                    cur.execute(
                        """
                        SELECT table_name FROM information_schema.tables
                        WHERE table_schema = %s AND table_type = 'BASE TABLE'
                    """,
                        (schema,),
                    )

                    target_tables = {row[0] for row in cur.fetchall()}

                    # Find conflicts
                    conflicting_tables = source_tables.intersection(target_tables)
                    for table in conflicting_tables:
                        conflicts.append(
                            f"Table '{table}' exists in both source and target"
                        )

                conn.close()

            except Exception as e:
                self.logger.warning(f"Could not analyze table conflicts: {e}")

        self.logger.info(f"Found {len(conflicts)} potential conflicts")
        return conflicts

    async def _migrate_schema(self, dump_file: str) -> None:
        """Migrate database schema."""
        self.logger.info("Migrating database schema...")

        cmd = [
            "pg_restore",
            "--no-owner",
            "--no-privileges",
            "--schema-only",
            "--dbname",
            self.target.db_url,
            dump_file,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 and "already exists" not in result.stderr:
            self.logger.warning(f"Schema migration warnings: {result.stderr}")

        self.logger.info("Schema migration completed")

    async def _migrate_data(self, dump_file: str) -> None:
        """Migrate database data."""
        self.logger.info("Migrating database data...")

        cmd = [
            "pg_restore",
            "--no-owner",
            "--no-privileges",
            "--data-only",
            "--dbname",
            self.target.db_url,
            dump_file,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.logger.warning(f"Data migration warnings: {result.stderr}")

        self.logger.info("Data migration completed")

    async def _migrate_storage(self) -> List[str]:
        """Migrate Supabase storage buckets and files."""
        self.logger.info("Migrating Supabase storage...")
        skipped_items = []

        try:
            from supabase import create_client

            source_client = create_client(
                self.source.supabase_url, self.source.service_role_key
            )
            target_client = create_client(
                self.target.supabase_url, self.target.service_role_key
            )

            # Get source buckets
            buckets_response = source_client.storage.list_buckets()

            if hasattr(buckets_response, "data") and buckets_response.data:
                for bucket in buckets_response.data:
                    bucket_name = bucket.name
                    self.logger.info(f"Processing bucket: {bucket_name}")

                    # Create bucket in target if it doesn't exist
                    try:
                        target_client.storage.create_bucket(
                            bucket_name, {"public": bucket.public}
                        )
                    except Exception as e:
                        if "already exists" not in str(e):
                            self.logger.warning(
                                f"Could not create bucket {bucket_name}: {e}"
                            )

                    # List and copy files
                    try:
                        files_response = source_client.storage.from_(bucket_name).list()
                        if hasattr(files_response, "data") and files_response.data:
                            for file_obj in files_response.data:
                                file_name = file_obj.name
                                try:
                                    # Download from source
                                    file_data = source_client.storage.from_(
                                        bucket_name
                                    ).download(file_name)
                                    # Upload to target
                                    target_client.storage.from_(bucket_name).upload(
                                        file_name, file_data
                                    )
                                    self.logger.info(
                                        f"Copied file: {bucket_name}/{file_name}"
                                    )
                                except Exception as e:
                                    skipped_items.append(
                                        f"File {bucket_name}/{file_name}: {e}"
                                    )
                    except Exception as e:
                        skipped_items.append(f"Bucket {bucket_name} files: {e}")

        except Exception as e:
            self.logger.warning(f"Storage migration failed: {e}")
            skipped_items.append(f"Storage migration: {e}")

        self.logger.info("Storage migration completed")
        return skipped_items

    async def _migrate_policies(self) -> List[str]:
        """Migrate Row Level Security policies."""
        self.logger.info("Migrating RLS policies...")
        skipped_items = []

        try:
            # Connect to source database
            source_conn = psycopg2.connect(self.source.db_url)
            target_conn = psycopg2.connect(self.target.db_url)

            source_cur = source_conn.cursor()
            target_cur = target_conn.cursor()

            # Query policies from source
            for schema in self.options.schemas:
                source_cur.execute(
                    """
                    SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
                    FROM pg_policies
                    WHERE schemaname = %s
                """,
                    (schema,),
                )

                policies = source_cur.fetchall()

                for policy in policies:
                    (
                        schema_name,
                        table_name,
                        policy_name,
                        permissive,
                        roles,
                        cmd,
                        qual,
                        with_check,
                    ) = policy

                    try:
                        # Drop existing policy if it exists
                        target_cur.execute(
                            sql.SQL("DROP POLICY IF EXISTS {} ON {}.{}").format(
                                sql.Identifier(policy_name),
                                sql.Identifier(schema_name),
                                sql.Identifier(table_name),
                            )
                        )

                        # Create policy
                        policy_sql = sql.SQL(
                            "CREATE POLICY {} ON {}.{} FOR {} TO {}"
                        ).format(
                            sql.Identifier(policy_name),
                            sql.Identifier(schema_name),
                            sql.Identifier(table_name),
                            sql.SQL(cmd),
                            sql.SQL(",".join(roles) if roles else "public"),
                        )

                        if qual:
                            policy_sql = sql.SQL("{} USING ({})").format(
                                policy_sql, sql.SQL(qual)
                            )

                        if with_check:
                            policy_sql = sql.SQL("{} WITH CHECK ({})").format(
                                policy_sql, sql.SQL(with_check)
                            )

                        target_cur.execute(policy_sql)
                        self.logger.info(
                            f"Migrated policy: {schema_name}.{table_name}.{policy_name}"
                        )

                    except Exception as e:
                        skipped_items.append(
                            f"Policy {schema_name}.{table_name}.{policy_name}: {e}"
                        )

            target_conn.commit()
            source_conn.close()
            target_conn.close()

        except Exception as e:
            self.logger.warning(f"Policy migration failed: {e}")
            skipped_items.append(f"Policy migration: {e}")

        self.logger.info("Policy migration completed")
        return skipped_items

    def generate_manifest(self, output_path: str) -> None:
        """Generate a migration manifest file."""
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "source": asdict(self.source) if self.source else None,
            "target": asdict(self.target) if self.target else None,
            "options": asdict(self.options),
        }

        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)

        self.logger.info(f"Migration manifest saved to: {output_path}")
