"""Widget for Supabase related tools."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QGroupBox, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QMessageBox, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt
# Now instantiate connector when needed, don't get singleton globally
# from ..utils.supabase_connector import get_supabase_connector 
from ..utils.supabase_connector import SupabaseConnector
from ..utils.config import Config # Need config to check active profile
from ..widgets.supabase_config_dialog import SupabaseConfigDialog
import os

class SupabaseWidget(QWidget):
    """Container widget for Supabase tools."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Don't create connector here yet, create when action is needed
        # self.connector = SupabaseConnector()
        self.config = Config() # Keep config access
        self.selected_md_path: str | None = None
        self.setup_ui()
        self.refresh_active_connection_status() # Initial status check
        
    def setup_ui(self):
        """Initialize the UI components."""
        main_layout = QVBoxLayout(self)
        
        # --- Top Bar: Active Connection Status & Config Button --- 
        top_bar_layout = QHBoxLayout()
        self.active_connection_label = QLabel("Active Supabase Connection: None")
        self.active_connection_label.setStyleSheet("font-style: italic; color: grey;")
        top_bar_layout.addWidget(self.active_connection_label)
        top_bar_layout.addStretch()
        self.config_btn = QPushButton("Manage Connections...")
        self.config_btn.clicked.connect(self.show_supabase_config)
        top_bar_layout.addWidget(self.config_btn)
        main_layout.addLayout(top_bar_layout)
        
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
        self.upload_md_btn.setEnabled(False) # Enable when file and bucket are ready
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
        self.source_table_combo.currentTextChanged.connect(self.update_clone_button_state) 
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
        self.clone_table_btn.setEnabled(False) # Enable when source/target are ready
        self.clone_table_btn.clicked.connect(self.clone_table)
        cloner_layout.addWidget(self.clone_table_btn)
        
        main_layout.addWidget(cloner_group)
        
        main_layout.addStretch() # Push groups to the top
        
    def refresh_active_connection_status(self):
        """Updates the status label and potentially refreshes lists if connection is active."""
        active_profile = self.config.get_active_supabase_connection()
        if active_profile:
            name = active_profile.get("name")
            self.active_connection_label.setText(f"Active Supabase Connection: <b>{name}</b>")
            self.active_connection_label.setStyleSheet("font-style: normal; color: black;") # Or theme color
            # Optionally auto-refresh lists when status changes to active
            self.refresh_buckets()
            self.refresh_tables()
        else:
            self.active_connection_label.setText("Active Supabase Connection: None")
            self.active_connection_label.setStyleSheet("font-style: italic; color: grey;")
            # Clear lists if no connection is active
            self.bucket_combo.clear()
            self.source_table_combo.clear()
            self.update_upload_button_state()
            self.update_clone_button_state()

    def show_supabase_config(self):
        """Show Supabase configuration dialog and refresh status on close."""
        dialog = SupabaseConfigDialog(self)
        dialog.exec() # Use exec_() for modal dialog behavior
        # Refresh status after dialog closes, regardless of accept/reject
        # as the active connection might have been changed or deleted
        self.refresh_active_connection_status() 

    def select_markdown_file(self):
        """Open dialog to select a markdown file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Markdown File", "", "Markdown Files (*.md *.markdown);;All Files (*)")
        if file_path:
            self.selected_md_path = file_path
            self.md_file_label.setText(os.path.basename(file_path))
            self.update_upload_button_state()
        else:
            self.selected_md_path = None
            self.md_file_label.setText("No file selected")
            self.update_upload_button_state()

    def _get_current_connector(self) -> SupabaseConnector | None:
        """Helper to get a connector instance based on current active config."""
        connector = SupabaseConnector()
        if not connector.get_client():
             QMessageBox.warning(self, "Connection Error",
                                 "No active Supabase connection or failed to connect. Check configuration.")
             return None
        return connector

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
            self.bucket_combo.clear() # Clear on error
            self.update_upload_button_state()

    def update_upload_button_state(self):
        """Enable/disable upload button based on file/bucket selection and active connection."""
        has_file = self.selected_md_path is not None
        has_bucket = bool(self.bucket_combo.currentText())
        has_connection = self.config.get_active_supabase_connection() is not None
        self.upload_md_btn.setEnabled(has_file and has_bucket and has_connection)

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
        bucket_path = file_name # Define path within the bucket
        
        progress = QProgressDialog(f"Uploading {file_name}...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        QApplication.processEvents() # Ensure dialog shows
        
        try:
            with open(self.selected_md_path, 'rb') as f:
                # Use service client if available for potentially better permissions/control
                service_client = connector.get_service_client()
                upload_client = service_client if service_client else client
                
                # Check if bucket exists, create if not (requires service key or proper policy)
                try:
                    upload_client.storage.get_bucket(bucket_name)
                except Exception:
                    reply = QMessageBox.question(self, "Create Bucket?", 
                                                 f"Bucket '{bucket_name}' not found. Create it?",
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        if not service_client:
                             raise Exception("Service Role Key needed to create buckets.")
                        # Create public bucket for simplicity, adjust as needed
                        service_client.storage.create_bucket(bucket_name, options={"public": True})
                    else:
                        raise Exception(f"Bucket '{bucket_name}' does not exist.")
                
                # Perform upload
                res = upload_client.storage.from_(bucket_name).upload(
                    path=bucket_path,
                    file=f,
                    file_options={"content-type": "text/markdown", "upsert": "true"} # Upsert = true overwrites
                )
                
            progress.close()
            QMessageBox.information(self, "Upload Complete", f"'{file_name}' uploaded to bucket '{bucket_name}'.")

        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Upload Failed", str(e))

    def refresh_tables(self):
        """Fetch and update the list of tables for the active connection."""
        connector = self._get_current_connector()
        if not connector:
            self.source_table_combo.clear()
            return
            
        client = connector.get_client()
        try:
            # Fetch tables from the 'public' schema (common default)
            response = client.rpc('get_schema_tables', {"schema_name": "public"}).execute()
            
            if response.data:
                current_table = self.source_table_combo.currentText()
                self.source_table_combo.clear()
                self.source_table_combo.addItems(sorted([t['tablename'] for t in response.data]))
                
                index = self.source_table_combo.findText(current_table)
                if index >= 0:
                    self.source_table_combo.setCurrentIndex(index)
                    
                self.update_clone_button_state()
            else:
                 # Check for specific error if possible, maybe permission error?
                 if hasattr(response, 'error') and response.error:
                      QMessageBox.warning(self, "No Tables Found", f"Could not retrieve tables: {response.error.message}")
                 else:
                      QMessageBox.warning(self, "No Tables Found", "Could not retrieve tables. Check permissions or RPC function '$get_schema_tables'.")
                 self.source_table_combo.clear()
                 self.update_clone_button_state()
                 
        except Exception as e:
            QMessageBox.critical(self, "Error Refreshing Tables", f"Could not list tables: {str(e)}\nEnsure the 'get_schema_tables' RPC function exists or adjust permissions.")
            self.source_table_combo.clear()
            self.update_clone_button_state()

    def update_clone_button_state(self):
        """Enable/disable clone button based on table selection/name and active connection."""
        has_source = bool(self.source_table_combo.currentText())
        has_target_name = bool(self.new_table_name_input.text().strip())
        has_connection = self.config.get_active_supabase_connection() is not None
        self.clone_table_btn.setEnabled(has_source and has_target_name and has_connection)
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
            QMessageBox.critical(self, "Permission Error", "Service Role Key for the active connection is required to clone tables.")
            return
            
        source_table = self.source_table_combo.currentText()
        new_table = self.new_table_name_input.text().strip()
        
        if not source_table or not new_table:
             QMessageBox.warning(self, "Input Missing", "Please select a source table and enter a new table name.")
             return
             
        if source_table == new_table:
             QMessageBox.warning(self, "Invalid Name", "New table name cannot be the same as the source table.")
             return

        reply = QMessageBox.question(self, "Confirm Clone",
                                     f"Clone table '{source_table}' to '{new_table}'? This will copy structure and data.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return
            
        progress = QProgressDialog(f"Cloning {source_table}...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        QApplication.processEvents()
        
        try:
            # Step 1: Create the new table like the source table (structure only)
            # This often requires executing raw SQL
            create_sql = f"CREATE TABLE public.\"{new_table}\" (LIKE public.\"{source_table}\" INCLUDING ALL);"
            # Using rpc to execute raw SQL (requires a helper function in Supabase SQL Editor)
            # Example SQL function 'execute_sql(sql_query text)'
            # CREATE OR REPLACE FUNCTION execute_sql(sql_query text)
            # RETURNS void
            # LANGUAGE plpgsql
            # SECURITY DEFINER -- Requires careful security considerations
            # AS $$
            # BEGIN
            #   EXECUTE sql_query;
            # END;
            # $$;
            service_client.rpc('execute_sql', {"sql_query": create_sql}).execute()
            
            # Step 2: Copy data from source to new table
            copy_sql = f"INSERT INTO public.\"{new_table}\" SELECT * FROM public.\"{source_table}\";"
            service_client.rpc('execute_sql', {"sql_query": copy_sql}).execute()

            progress.close()
            QMessageBox.information(self, "Clone Complete", f"Table '{source_table}' cloned to '{new_table}'.")
            self.refresh_tables() # Update table list
            self.new_table_name_input.clear()

        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Clone Failed", f"Error cloning table: {str(e)}\nCheck permissions and ensure the 'execute_sql' RPC function exists.") 