"""Supabase configuration dialog for managing multiple connection profiles."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QMessageBox, QLabel, QDialogButtonBox, QListWidget,
    QListWidgetItem, QSplitter, QGroupBox, QComboBox, QWidget
)
from PyQt6.QtCore import Qt
from ..utils.config import Config
from ..utils.supabase_connector import SupabaseConnector

class SupabaseConfigDialog(QDialog):
    """Dialog for configuring multiple Supabase connection profiles."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.current_profile_name: str | None = None # Track which profile is being edited
        self.profiles: list[dict] = [] # Local copy of profiles to manage changes
        self.setup_ui()
        self.load_profiles()
        
    def setup_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("Supabase Configuration Profiles")
        self.setMinimumSize(600, 400)
        main_layout = QHBoxLayout(self)
        
        # --- Left Side: Profile List --- 
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        
        left_layout.addWidget(QLabel("Connection Profiles:"))
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self.on_profile_selected)
        left_layout.addWidget(self.profile_list)
        
        list_buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Add New")
        add_btn.clicked.connect(self.add_new_profile)
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_selected_profile)
        list_buttons_layout.addWidget(add_btn)
        list_buttons_layout.addWidget(delete_btn)
        left_layout.addLayout(list_buttons_layout)

        # --- Right Side: Profile Details --- 
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)

        details_group = QGroupBox("Profile Details")
        form = QFormLayout(details_group)
        
        # Profile Name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Unique name for this connection")
        form.addRow("Profile Name:", self.name_input)
        
        # Supabase URL input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://<your-project-ref>.supabase.co")
        form.addRow("Project URL:", self.url_input)
        
        # Anon Key input
        self.anon_key_input = QLineEdit()
        self.anon_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Anon (Public) Key:", self.anon_key_input)
        
        # Service Role Key input
        self.service_key_input = QLineEdit()
        self.service_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Service Role Key (Optional):", self.service_key_input)
        
        right_layout.addWidget(details_group)
        
        # Add test connection button
        test_btn = QPushButton("Test Connection (Current Details)")
        test_btn.clicked.connect(self.test_connection)
        right_layout.addWidget(test_btn)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        right_layout.addWidget(self.status_label)
        
        right_layout.addStretch()

        # --- Splitter --- 
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([200, 400]) # Initial sizes
        main_layout.addWidget(splitter)
        
        # --- Dialog Buttons --- 
        dialog_buttons_layout = QVBoxLayout() # Use QVBoxLayout to put buttons below splitter

        # Active profile selector (optional, could also be implicit by selection)
        active_layout = QHBoxLayout()
        active_layout.addWidget(QLabel("Active Profile:"))
        self.active_profile_combo = QComboBox()
        active_layout.addWidget(self.active_profile_combo)
        active_layout.addStretch()
        dialog_buttons_layout.addLayout(active_layout)

        # Standard OK/Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_profiles) # Changed from save_config
        button_box.rejected.connect(self.reject)
        dialog_buttons_layout.addWidget(button_box)
        
        main_layout.addLayout(dialog_buttons_layout) # Add buttons below splitter

    def load_profiles(self):
        """Load profiles from config into the list and form."""
        self.profiles = self.config.get_supabase_connections().copy() # Work with a copy
        self.profile_list.clear()
        self.active_profile_combo.clear()
        self.active_profile_combo.addItem("None") # Option for no active profile
        
        active_profile_name = self.config.get_active_supabase_connection_name()
        active_index_to_select = -1
        active_combo_index = 0 # Default to 'None'

        for index, profile in enumerate(self.profiles):
            profile_name = profile.get('name', f'Profile {index+1}')
            item = QListWidgetItem(profile_name)
            item.setData(Qt.ItemDataRole.UserRole, profile_name) # Store name for retrieval
            self.profile_list.addItem(item)
            self.active_profile_combo.addItem(profile_name)
            if profile_name == active_profile_name:
                active_index_to_select = index
                active_combo_index = self.active_profile_combo.count() - 1
                
        self.active_profile_combo.setCurrentIndex(active_combo_index)
                
        if active_index_to_select != -1:
            self.profile_list.setCurrentRow(active_index_to_select)
            # self.on_profile_selected will be called automatically
        elif self.profile_list.count() > 0:
             self.profile_list.setCurrentRow(0)
             # self.on_profile_selected will be called automatically
        else:
            self.clear_form()
            self.set_form_enabled(False)

    def on_profile_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Load the selected profile's details into the form."""
        if not current:
            self.clear_form()
            self.set_form_enabled(False)
            self.current_profile_name = None
            return

        # Save changes of the previously selected item before loading new one
        if previous:
             self._save_current_form_to_profile(previous.data(Qt.ItemDataRole.UserRole))

        profile_name = current.data(Qt.ItemDataRole.UserRole)
        profile = next((p for p in self.profiles if p.get('name') == profile_name), None)
        
        if profile:
            self.current_profile_name = profile_name
            self.name_input.setText(profile.get('name', ''))
            self.url_input.setText(profile.get('url', ''))
            self.anon_key_input.setText(profile.get('anon_key', ''))
            self.service_key_input.setText(profile.get('service_role_key', ''))
            self.set_form_enabled(True)
            self.status_label.clear()
        else:
            # Should not happen if list and self.profiles are in sync
            self.clear_form()
            self.set_form_enabled(False)
            self.current_profile_name = None
            QMessageBox.warning(self, "Error", f"Could not find profile data for '{profile_name}'.")

    def _get_profile_from_form(self) -> dict:
        """Read profile data from the form fields."""
        return {
            "name": self.name_input.text().strip(),
            "url": self.url_input.text().strip(),
            "anon_key": self.anon_key_input.text().strip(),
            "service_role_key": self.service_key_input.text().strip()
        }

    def _save_current_form_to_profile(self, profile_name_to_save: str | None):
        """Saves the data in the form fields back to the self.profiles list
           for the specified profile name.
        """
        if profile_name_to_save is None:
            return
            
        form_data = self._get_profile_from_form()
        # Find the profile in our local list and update it
        for i, p in enumerate(self.profiles):
            if p.get('name') == profile_name_to_save:
                # Basic validation: ensure name isn't empty if it's being saved
                if not form_data['name']:
                     QMessageBox.warning(self, "Validation Error", "Profile Name cannot be empty.")
                     # Optionally revert form field? For now, we just warn.
                     return # Don't save invalid state
                     
                # Check if name changed and conflicts
                if form_data['name'] != profile_name_to_save:
                    if any(existing_p.get('name') == form_data['name'] for existing_p in self.profiles if existing_p.get('name') != profile_name_to_save):
                         QMessageBox.warning(self, "Validation Error", f"Profile name '{form_data['name']}' already exists.")
                         return # Don't save conflicting name
                         
                    # Update name in the list widget item too
                    current_item = self.profile_list.findItems(profile_name_to_save, Qt.MatchFlag.MatchExactly)[0]
                    current_item.setText(form_data['name']) # Update text
                    current_item.setData(Qt.ItemDataRole.UserRole, form_data['name']) # Update stored name
                    self.current_profile_name = form_data['name'] # Update tracked name
                    
                self.profiles[i] = form_data
                break

    def add_new_profile(self):
        """Prepare the form for adding a new profile."""
        # Save any pending changes to the currently selected profile first
        if self.current_profile_name:
             self._save_current_form_to_profile(self.current_profile_name)
        
        # Create a placeholder name
        new_profile_name = "New Profile"
        count = 1
        while any(p.get('name') == new_profile_name for p in self.profiles):
            count += 1
            new_profile_name = f"New Profile {count}"
            
        new_profile_data = {"name": new_profile_name, "url": "", "anon_key": "", "service_role_key": ""}
        self.profiles.append(new_profile_data)
        
        item = QListWidgetItem(new_profile_name)
        item.setData(Qt.ItemDataRole.UserRole, new_profile_name)
        self.profile_list.addItem(item)
        self.profile_list.setCurrentItem(item) # This will trigger on_profile_selected
        self.name_input.setFocus() # Focus on name field
        self.name_input.selectAll()
        self.set_form_enabled(True)

    def delete_selected_profile(self):
        """Delete the profile currently selected in the list."""
        current_item = self.profile_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Selection Error", "Please select a profile to delete.")
            return
            
        profile_name = current_item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"Are you sure you want to delete the profile '{profile_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from local list
            self.profiles = [p for p in self.profiles if p.get('name') != profile_name]
            # Remove from QListWidget
            row = self.profile_list.row(current_item)
            self.profile_list.takeItem(row)
            # Reload to refresh selection and form state
            self.load_profiles() 

    def save_profiles(self):
        """Save all profile changes back to the config file."""
        # Save any pending changes from the form to the last selected profile
        if self.current_profile_name:
            self._save_current_form_to_profile(self.current_profile_name)
            
        # Basic validation before saving all
        names = set()
        for profile in self.profiles:
            name = profile.get('name')
            if not name:
                 QMessageBox.critical(self, "Error", "One or more profiles have an empty name. Please fix before saving.")
                 return
            if name in names:
                 QMessageBox.critical(self, "Error", f"Duplicate profile name found: '{name}'. Names must be unique.")
                 return
            names.add(name)
            
        try:
            # Replace the entire list in the config with our edited list
            self.config.config['supabase_connections'] = self.profiles 
            
            # Save the selected active profile
            active_text = self.active_profile_combo.currentText()
            active_name = active_text if active_text != "None" else None
            self.config.set_active_supabase_connection_name(active_name)
            
            # This call implicitly saves the whole config, including the list and active name
            # self.config.save_config() # set_active already calls save
            
            self.accept() # Close dialog
        except Exception as e:
            QMessageBox.critical(self, "Error Saving Config", f"Could not save configuration: {str(e)}")

    def test_connection(self):
        """Test Supabase connection using the details currently in the form."""
        profile_data = self._get_profile_from_form()
        url = profile_data.get('url')
        anon_key = profile_data.get('anon_key')
        
        if not url or not anon_key:
            self.status_label.setText("URL and Anon Key are required to test.")
            self.status_label.setStyleSheet("color: orange")
            return False
            
        try:
            # Test using a temporary connector instance
            connector = SupabaseConnector(url, anon_key)
            client = connector.get_client()
            if client:
                 # Try a simple operation
                 buckets = client.storage.list_buckets() 
                 self.status_label.setText("Connection successful!")
                 self.status_label.setStyleSheet("color: green")
                 return True
            else:
                 raise Exception("Client could not be initialized.")
        except Exception as e:
            self.status_label.setText(f"Connection failed: {str(e)}")
            self.status_label.setStyleSheet("color: red")
            return False
            
    def clear_form(self):
        """Clear all input fields in the form."""
        self.name_input.clear()
        self.url_input.clear()
        self.anon_key_input.clear()
        self.service_key_input.clear()
        self.status_label.clear()

    def set_form_enabled(self, enabled: bool):
        """Enable or disable the form input fields."""
        self.name_input.setEnabled(enabled)
        self.url_input.setEnabled(enabled)
        self.anon_key_input.setEnabled(enabled)
        self.service_key_input.setEnabled(enabled) 