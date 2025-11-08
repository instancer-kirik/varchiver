"""Widget for Supabase related tools."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QGroupBox,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QComboBox,
    QMessageBox,
    QProgressDialog,
    QApplication,
)
from PyQt6.QtCore import Qt

# Now instantiate connector when needed, don't get singleton globally
# from ..utils.supabase_connector import get_supabase_connector
from ..utils.supabase_connector import SupabaseConnector
from ..utils.config import Config  # Need config to check active profile
from ..widgets.supabase_config_dialog import SupabaseConfigDialog
import os


class SupabaseWidget(QWidget):
    """Container widget for Supabase tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Don't create connector here yet, create when action is needed
        # self.connector = SupabaseConnector()
        self.config = Config()  # Keep config access
        self.selected_md_path: str | None = None
        self.setup_ui()
        self.refresh_active_connection_status()  # Initial status check

    def setup_ui(self):
        """Initialize the UI components."""
        main_layout = QVBoxLayout(self)

        # --- Top Bar: Connection Profile Selector & Config Button ---
        top_bar_layout = QHBoxLayout()

        # Connection profile selector
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("(Select a profile)")
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)
        profile_layout.addWidget(self.profile_combo)

        refresh_profiles_btn = QPushButton("🔄")
        refresh_profiles_btn.setMaximumWidth(30)
        refresh_profiles_btn.setToolTip("Refresh profile list")
        refresh_profiles_btn.clicked.connect(self.refresh_profiles)
        profile_layout.addWidget(refresh_profiles_btn)

        top_bar_layout.addLayout(profile_layout)
        top_bar_layout.addStretch()

        self.config_btn = QPushButton("Manage Connections...")
        self.config_btn.clicked.connect(self.show_supabase_config)
        top_bar_layout.addWidget(self.config_btn)
        main_layout.addLayout(top_bar_layout)

        # Connection status label
        self.connection_status_label = QLabel("No profile selected")
        self.connection_status_label.setStyleSheet(
            "font-size: 11px; color: #666; font-style: italic; margin: 5px 0px;"
        )
        main_layout.addWidget(self.connection_status_label)

        # --- MD Uploader Group ---
        md_group = QGroupBox("Markdown Uploader")
        md_layout = QVBoxLayout(md_group)

        # File selection
        file_select_layout = QHBoxLayout()
        self.md_file_label = QLabel("No file selected")
        self.md_file_label.setWordWrap(True)
        select_md_btn = QPushButton("Select Markdown File")
        select_md_btn.clicked.connect(self.select_markdown_file)
        file_select_layout.addWidget(QLabel("File:"))
        file_select_layout.addWidget(self.md_file_label)
        file_select_layout.addWidget(select_md_btn)
        md_layout.addLayout(file_select_layout)

        # Bucket selection
        bucket_layout = QHBoxLayout()
        self.bucket_combo = QComboBox()
        self.bucket_combo.setEditable(True)
        self.bucket_combo.setPlaceholderText("Enter or select bucket name")
        # Connect text changed signal AFTER initial population
        self.bucket_combo.currentTextChanged.connect(self.update_upload_button_state)
        refresh_buckets_btn = QPushButton("Refresh Buckets")
        refresh_buckets_btn.clicked.connect(self.refresh_buckets)
        bucket_layout.addWidget(QLabel("Storage Bucket:"))
        bucket_layout.addWidget(self.bucket_combo)
        bucket_layout.addWidget(refresh_buckets_btn)
        md_layout.addLayout(bucket_layout)

        # Upload button
        self.upload_md_btn = QPushButton("Upload to Bucket")
        self.upload_md_btn.setEnabled(False)  # Enable when file and bucket are ready
        self.upload_md_btn.clicked.connect(self.upload_markdown)
        md_layout.addWidget(self.upload_md_btn)

        main_layout.addWidget(md_group)

        # --- Table Cloner Group ---
        cloner_group = QGroupBox("Table Cloner")
        cloner_layout = QVBoxLayout(cloner_group)

        # Table selection
        table_select_layout = QHBoxLayout()
        self.source_table_combo = QComboBox()
        self.source_table_combo.setPlaceholderText("Select source table")
        self.source_table_combo.currentTextChanged.connect(
            self.update_clone_button_state
        )
        refresh_tables_btn = QPushButton("Refresh Tables")
        refresh_tables_btn.clicked.connect(self.refresh_tables)
        table_select_layout.addWidget(QLabel("Source Table:"))
        table_select_layout.addWidget(self.source_table_combo)
        table_select_layout.addWidget(refresh_tables_btn)
        cloner_layout.addLayout(table_select_layout)

        # New table name
        new_table_layout = QHBoxLayout()
        self.new_table_name_input = QLineEdit()
        self.new_table_name_input.setPlaceholderText("Enter name for new table")
        self.new_table_name_input.textChanged.connect(self.update_clone_button_state)
        new_table_layout.addWidget(QLabel("New Table Name:"))
        new_table_layout.addWidget(self.new_table_name_input)
        cloner_layout.addLayout(new_table_layout)

        # Clone button
        self.clone_table_btn = QPushButton("Clone Table")
        self.clone_table_btn.setEnabled(False)  # Enable when source/target are ready
        self.clone_table_btn.clicked.connect(self.clone_table)
        cloner_layout.addWidget(self.clone_table_btn)

        main_layout.addWidget(cloner_group)

        main_layout.addStretch()  # Push groups to the top

    def refresh_profiles(self):
        """Refresh the list of available connection profiles."""
        current_selection = self.profile_combo.currentText()
        self.profile_combo.clear()
        self.profile_combo.addItem("(Select a profile)")

        profiles = self.config.get_supabase_connections()

        for profile in profiles:
            profile_name = profile.get("name", "").strip()
            if profile_name:  # Just check for non-empty names
                self.profile_combo.addItem(profile_name)

        # Restore previous selection if it still exists
        index = self.profile_combo.findText(current_selection)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)

    def on_profile_changed(self, profile_name):
        """Handle profile selection change."""
        if profile_name == "(Select a profile)" or not profile_name:
            self.connection_status_label.setText("No profile selected")
            self.connection_status_label.setStyleSheet(
                "font-size: 11px; color: #666; font-style: italic;"
            )
            # Clear lists when no profile selected
            self.bucket_combo.clear()
            self.source_table_combo.clear()
            self.update_upload_button_state()
            self.update_clone_button_state()
        else:
            # Test if we can get a connector for this profile
            profile = self.config.get_supabase_connection_by_name(profile_name)
            if profile:
                self.connection_status_label.setText(
                    f"Selected: <b>{profile_name}</b> ({profile.get('url', 'No URL')})"
                )
                self.connection_status_label.setStyleSheet(
                    "font-size: 11px; color: #333;"
                )
                # Refresh buckets for the selected profile
                self.refresh_buckets()
            else:
                self.connection_status_label.setText(
                    f"Profile '{profile_name}' not found"
                )
                self.connection_status_label.setStyleSheet(
                    "font-size: 11px; color: #d32f2f; font-style: italic;"
                )

    def refresh_active_connection_status(self):
        """Initialize the profile selector and update status."""
        self.refresh_profiles()

    def show_supabase_config(self):
        """Show Supabase configuration dialog and refresh status on close."""
        dialog = SupabaseConfigDialog(self)
        dialog.profiles_changed.connect(self.on_profiles_changed)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Only refresh if user clicked OK (saved changes)
            self.refresh_profiles()

    def on_profiles_changed(self):
        """Handle profiles changed signal from config dialog."""
        # Refresh the supabase connector to pick up changes
        from ..utils.supabase_connector import refresh_supabase_connection

        refresh_supabase_connection()
        self.refresh_profiles()

    def select_markdown_file(self):
        """Open dialog to select a markdown file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Markdown File",
            "",
            "Markdown Files (*.md *.markdown);;All Files (*)",
        )
        if file_path:
            self.selected_md_path = file_path
            self.md_file_label.setText(os.path.basename(file_path))
            self.update_upload_button_state()
        else:
            self.selected_md_path = None
            self.md_file_label.setText("No file selected")
            self.update_upload_button_state()

    def _get_current_connector(self) -> SupabaseConnector | None:
        """Helper to get a connector instance based on currently selected profile."""
        selected_profile = self.profile_combo.currentText()
        if selected_profile == "(Select a profile)" or not selected_profile:
            QMessageBox.warning(
                self,
                "No Profile Selected",
                "Please select a connection profile from the dropdown first.",
            )
            return None

        # Get the profile data
        profile = self.config.get_supabase_connection_by_name(selected_profile)
        if not profile:
            QMessageBox.warning(
                self,
                "Profile Not Found",
                f"The selected profile '{selected_profile}' was not found in the configuration.",
            )
            return None

        # Temporarily set this as the active profile for the connector
        original_active = self.config.get_active_supabase_connection_name()
        self.config.set_active_supabase_connection_name(selected_profile)

        try:
            connector = SupabaseConnector()
            client = connector.get_client()
            if not client:
                QMessageBox.warning(
                    self,
                    "Connection Error",
                    f"Failed to connect to '{selected_profile}'. Check the profile configuration.",
                )
                return None
            return connector
        finally:
            # Restore original active connection
            self.config.set_active_supabase_connection_name(original_active)

    def refresh_buckets(self):
        """Fetch and update the list of storage buckets for the active connection."""
        connector = self._get_current_connector()
        if not connector:
            self.bucket_combo.clear()
            return

        client = connector.get_client()
        try:
            buckets = client.storage.list_buckets()
            current_bucket = self.bucket_combo.currentText()
            self.bucket_combo.clear()
            self.bucket_combo.addItems([b.name for b in buckets])
            # Restore selection if it exists
            index = self.bucket_combo.findText(current_bucket)
            if index >= 0:
                self.bucket_combo.setCurrentIndex(index)
            else:
                self.bucket_combo.setCurrentText(current_bucket)

            self.update_upload_button_state()
        except Exception as e:
            QMessageBox.critical(self, "Error Refreshing Buckets", str(e))
            self.bucket_combo.clear()  # Clear on error
            self.update_upload_button_state()

    def update_upload_button_state(self):
        """Enable/disable upload button based on file/bucket selection and profile selection."""
        has_file = self.selected_md_path is not None
        has_bucket = bool(self.bucket_combo.currentText())
        has_profile = self.profile_combo.currentText() != "(Select a profile)" and bool(
            self.profile_combo.currentText()
        )
        self.upload_md_btn.setEnabled(has_file and has_bucket and has_profile)

    def upload_markdown(self):
        """Upload the selected markdown file to the selected bucket using active connection."""
        if not self.selected_md_path:
            QMessageBox.warning(self, "Error", "No file selected.")
            return

        connector = self._get_current_connector()
        if not connector:
            return

        client = connector.get_client()
        bucket_name = self.bucket_combo.currentText()
        if not bucket_name:
            QMessageBox.warning(self, "Error", "No bucket selected or specified.")
            return

        file_name = os.path.basename(self.selected_md_path)
        bucket_path = file_name  # Define path within the bucket

        progress = QProgressDialog(f"Uploading {file_name}...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        QApplication.processEvents()  # Ensure dialog shows

        try:
            with open(self.selected_md_path, "rb") as f:
                # Use service client if available for potentially better permissions/control
                service_client = connector.get_service_client()
                upload_client = service_client if service_client else client

                # Check if bucket exists, create if not (requires service key or proper policy)
                try:
                    upload_client.storage.get_bucket(bucket_name)
                except Exception:
                    reply = QMessageBox.question(
                        self,
                        "Create Bucket?",
                        f"Bucket '{bucket_name}' not found. Create it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        if not service_client:
                            raise Exception(
                                "Service Role Key needed to create buckets."
                            )
                        # Create public bucket for simplicity, adjust as needed
                        service_client.storage.create_bucket(
                            bucket_name, options={"public": True}
                        )
                    else:
                        raise Exception(f"Bucket '{bucket_name}' does not exist.")

                # Perform upload
                res = upload_client.storage.from_(bucket_name).upload(
                    path=bucket_path,
                    file=f,
                    file_options={
                        "content-type": "text/markdown",
                        "upsert": "true",
                    },  # Upsert = true overwrites
                )

            progress.close()
            QMessageBox.information(
                self,
                "Upload Complete",
                f"'{file_name}' uploaded to bucket '{bucket_name}'.",
            )

        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Upload Failed", str(e))

    def refresh_tables(self):
        """Fetch and update the list of tables for the active connection using Supabase client."""
        connector = self._get_current_connector()
        if not connector:
            self.source_table_combo.clear()
            return

        # Get service client for admin operations
        service_client = connector.get_service_client()
        if not service_client:
            QMessageBox.warning(
                self,
                "Service Connection Error",
                "Could not get service client for table operations.\n"
                "Check that your Supabase profile has a valid service role key.",
            )
            self.source_table_combo.clear()
            return

        try:
            # Use Supabase RPC to get table information
            # This RPC function needs to be created in your Supabase project
            result = service_client.rpc("get_user_tables").execute()

            if result.data:
                tables = [table["table_name"] for table in result.data]

                if tables:
                    current_table = self.source_table_combo.currentText()
                    self.source_table_combo.clear()
                    self.source_table_combo.addItems(sorted(tables))

                    # Restore previous selection if it still exists
                    index = self.source_table_combo.findText(current_table)
                    if index >= 0:
                        self.source_table_combo.setCurrentIndex(index)

                    self.update_clone_button_state()
                else:
                    QMessageBox.information(
                        self,
                        "No Tables Found",
                        "No user tables found in the public schema.",
                    )
                    self.source_table_combo.clear()
                    self.update_clone_button_state()
            else:
                # Fallback: try to query a known table to test connection
                # This is a minimal approach that avoids direct PostgreSQL connections
                try:
                    # Try to access auth.users which should exist in any Supabase project
                    test_result = (
                        service_client.table("auth.users")
                        .select("id")
                        .limit(1)
                        .execute()
                    )

                    QMessageBox.information(
                        self,
                        "RPC Function Missing",
                        "The 'get_user_tables' RPC function is not available.\n\n"
                        "Connection to Supabase is working, but table listing requires\n"
                        "an RPC function to be created in your Supabase project.\n\n"
                        "You can still use manual table operations.",
                    )
                except Exception:
                    QMessageBox.warning(
                        self,
                        "Connection Test Failed",
                        "Could not verify Supabase connection.\n"
                        "Please check your connection configuration.",
                    )

                self.source_table_combo.clear()
                self.update_clone_button_state()

        except Exception as e:
            error_msg = str(e)
            QMessageBox.critical(
                self,
                "Error Refreshing Tables",
                f"Could not list tables: {error_msg}\n\n"
                "This may be due to missing RPC function or connection issues.\n"
                "Check your Supabase configuration and permissions.",
            )
            self.source_table_combo.clear()
            self.update_clone_button_state()

    def update_clone_button_state(self):
        """Enable/disable clone button based on table selection/name and profile selection."""
        has_source = bool(self.source_table_combo.currentText())
        has_target_name = bool(self.new_table_name_input.text().strip())
        has_profile = self.profile_combo.currentText() != "(Select a profile)" and bool(
            self.profile_combo.currentText()
        )
        self.clone_table_btn.setEnabled(has_source and has_target_name and has_profile)
        # Connect signals only once if needed, or ensure they don't cause infinite loops
        # self.new_table_name_input.textChanged.connect(self.update_clone_button_state)
        # self.source_table_combo.currentTextChanged.connect(self.update_clone_button_state)

    def clone_table(self):
        """Clone the selected table structure and data using the active connection."""
        connector = self._get_current_connector()
        if not connector:
            return

        service_client = connector.get_service_client()
        if not service_client:
            QMessageBox.critical(
                self,
                "Permission Error",
                "Service Role Key for the active connection is required to clone tables.",
            )
            return

        source_table = self.source_table_combo.currentText()
        new_table = self.new_table_name_input.text().strip()

        if not source_table or not new_table:
            QMessageBox.warning(
                self,
                "Input Missing",
                "Please select a source table and enter a new table name.",
            )
            return

        if source_table == new_table:
            QMessageBox.warning(
                self,
                "Invalid Name",
                "New table name cannot be the same as the source table.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Clone",
            f"Clone table '{source_table}' to '{new_table}'? This will copy structure and data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            return

        progress = QProgressDialog(f"Cloning {source_table}...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        QApplication.processEvents()

        try:
            # Step 1: Create the new table like the source table (structure only)
            # Use Supabase RPC to clone table (requires RPC function in Supabase)
            service_client = connector.get_service_client()
            if not service_client:
                progress.close()
                QMessageBox.critical(
                    self,
                    "Service Connection Error",
                    "Could not get service client for table cloning.\n"
                    "Check that your Supabase profile has a valid service role key.",
                )
                return

            try:
                # Try to use RPC function for table cloning
                result = service_client.rpc(
                    "clone_table",
                    {"source_table": source_table, "target_table": new_table},
                ).execute()

                if result.data is not None:
                    progress.close()
                    QMessageBox.information(
                        self,
                        "Clone Complete",
                        f"Table '{source_table}' cloned to '{new_table}'.",
                    )
                    self.refresh_tables()  # Update table list
                    self.new_table_name_input.clear()
                    return
                else:
                    raise Exception("RPC function returned no data")

            except Exception as rpc_error:
                # RPC failed, show helpful message about creating the function
                progress.close()
                QMessageBox.critical(
                    self,
                    "Table Clone Failed",
                    f"Could not clone table using RPC: {rpc_error}\n\n"
                    "This operation requires a 'clone_table' RPC function in your Supabase project.\n\n"
                    "You can create this function in the Supabase SQL Editor:\n\n"
                    "CREATE OR REPLACE FUNCTION clone_table(source_table text, target_table text)\n"
                    "RETURNS void\n"
                    "LANGUAGE plpgsql\n"
                    "SECURITY DEFINER\n"
                    "AS $$\n"
                    "BEGIN\n"
                    "  EXECUTE format('CREATE TABLE %I (LIKE %I INCLUDING ALL)', target_table, source_table);\n"
                    "  EXECUTE format('INSERT INTO %I SELECT * FROM %I', target_table, source_table);\n"
                    "END;\n"
                    "$$;",
                )
                return

        except Exception as e:
            progress.close()
            error_msg = str(e)
            QMessageBox.critical(
                self,
                "Clone Failed",
                f"Failed to clone table: {error_msg}\n\n"
                "Check your Supabase connection and permissions.\n"
                "Make sure the required RPC functions are available.",
            )
