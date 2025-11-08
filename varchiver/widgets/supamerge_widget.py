"""Widget for Supamerge - Supabase project migration tool."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QGroupBox,
    QFileDialog,
    QComboBox,
    QMessageBox,
    QProgressDialog,
    QTextEdit,
    QCheckBox,
    QFormLayout,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QFrame,
    QScrollArea,
    QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor
import asyncio
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

from ..supamerge.core import (
    Supamerge,
    SourceConfig,
    TargetConfig,
    MigrationOptions,
    MigrationResult,
    SupamergeError,
)
from ..supamerge.config import SupamergeConfig
from ..utils.config import Config
from ..widgets.supabase_config_dialog import SupabaseConfigDialog


class MigrationWorker(QThread):
    """Worker thread for running migrations without blocking UI."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(object)  # MigrationResult
    error = pyqtSignal(str)

    def __init__(self, supamerge_instance: Supamerge):
        super().__init__()
        self.supamerge = supamerge_instance

    def run(self):
        """Run the migration in a separate thread."""
        try:
            # Run async migration in thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.supamerge.migrate())
            loop.close()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SupamergeWidget(QWidget):
    """Main widget for Supamerge functionality."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.supamerge_config = SupamergeConfig()
        self.supamerge = Supamerge()
        self.migration_worker: Optional[MigrationWorker] = None

        self.setup_ui()
        self.load_supabase_connections()

    def setup_ui(self):
        """Initialize the UI components."""
        main_layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Supamerge - Supabase Project Migration")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Create tabbed interface
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Configuration Tab
        self.setup_config_tab()

        # Quick Actions Tab
        self.setup_quick_actions_tab()

        # Migration Tab
        self.setup_migration_tab()

        # Results Tab
        self.setup_results_tab()

    def setup_config_tab(self):
        """Setup the configuration tab."""
        config_widget = QWidget()
        layout = QVBoxLayout(config_widget)

        # Quick Setup Section
        quick_setup_group = QGroupBox("Quick Setup")
        quick_layout = QVBoxLayout(quick_setup_group)

        # Load from existing connections
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("Use Existing Connections:"))

        self.source_conn_combo = QComboBox()
        self.source_conn_combo.currentTextChanged.connect(
            self.on_source_connection_changed
        )
        conn_layout.addWidget(QLabel("Source:"))
        conn_layout.addWidget(self.source_conn_combo)

        self.target_conn_combo = QComboBox()
        self.target_conn_combo.currentTextChanged.connect(
            self.on_target_connection_changed
        )
        conn_layout.addWidget(QLabel("Target:"))
        conn_layout.addWidget(self.target_conn_combo)

        manage_conn_btn = QPushButton("Manage Connections...")
        manage_conn_btn.clicked.connect(self.show_connection_manager)
        conn_layout.addWidget(manage_conn_btn)

        refresh_conn_btn = QPushButton("🔄 Refresh")
        refresh_conn_btn.clicked.connect(self.load_supabase_connections)
        conn_layout.addWidget(refresh_conn_btn)

        quick_layout.addLayout(conn_layout)

        # Connection status
        self.connection_status_label = QLabel("Click refresh to load connections")
        self.connection_status_label.setStyleSheet(
            "font-size: 11px; color: #666; font-style: italic;"
        )
        quick_layout.addWidget(self.connection_status_label)

        layout.addWidget(quick_setup_group)

        # Configuration File Section
        config_file_group = QGroupBox("Configuration File")
        config_file_layout = QVBoxLayout(config_file_group)

        # Load/Save config
        config_buttons_layout = QHBoxLayout()
        load_config_btn = QPushButton("Load Config...")
        load_config_btn.clicked.connect(self.load_config_file)
        config_buttons_layout.addWidget(load_config_btn)

        save_config_btn = QPushButton("Save Config...")
        save_config_btn.clicked.connect(self.save_config_file)
        config_buttons_layout.addWidget(save_config_btn)

        create_template_btn = QPushButton("Create Template...")
        create_template_btn.clicked.connect(self.create_config_template)
        config_buttons_layout.addWidget(create_template_btn)

        config_file_layout.addLayout(config_buttons_layout)

        # Config file path
        self.config_path_label = QLabel("No configuration file loaded")
        self.config_path_label.setStyleSheet("font-style: italic; color: grey;")
        config_file_layout.addWidget(self.config_path_label)

        layout.addWidget(config_file_group)

        # Migration Options
        options_group = QGroupBox("Migration Options")
        options_layout = QFormLayout(options_group)

        self.backup_target_cb = QCheckBox("Backup target database first")
        self.backup_target_cb.setChecked(True)
        options_layout.addRow(self.backup_target_cb)

        self.include_data_cb = QCheckBox("Include table data")
        self.include_data_cb.setChecked(True)
        options_layout.addRow(self.include_data_cb)

        self.include_storage_cb = QCheckBox("Include storage buckets")
        self.include_storage_cb.setChecked(True)
        options_layout.addRow(self.include_storage_cb)

        self.include_policies_cb = QCheckBox("Include RLS policies")
        self.include_policies_cb.setChecked(True)
        options_layout.addRow(self.include_policies_cb)

        self.remap_conflicts_cb = QCheckBox("Remap conflicting table names")
        self.remap_conflicts_cb.setChecked(True)
        options_layout.addRow(self.remap_conflicts_cb)

        # Dry run should be prominently displayed and default
        dry_run_label = QLabel("⚠️ Safety Mode:")
        dry_run_label.setStyleSheet("font-weight: bold; color: #d32f2f;")
        self.dry_run_cb = QCheckBox("Dry run (preview only) - RECOMMENDED")
        self.dry_run_cb.setChecked(True)  # Default to dry run for safety
        self.dry_run_cb.setStyleSheet("font-weight: bold;")
        options_layout.addRow(dry_run_label, self.dry_run_cb)

        # Schema selection
        self.schemas_edit = QLineEdit("public")
        options_layout.addRow("Schemas (comma-separated):", self.schemas_edit)

        layout.addWidget(options_group)

        # Validation Section
        validation_group = QGroupBox("Configuration Validation")
        validation_layout = QVBoxLayout(validation_group)

        validate_btn = QPushButton("Validate Configuration")
        validate_btn.clicked.connect(self.validate_configuration)
        validation_layout.addWidget(validate_btn)

        self.validation_text = QTextEdit()
        self.validation_text.setMaximumHeight(100)
        self.validation_text.setReadOnly(True)
        validation_layout.addWidget(self.validation_text)

        layout.addWidget(validation_group)

        self.tabs.addTab(config_widget, "Configuration")

    def setup_quick_actions_tab(self):
        """Setup the quick actions tab with simple backup/dump buttons."""
        actions_widget = QWidget()
        layout = QVBoxLayout(actions_widget)

        # Title
        title = QLabel("Quick Database Actions")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # Source selection for quick actions
        source_group = QGroupBox("Select Source Database")
        source_layout = QVBoxLayout(source_group)

        source_conn_layout = QHBoxLayout()
        source_conn_layout.addWidget(QLabel("Connection:"))
        self.quick_source_combo = QComboBox()
        source_conn_layout.addWidget(self.quick_source_combo)
        source_layout.addLayout(source_conn_layout)

        layout.addWidget(source_group)

        # Quick action buttons
        actions_group = QGroupBox("Available Actions")
        actions_layout = QVBoxLayout(actions_group)

        # Backup/Dump buttons
        dump_schema_btn = QPushButton("🗄️ Dump Schema Only")
        dump_schema_btn.setMinimumHeight(40)
        dump_schema_btn.clicked.connect(self.dump_schema_only)
        actions_layout.addWidget(dump_schema_btn)

        dump_data_btn = QPushButton("💾 Dump Schema + Data")
        dump_data_btn.setMinimumHeight(40)
        dump_data_btn.clicked.connect(self.dump_schema_and_data)
        actions_layout.addWidget(dump_data_btn)

        backup_storage_btn = QPushButton("📁 Backup Storage Files")
        backup_storage_btn.setMinimumHeight(40)
        backup_storage_btn.clicked.connect(self.backup_storage_files)
        actions_layout.addWidget(backup_storage_btn)

        full_backup_btn = QPushButton("🎯 Full Project Backup")
        full_backup_btn.setMinimumHeight(40)
        full_backup_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )
        full_backup_btn.clicked.connect(self.full_project_backup)
        actions_layout.addWidget(full_backup_btn)

        layout.addWidget(actions_group)

        # Status area for quick actions
        self.quick_status = QTextEdit()
        self.quick_status.setMaximumHeight(150)
        self.quick_status.setPlaceholderText("Action results will appear here...")
        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.quick_status)

        layout.addStretch()
        self.tabs.addTab(actions_widget, "Quick Actions")

    def setup_migration_tab(self):
        """Setup the migration execution tab."""
        migration_widget = QWidget()
        layout = QVBoxLayout(migration_widget)

        # Migration Status
        status_group = QGroupBox("Migration Status")
        status_layout = QVBoxLayout(status_group)

        self.status_label = QLabel("Ready to migrate")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.status_label)

        # Progress area
        self.progress_text = QTextEdit()
        self.progress_text.setMaximumHeight(200)
        self.progress_text.setReadOnly(True)
        status_layout.addWidget(self.progress_text)

        layout.addWidget(status_group)

        # Migration Controls
        controls_group = QGroupBox("Migration Controls")
        controls_layout = QHBoxLayout(controls_group)

        self.start_migration_btn = QPushButton("Start Migration")
        self.start_migration_btn.clicked.connect(self.start_migration)
        self.start_migration_btn.setEnabled(False)  # Disabled until connections are set
        self.start_migration_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }"
        )
        controls_layout.addWidget(self.start_migration_btn)

        self.cancel_migration_btn = QPushButton("Cancel")
        self.cancel_migration_btn.clicked.connect(self.cancel_migration)
        self.cancel_migration_btn.setEnabled(False)
        controls_layout.addWidget(self.cancel_migration_btn)

        controls_layout.addStretch()

        layout.addWidget(controls_group)

        # Add stretch to push everything to the top
        layout.addStretch()

        self.tabs.addTab(migration_widget, "Migration")

    def setup_results_tab(self):
        """Setup the results and logs tab."""
        results_widget = QWidget()
        layout = QVBoxLayout(results_widget)

        # Results Summary
        summary_group = QGroupBox("Migration Results")
        summary_layout = QVBoxLayout(summary_group)

        self.results_summary = QTextEdit()
        self.results_summary.setMaximumHeight(150)
        self.results_summary.setReadOnly(True)
        summary_layout.addWidget(self.results_summary)

        layout.addWidget(summary_group)

        # Detailed Results
        details_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Conflicts and Issues
        conflicts_group = QGroupBox("Conflicts & Issues")
        conflicts_layout = QVBoxLayout(conflicts_group)

        self.conflicts_list = QListWidget()
        conflicts_layout.addWidget(self.conflicts_list)

        details_splitter.addWidget(conflicts_group)

        # Backup Files
        backups_group = QGroupBox("Backup Files")
        backups_layout = QVBoxLayout(backups_group)

        self.backups_list = QListWidget()
        backups_layout.addWidget(self.backups_list)

        open_backups_btn = QPushButton("Open Backups Folder")
        open_backups_btn.clicked.connect(self.open_backups_folder)
        backups_layout.addWidget(open_backups_btn)

        details_splitter.addWidget(backups_group)

        layout.addWidget(details_splitter)

        # Full Log
        log_group = QGroupBox("Full Migration Log")
        log_layout = QVBoxLayout(log_group)

        self.full_log_text = QTextEdit()
        self.full_log_text.setReadOnly(True)
        log_layout.addWidget(self.full_log_text)

        log_buttons_layout = QHBoxLayout()
        save_log_btn = QPushButton("Save Log...")
        save_log_btn.clicked.connect(self.save_log)
        log_buttons_layout.addWidget(save_log_btn)

        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.clear_log)
        log_buttons_layout.addWidget(clear_log_btn)

        log_buttons_layout.addStretch()
        log_layout.addLayout(log_buttons_layout)

        layout.addWidget(log_group)

        self.tabs.addTab(results_widget, "Results")

    def load_supabase_connections(self):
        """Load available Supabase connections into the combo boxes."""
        # Force reload from config to get latest data
        self.config = Config()
        connections = self.config.get_supabase_connections()

        # Clear existing items
        self.source_conn_combo.clear()
        self.target_conn_combo.clear()
        if hasattr(self, "quick_source_combo"):
            self.quick_source_combo.clear()

        self.source_conn_combo.addItem("-- Select Connection --", None)
        self.target_conn_combo.addItem("-- Select Connection --", None)
        if hasattr(self, "quick_source_combo"):
            self.quick_source_combo.addItem("-- Select Connection --", None)

        for conn in connections:
            name = conn.get("name", "Unnamed")
            # Only add connections that have the required fields
            has_required = (
                conn.get("url")
                and (conn.get("service_role_key") or conn.get("secret_key"))
                and (conn.get("anon_key") or conn.get("publishable_key"))
            )
            if has_required:
                self.source_conn_combo.addItem(name, conn)
                self.target_conn_combo.addItem(name, conn)
                if hasattr(self, "quick_source_combo"):
                    self.quick_source_combo.addItem(name, conn)

        # Update status label
        valid_connections = [
            c
            for c in connections
            if (
                c.get("url")
                and (c.get("service_role_key") or c.get("secret_key"))
                and (c.get("anon_key") or c.get("publishable_key"))
            )
        ]
        status_text = f"Loaded {len(connections)} total connections, {len(valid_connections)} valid"
        if hasattr(self, "connection_status_label"):
            self.connection_status_label.setText(status_text)

        # Log connection details for debugging
        self.log_message(status_text)
        for conn in connections:
            name = conn.get("name", "Unnamed")
            has_url = bool(conn.get("url"))
            has_service_key = bool(
                conn.get("service_role_key") or conn.get("secret_key")
            )
            has_anon_key = bool(conn.get("anon_key") or conn.get("publishable_key"))
            self.log_message(
                f"  - {name}: URL={has_url}, ServiceKey={has_service_key}, AnonKey={has_anon_key}"
            )

    def on_source_connection_changed(self, connection_name: str):
        """Handle source connection selection."""
        if connection_name != "-- Select Connection --":
            conn_data = self.source_conn_combo.currentData()
            if conn_data:
                self.update_supamerge_source(conn_data)
                self.validate_connection_button_state()

    def on_target_connection_changed(self, connection_name: str):
        """Handle target connection selection."""
        if connection_name != "-- Select Connection --":
            conn_data = self.target_conn_combo.currentData()
            if conn_data:
                self.update_supamerge_target(conn_data)
                self.validate_connection_button_state()

    def update_supamerge_source(self, conn_data: Dict[str, Any]):
        """Update supamerge with source configuration."""
        try:
            url = conn_data.get("url", "")
            # Handle both new (sb_) and legacy (JWT) key formats
            anon_key = conn_data.get("anon_key", "") or conn_data.get(
                "publishable_key", ""
            )
            service_key = conn_data.get("service_role_key", "") or conn_data.get(
                "secret_key", ""
            )

            if not all([url, anon_key, service_key]):
                self.validation_text.setPlainText(
                    "⚠️ Source connection missing required fields.\n"
                    + "Please check URL, anon key, and service role key."
                )
                self.validation_text.setStyleSheet("color: orange;")
                return

            # Construct database URL from Supabase URL and service key
            project_ref = self.extract_project_ref(url)
            # Use the direct database connection format
            db_url = f"postgresql://postgres:{service_key}@db.{project_ref}.supabase.co:5432/postgres"

            source_config = SourceConfig(
                project_ref=project_ref,
                db_url=db_url,
                supabase_url=url,
                anon_key=anon_key,
                service_role_key=service_key,
            )
            self.supamerge.set_source(source_config)
            self.log_message(f"Source configured: {conn_data.get('name', 'Unknown')}")
            self.validation_text.setPlainText(
                "✓ Source connection configured successfully"
            )
            self.validation_text.setStyleSheet("color: green;")
        except Exception as e:
            self.log_message(f"Error setting source: {e}")
            self.validation_text.setPlainText(f"✗ Error configuring source: {e}")
            self.validation_text.setStyleSheet("color: red;")

    def update_supamerge_target(self, conn_data: Dict[str, Any]):
        """Update supamerge with target configuration."""
        try:
            url = conn_data.get("url", "")
            # Handle both new (sb_) and legacy (JWT) key formats
            anon_key = conn_data.get("anon_key", "") or conn_data.get(
                "publishable_key", ""
            )
            service_key = conn_data.get("service_role_key", "") or conn_data.get(
                "secret_key", ""
            )

            if not all([url, anon_key, service_key]):
                self.validation_text.setPlainText(
                    "⚠️ Target connection missing required fields.\n"
                    + "Please check URL, anon key, and service role key."
                )
                self.validation_text.setStyleSheet("color: orange;")
                return

            # Construct database URL from Supabase URL and service key
            project_ref = self.extract_project_ref(url)
            # Use the direct database connection format
            db_url = f"postgresql://postgres:{service_key}@db.{project_ref}.supabase.co:5432/postgres"

            target_config = TargetConfig(
                project_ref=project_ref,
                db_url=db_url,
                supabase_url=url,
                anon_key=anon_key,
                service_role_key=service_key,
            )
            self.supamerge.set_target(target_config)
            self.log_message(f"Target configured: {conn_data.get('name', 'Unknown')}")
            self.validation_text.setPlainText(
                "✓ Target connection configured successfully"
            )
            self.validation_text.setStyleSheet("color: green;")
        except Exception as e:
            self.log_message(f"Error setting target: {e}")
            self.validation_text.setPlainText(f"✗ Error configuring target: {e}")
            self.validation_text.setStyleSheet("color: red;")

    def extract_project_ref(self, supabase_url: str) -> str:
        """Extract project reference from Supabase URL."""
        if supabase_url:
            return supabase_url.replace("https://", "").replace(".supabase.co", "")
        return ""

    def validate_connection_button_state(self):
        """Update UI based on connection state."""
        has_source = self.source_conn_combo.currentData() is not None
        has_target = self.target_conn_combo.currentData() is not None

        # Enable migration button only if both connections are set
        self.start_migration_btn.setEnabled(has_source and has_target)

    def show_connection_manager(self):
        """Show the Supabase connection manager dialog."""
        dialog = SupabaseConfigDialog(self)
        dialog.profiles_changed.connect(self.on_profiles_changed)
        if dialog.exec() == dialog.DialogCode.Accepted:
            # Reload connections and refresh all combo boxes
            self.log_message("Connection dialog closed, refreshing connection list...")
            self.load_supabase_connections()
            self.validate_connection_button_state()

            # Force refresh of the parent widget if it exists
            if hasattr(self.parent(), "refresh_active_connection_status"):
                self.parent().refresh_active_connection_status()

            self.log_message("Connection list refreshed after dialog close")

    def on_profiles_changed(self):
        """Handle profiles changed signal from config dialog."""
        # Refresh the supabase connector to pick up changes
        from ..utils.supabase_connector import refresh_supabase_connection

        self.log_message("Profiles changed, refreshing connection...")
        refresh_supabase_connection()
        self.load_supabase_connections()
        self.validate_connection_button_state()

    def test_database_connection(self, conn_data):
        """Test database connectivity before performing backup operations."""
        try:
            import psycopg2
            import psycopg2.extras

            project_ref = self.extract_project_ref(conn_data.get("url", ""))
            service_key = conn_data.get("service_role_key", "") or conn_data.get(
                "secret_key", ""
            )

            # Try direct connection format first
            db_url = f"postgresql://postgres:{service_key}@db.{project_ref}.supabase.co:5432/postgres"

            self.quick_status.append("🔍 Testing database connection...")

            # Test connection
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            self.quick_status.append(f"✅ Database connection successful")
            self.quick_status.append(f"   PostgreSQL: {version.split()[1]}")
            return True

        except psycopg2.OperationalError as e:
            error_str = str(e)
            if "Tenant or user not found" in error_str:
                # Try pooler connection format
                try:
                    pooler_url = f"postgresql://postgres.{project_ref}:{service_key}@aws-0-us-west-1.pooler.supabase.com:5432/postgres"
                    conn = psycopg2.connect(pooler_url)
                    cursor = conn.cursor()
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()[0]
                    cursor.close()
                    conn.close()

                    self.quick_status.append(
                        f"✅ Database connection successful (via pooler)"
                    )
                    return True
                except Exception as pooler_error:
                    self.quick_status.append(
                        f"❌ Database connection failed: {pooler_error}"
                    )
                    return False
            else:
                self.quick_status.append(f"❌ Database connection failed: {error_str}")
                return False
        except Exception as e:
            self.quick_status.append(f"❌ Database connection error: {str(e)}")
            return False

    def dump_schema_only(self):
        """Dump database schema to local file."""
        conn_data = self.quick_source_combo.currentData()
        if not conn_data:
            self.quick_status.append("❌ Please select a connection first")
            return

        # Test connection first
        if not self.test_database_connection(conn_data):
            return

        try:
            from PyQt6.QtWidgets import QFileDialog
            import subprocess
            import os
            from datetime import datetime

            # Get save location
            default_name = f"{conn_data.get('name', 'database')}_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Schema Dump", default_name, "SQL files (*.sql)"
            )

            if not file_path:
                return

            # Construct database URL
            project_ref = self.extract_project_ref(conn_data.get("url", ""))
            service_key = conn_data.get("service_role_key", "") or conn_data.get(
                "secret_key", ""
            )
            db_url = f"postgresql://postgres:{service_key}@db.{project_ref}.supabase.co:5432/postgres"

            self.quick_status.append(
                f"🔄 Dumping schema to {os.path.basename(file_path)}..."
            )

            # Use pg_dump to get schema only
            result = subprocess.run(
                [
                    "pg_dump",
                    db_url,
                    "--schema-only",
                    "--no-owner",
                    "--no-privileges",
                    "--file",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                self.quick_status.append(
                    f"✅ Schema dumped successfully to {file_path}"
                )
            else:
                self.quick_status.append(f"❌ Schema dump failed: {result.stderr}")

        except Exception as e:
            self.quick_status.append(f"❌ Error dumping schema: {str(e)}")

    def dump_schema_and_data(self):
        """Dump database schema and data to local file."""
        conn_data = self.quick_source_combo.currentData()
        if not conn_data:
            self.quick_status.append("❌ Please select a connection first")
            return

        # Test connection first
        if not self.test_database_connection(conn_data):
            return

        try:
            from PyQt6.QtWidgets import QFileDialog
            import subprocess
            import os
            from datetime import datetime

            # Get save location
            default_name = f"{conn_data.get('name', 'database')}_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Full Dump", default_name, "SQL files (*.sql)"
            )

            if not file_path:
                return

            # Construct database URL
            project_ref = self.extract_project_ref(conn_data.get("url", ""))
            service_key = conn_data.get("service_role_key", "") or conn_data.get(
                "secret_key", ""
            )
            db_url = f"postgresql://postgres:{service_key}@db.{project_ref}.supabase.co:5432/postgres"

            self.quick_status.append(
                f"🔄 Dumping schema and data to {os.path.basename(file_path)}..."
            )

            # Use pg_dump to get full dump
            result = subprocess.run(
                [
                    "pg_dump",
                    db_url,
                    "--no-owner",
                    "--no-privileges",
                    "--file",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode == 0:
                self.quick_status.append(
                    f"✅ Full dump completed successfully to {file_path}"
                )
            else:
                self.quick_status.append(f"❌ Full dump failed: {result.stderr}")

        except Exception as e:
            self.quick_status.append(f"❌ Error dumping data: {str(e)}")

    def backup_storage_files(self):
        """Backup Supabase storage files to local directory."""
        conn_data = self.quick_source_combo.currentData()
        if not conn_data:
            self.quick_status.append("❌ Please select a connection first")
            return

        try:
            from PyQt6.QtWidgets import QFileDialog
            import os
            from datetime import datetime
            from ..utils.supabase_connector import SupabaseConnector

            # Get save location
            backup_dir = QFileDialog.getExistingDirectory(
                self, "Select Backup Directory"
            )

            if not backup_dir:
                return

            # Create timestamped subdirectory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = conn_data.get("name", "project")
            storage_backup_dir = os.path.join(
                backup_dir, f"{project_name}_storage_{timestamp}"
            )
            os.makedirs(storage_backup_dir, exist_ok=True)

            self.quick_status.append(
                f"🔄 Backing up storage files to {storage_backup_dir}..."
            )

            # Use Supabase client to download files
            connector = SupabaseConnector()
            # Set temporary active connection
            original_active = self.config.get_active_supabase_connection_name()
            self.config.set_active_supabase_connection_name(conn_data.get("name"))

            client = connector.get_service_client()
            if not client:
                self.quick_status.append("❌ Failed to create Supabase client")
                return

            # List all buckets
            buckets = client.storage.list_buckets()
            total_files = 0

            for bucket in buckets:
                bucket_name = bucket["name"]
                bucket_dir = os.path.join(storage_backup_dir, bucket_name)
                os.makedirs(bucket_dir, exist_ok=True)

                self.quick_status.append(f"📁 Processing bucket: {bucket_name}")

                # List files in bucket
                try:
                    files = client.storage.from_(bucket_name).list()
                    for file_obj in files:
                        file_name = file_obj["name"]
                        file_path = os.path.join(bucket_dir, file_name)

                        # Download file
                        file_data = client.storage.from_(bucket_name).download(
                            file_name
                        )
                        with open(file_path, "wb") as f:
                            f.write(file_data)
                        total_files += 1

                except Exception as bucket_error:
                    self.quick_status.append(
                        f"⚠️ Error with bucket {bucket_name}: {str(bucket_error)}"
                    )

            # Restore original active connection
            self.config.set_active_supabase_connection_name(original_active)

            self.quick_status.append(
                f"✅ Storage backup completed: {total_files} files backed up to {storage_backup_dir}"
            )

        except Exception as e:
            self.quick_status.append(f"❌ Error backing up storage: {str(e)}")

    def full_project_backup(self):
        """Perform a complete project backup including schema, data, and storage."""
        conn_data = self.quick_source_combo.currentData()
        if not conn_data:
            self.quick_status.append("❌ Please select a connection first")
            return

        try:
            from PyQt6.QtWidgets import QFileDialog
            import os
            from datetime import datetime

            # Get save location
            backup_dir = QFileDialog.getExistingDirectory(
                self, "Select Full Backup Directory"
            )

            if not backup_dir:
                return

            # Create timestamped backup directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = conn_data.get("name", "project")
            full_backup_dir = os.path.join(
                backup_dir, f"{project_name}_full_backup_{timestamp}"
            )
            os.makedirs(full_backup_dir, exist_ok=True)

            self.quick_status.append(
                f"🎯 Starting full project backup to {full_backup_dir}..."
            )

            # 1. Backup database schema and data
            self.quick_status.append("1️⃣ Backing up database...")
            import subprocess

            project_ref = self.extract_project_ref(conn_data.get("url", ""))
            service_key = conn_data.get("service_role_key", "") or conn_data.get(
                "secret_key", ""
            )
            db_url = f"postgresql://postgres:{service_key}@db.{project_ref}.supabase.co:5432/postgres"

            db_backup_path = os.path.join(full_backup_dir, "database_full.sql")
            result = subprocess.run(
                [
                    "pg_dump",
                    db_url,
                    "--no-owner",
                    "--no-privileges",
                    "--file",
                    db_backup_path,
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode == 0:
                self.quick_status.append("✅ Database backup completed")
            else:
                self.quick_status.append(
                    f"⚠️ Database backup had issues: {result.stderr}"
                )

            # 2. Backup storage files
            self.quick_status.append("2️⃣ Backing up storage files...")
            storage_dir = os.path.join(full_backup_dir, "storage")
            os.makedirs(storage_dir, exist_ok=True)

            from ..utils.supabase_connector import SupabaseConnector

            connector = SupabaseConnector()
            original_active = self.config.get_active_supabase_connection_name()
            self.config.set_active_supabase_connection_name(conn_data.get("name"))

            client = connector.get_service_client()
            if client:
                buckets = client.storage.list_buckets()
                total_files = 0

                for bucket in buckets:
                    bucket_name = bucket["name"]
                    bucket_dir = os.path.join(storage_dir, bucket_name)
                    os.makedirs(bucket_dir, exist_ok=True)

                    try:
                        files = client.storage.from_(bucket_name).list()
                        for file_obj in files:
                            file_name = file_obj["name"]
                            file_path = os.path.join(bucket_dir, file_name)

                            file_data = client.storage.from_(bucket_name).download(
                                file_name
                            )
                            with open(file_path, "wb") as f:
                                f.write(file_data)
                            total_files += 1

                    except Exception as bucket_error:
                        self.quick_status.append(
                            f"⚠️ Storage bucket {bucket_name}: {str(bucket_error)}"
                        )

                self.config.set_active_supabase_connection_name(original_active)
                self.quick_status.append(
                    f"✅ Storage backup completed: {total_files} files"
                )

            # 3. Create backup manifest
            manifest_path = os.path.join(full_backup_dir, "backup_manifest.txt")
            with open(manifest_path, "w") as f:
                f.write(f"Full Project Backup\n")
                f.write(f"Project: {conn_data.get('name')}\n")
                f.write(f"URL: {conn_data.get('url')}\n")
                f.write(f"Backup Date: {datetime.now().isoformat()}\n")
                f.write(f"Database: {db_backup_path}\n")
                f.write(f"Storage: {storage_dir}\n")
                f.write(f"\nNOTE: This backup uses standard PostgreSQL commands\n")
                f.write(f"and does not rely on custom RPC functions.\n")

            self.quick_status.append(f"🎉 Full project backup completed successfully!")
            self.quick_status.append(f"📁 Backup location: {full_backup_dir}")

        except Exception as e:
            self.quick_status.append(f"❌ Error during full backup: {str(e)}")

    def load_config_file(self):
        """Load migration configuration from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration", "", "YAML files (*.yaml *.yml);;All files (*)"
        )

        if file_path:
            try:
                self.supamerge.load_config(file_path)
                self.config_path_label.setText(f"Loaded: {os.path.basename(file_path)}")
                self.config_path_label.setStyleSheet("color: green;")
                self.log_message(f"Configuration loaded from {file_path}")

                # Update UI with loaded options
                self.update_ui_from_config()

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to load configuration:\n{e}"
                )

    def save_config_file(self):
        """Save current configuration to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration",
            "supamerge_config.yaml",
            "YAML files (*.yaml);;All files (*)",
        )

        if file_path:
            try:
                self.update_supamerge_from_ui()
                config_dict = self.build_config_dict()
                self.supamerge_config.save_config(config_dict, file_path)
                self.log_message(f"Configuration saved to {file_path}")
                QMessageBox.information(
                    self, "Success", "Configuration saved successfully!"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to save configuration:\n{e}"
                )

    def create_config_template(self):
        """Create a configuration template file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create Config Template",
            "supamerge_template.yaml",
            "YAML files (*.yaml);;All files (*)",
        )

        if file_path:
            try:
                self.supamerge_config.create_template_config(file_path)
                self.log_message(f"Template created at {file_path}")
                QMessageBox.information(
                    self,
                    "Success",
                    f"Configuration template created!\n\nEdit {file_path} with your project details, then load it back into Supamerge.",
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create template:\n{e}")

    def update_ui_from_config(self):
        """Update UI elements from loaded configuration."""
        if hasattr(self.supamerge, "options") and self.supamerge.options:
            options = self.supamerge.options
            self.backup_target_cb.setChecked(options.backup_target_first)
            self.include_data_cb.setChecked(options.include_data)
            self.include_storage_cb.setChecked(options.include_storage)
            self.include_policies_cb.setChecked(options.include_policies)
            self.remap_conflicts_cb.setChecked(options.remap_conflicts)
            self.dry_run_cb.setChecked(options.dry_run)

            if options.schemas:
                self.schemas_edit.setText(", ".join(options.schemas))

    def update_supamerge_from_ui(self):
        """Update supamerge configuration from UI elements."""
        schemas = [s.strip() for s in self.schemas_edit.text().split(",") if s.strip()]

        options = MigrationOptions(
            backup_target_first=self.backup_target_cb.isChecked(),
            include_data=self.include_data_cb.isChecked(),
            include_storage=self.include_storage_cb.isChecked(),
            include_policies=self.include_policies_cb.isChecked(),
            remap_conflicts=self.remap_conflicts_cb.isChecked(),
            dry_run=self.dry_run_cb.isChecked(),
            schemas=schemas if schemas else ["public"],
        )

        self.supamerge.set_options(options)

    def build_config_dict(self) -> Dict[str, Any]:
        """Build configuration dictionary from current supamerge state."""
        config_dict = self.supamerge_config.get_config_template()

        if self.supamerge.source:
            config_dict["source"] = {
                "project_ref": self.supamerge.source.project_ref,
                "db_url": self.supamerge.source.db_url,
                "supabase_url": self.supamerge.source.supabase_url,
                "anon_key": self.supamerge.source.anon_key,
                "service_role_key": self.supamerge.source.service_role_key,
            }

        if self.supamerge.target:
            config_dict["target"] = {
                "project_ref": self.supamerge.target.project_ref,
                "db_url": self.supamerge.target.db_url,
                "supabase_url": self.supamerge.target.supabase_url,
                "anon_key": self.supamerge.target.anon_key,
                "service_role_key": self.supamerge.target.service_role_key,
            }

        if self.supamerge.options:
            config_dict["options"] = {
                "backup_target_first": self.supamerge.options.backup_target_first,
                "remap_conflicts": self.supamerge.options.remap_conflicts,
                "skip_auth": self.supamerge.options.skip_auth,
                "dry_run": self.supamerge.options.dry_run,
            }

            config_dict["include"] = {
                "schemas": self.supamerge.options.schemas,
                "include_data": self.supamerge.options.include_data,
                "include_policies": self.supamerge.options.include_policies,
                "include_storage": self.supamerge.options.include_storage,
            }

        return config_dict

    def validate_configuration(self):
        """Validate the current configuration."""
        try:
            # Check if connections are selected
            if not self.source_conn_combo.currentData():
                self.validation_text.setPlainText(
                    "❌ Please select a source connection"
                )
                self.validation_text.setStyleSheet("color: red;")
                return

            if not self.target_conn_combo.currentData():
                self.validation_text.setPlainText(
                    "❌ Please select a target connection"
                )
                self.validation_text.setStyleSheet("color: red;")
                return

            self.update_supamerge_from_ui()
            self.supamerge.validate_configuration()

            self.validation_text.setPlainText("✅ Configuration is valid!")
            self.validation_text.setStyleSheet("color: green;")
            self.log_message("Configuration validation passed")

        except Exception as e:
            self.validation_text.setPlainText(f"❌ Configuration Error:\n{e}")
            self.validation_text.setStyleSheet("color: red;")
            self.log_message(f"Configuration validation failed: {e}")

    def start_migration(self):
        """Start the migration process."""
        try:
            self.update_supamerge_from_ui()
            self.supamerge.validate_configuration()
        except Exception as e:
            QMessageBox.critical(self, "Configuration Error", str(e))
            return

        # Confirm migration
        if not self.dry_run_cb.isChecked():
            reply = QMessageBox.question(
                self,
                "Confirm Migration",
                "This will modify the target database. Are you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        # Start migration in worker thread
        self.migration_worker = MigrationWorker(self.supamerge)
        self.migration_worker.progress.connect(self.on_migration_progress)
        self.migration_worker.finished.connect(self.on_migration_finished)
        self.migration_worker.error.connect(self.on_migration_error)

        # Update UI state
        self.start_migration_btn.setEnabled(False)
        self.cancel_migration_btn.setEnabled(True)
        self.status_label.setText("Migration in progress...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")

        # Switch to migration tab
        self.tabs.setCurrentIndex(1)

        # Start the worker
        self.migration_worker.start()

        self.log_message("Migration started...")

    def cancel_migration(self):
        """Cancel the ongoing migration."""
        if self.migration_worker and self.migration_worker.isRunning():
            self.migration_worker.terminate()
            self.migration_worker.wait(5000)  # Wait up to 5 seconds

        self.reset_migration_ui()
        self.log_message("Migration cancelled by user")

    def on_migration_progress(self, message: str):
        """Handle migration progress updates."""
        self.log_message(message)

    def on_migration_finished(self, result: MigrationResult):
        """Handle migration completion."""
        self.reset_migration_ui()

        if result.success:
            self.status_label.setText("Migration completed successfully!")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")

            # Update results tab
            self.display_migration_results(result)

            # Switch to results tab
            self.tabs.setCurrentIndex(2)

            QMessageBox.information(
                self,
                "Success",
                f"Migration completed successfully!\n\nExecution time: {result.execution_time:.2f} seconds",
            )
        else:
            self.status_label.setText("Migration failed!")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.critical(self, "Migration Failed", result.message)

        self.log_message(f"Migration completed: {result.message}")

    def on_migration_error(self, error_message: str):
        """Handle migration errors."""
        self.reset_migration_ui()
        self.status_label.setText("Migration failed!")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        QMessageBox.critical(self, "Migration Error", error_message)
        self.log_message(f"Migration error: {error_message}")

    def reset_migration_ui(self):
        """Reset migration UI to initial state."""
        self.start_migration_btn.setEnabled(True)
        self.cancel_migration_btn.setEnabled(False)
        self.status_label.setText("Ready to migrate")
        self.status_label.setStyleSheet("font-weight: bold; color: black;")

    def display_migration_results(self, result: MigrationResult):
        """Display migration results in the results tab."""
        # Summary
        summary_text = f"""Migration completed {"successfully" if result.success else "with errors"}

Execution time: {result.execution_time:.2f} seconds
Backup files created: {len(result.backup_files)}
Conflicts detected: {len(result.conflicts)}
Items skipped: {len(result.skipped_items)}
"""
        self.results_summary.setPlainText(summary_text)

        # Conflicts
        self.conflicts_list.clear()
        for conflict in result.conflicts:
            item = QListWidgetItem(conflict)
            item.setToolTip(conflict)
            self.conflicts_list.addItem(item)

        for skipped in result.skipped_items:
            item = QListWidgetItem(f"SKIPPED: {skipped}")
            item.setToolTip(skipped)
            self.conflicts_list.addItem(item)

        # Backup files
        self.backups_list.clear()
        for backup in result.backup_files:
            item = QListWidgetItem(os.path.basename(backup))
            item.setData(Qt.ItemDataRole.UserRole, backup)  # Store full path
            item.setToolTip(backup)
            self.backups_list.addItem(item)

        # Full log
        if result.log_file and os.path.exists(result.log_file):
            try:
                with open(result.log_file, "r") as f:
                    log_content = f.read()
                    self.full_log_text.setPlainText(log_content)
            except Exception as e:
                self.full_log_text.setPlainText(f"Could not load log file: {e}")

    def open_backups_folder(self):
        """Open the folder containing backup files."""
        selected_items = self.backups_list.selectedItems()
        if selected_items:
            backup_path = selected_items[0].data(Qt.ItemDataRole.UserRole)
            if backup_path and os.path.exists(backup_path):
                folder_path = os.path.dirname(backup_path)
                # Open folder in system file manager
                if os.name == "nt":  # Windows
                    os.startfile(folder_path)
                elif os.name == "posix":  # macOS and Linux
                    os.system(f'xdg-open "{folder_path}"')

    def save_log(self):
        """Save migration log to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Migration Log",
            "migration_log.txt",
            "Text files (*.txt);;All files (*)",
        )

        if file_path:
            try:
                with open(file_path, "w") as f:
                    f.write(self.full_log_text.toPlainText())
                QMessageBox.information(self, "Success", "Log saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save log:\n{e}")

    def clear_log(self):
        """Clear the migration log."""
        self.full_log_text.clear()
        self.progress_text.clear()

    def log_message(self, message: str):
        """Add a message to the progress log."""
        timestamp = QTimer()
        from datetime import datetime

        formatted_message = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"

        self.progress_text.append(formatted_message)

        # Auto-scroll to bottom
        cursor = self.progress_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.progress_text.setTextCursor(cursor)

        # Process events to update UI immediately
        QApplication.processEvents()
