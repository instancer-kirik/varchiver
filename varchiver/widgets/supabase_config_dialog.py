"""Enhanced dialog for managing Supabase connection profiles with .env file integration."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QListWidget,
    QFormLayout,
    QGroupBox,
    QComboBox,
    QDialogButtonBox,
    QSplitter,
    QWidget,
    QMessageBox,
    QListWidgetItem,
    QCheckBox,
    QTextEdit,
    QTabWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from ..utils.config import Config
from ..utils.env_manager import EnvManager


class SupabaseConfigDialog(QDialog):
    """Enhanced dialog for managing Supabase connection profiles with .env integration."""

    profiles_changed = pyqtSignal()  # Signal emitted when profiles are modified

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.env_manager = EnvManager()
        self.profiles = []
        self.current_profile_name = None

        self.setup_ui()
        self.load_profiles()

    def setup_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("Supabase Configuration Manager")
        self.setMinimumSize(900, 650)
        main_layout = QVBoxLayout(self)

        # Create tab widget for different views
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # --- Profile Management Tab ---
        profile_tab = QWidget()
        tab_widget.addTab(profile_tab, "Profile Management")
        self.setup_profile_tab(profile_tab)

        # --- Environment Variables Tab ---
        env_tab = QWidget()
        tab_widget.addTab(env_tab, "Environment Variables")
        self.setup_env_tab(env_tab)

        # --- Active Profile Selection ---
        active_layout = QHBoxLayout()
        active_layout.addWidget(QLabel("Active Profile:"))
        self.active_profile_combo = QComboBox()
        active_layout.addWidget(self.active_profile_combo)
        active_layout.addStretch()
        main_layout.addLayout(active_layout)

        # --- Dialog Buttons ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_profiles)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def setup_profile_tab(self, parent):
        """Setup the profile management tab."""
        layout = QVBoxLayout(parent)

        # Create splitter for left/right layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # --- Left Side: Profile List ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        left_layout.addWidget(QLabel("Connection Profiles:"))

        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.itemSelectionChanged.connect(self.on_profile_selected)
        left_layout.addWidget(self.profile_list)

        # Profile management buttons
        btn_layout = QVBoxLayout()

        add_btn = QPushButton("Add New Profile")
        add_btn.clicked.connect(self.add_new_profile)
        btn_layout.addWidget(add_btn)

        add_env_btn = QPushButton("Add Environment Profile")
        add_env_btn.clicked.connect(self.add_env_profile)
        btn_layout.addWidget(add_env_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_selected_profile)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()
        left_layout.addLayout(btn_layout)

        splitter.addWidget(left_widget)

        # --- Right Side: Profile Details ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Profile details form
        details_group = QGroupBox("Profile Details")
        form_layout = QFormLayout(details_group)

        # Profile name
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self._save_current_form_to_profile)
        form_layout.addRow("Profile Name:", self.name_edit)

        # Environment integration checkbox
        self.use_env_checkbox = QCheckBox("Use Environment Variables")
        self.use_env_checkbox.stateChanged.connect(self.on_use_env_changed)
        form_layout.addRow("", self.use_env_checkbox)

        # Connection fields
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://your-project.supabase.co")
        self.url_edit.textChanged.connect(self._save_current_form_to_profile)
        form_layout.addRow("Project URL:", self.url_edit)

        self.anon_key_edit = QLineEdit()
        self.anon_key_edit.setPlaceholderText("eyJhbGciOiJIUzI1NiIs...")
        self.anon_key_edit.textChanged.connect(self._save_current_form_to_profile)
        form_layout.addRow("Anon Key:", self.anon_key_edit)

        self.service_key_edit = QLineEdit()
        self.service_key_edit.setPlaceholderText("eyJhbGciOiJIUzI1NiIs...")
        self.service_key_edit.textChanged.connect(self._save_current_form_to_profile)
        form_layout.addRow("Service Key:", self.service_key_edit)

        right_layout.addWidget(details_group)

        # Connection actions
        action_layout = QHBoxLayout()

        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_connection)
        action_layout.addWidget(test_btn)

        debug_btn = QPushButton("Debug Connection")
        debug_btn.clicked.connect(self.debug_connection)
        debug_btn.setStyleSheet("background-color: #f0f0f0;")
        action_layout.addWidget(debug_btn)

        right_layout.addLayout(action_layout)

        # Status label
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        right_layout.addWidget(self.status_label)

        right_layout.addStretch()
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 600])

        # Initially disable form
        self.set_form_enabled(False)

    def setup_env_tab(self, parent):
        """Setup the environment variables tab."""
        layout = QVBoxLayout(parent)

        # Info label
        info_label = QLabel(
            "This tab shows the current .env file contents and allows direct editing. "
            "Changes made here will be saved to your .env file when you click OK."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "color: #666; padding: 10px; background: #f5f5f5; border-radius: 4px;"
        )
        layout.addWidget(info_label)

        # Env file path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Environment file:"))
        self.env_path_label = QLabel(str(self.env_manager.get_env_file_path()))
        self.env_path_label.setStyleSheet("font-family: monospace; color: #333;")
        path_layout.addWidget(self.env_path_label)
        path_layout.addStretch()

        reload_btn = QPushButton("Reload from File")
        reload_btn.clicked.connect(self.reload_env_display)
        path_layout.addWidget(reload_btn)

        layout.addLayout(path_layout)

        # Environment variables editor
        self.env_editor = QTextEdit()
        self.env_editor.setFont(self.env_editor.font())
        font = self.env_editor.font()
        font.setFamily("monospace")
        self.env_editor.setFont(font)
        layout.addWidget(self.env_editor)

        # Load current env content
        self.reload_env_display()

    def reload_env_display(self):
        """Reload the environment file content into the editor."""
        try:
            env_path = self.env_manager.get_env_file_path()
            if env_path.exists():
                content = env_path.read_text()
                self.env_editor.setPlainText(content)
            else:
                self.env_editor.setPlainText(
                    "# No .env file found - will be created when you save profiles"
                )
        except Exception as e:
            self.env_editor.setPlainText(f"# Error reading .env file: {e}")

    def on_use_env_changed(self, state):
        """Handle changes to the 'Use Environment Variables' checkbox."""
        use_env = state == Qt.CheckState.Checked.value

        # Update current profile
        if self.current_profile_name:
            for profile in self.profiles:
                if profile.get("name") == self.current_profile_name:
                    profile["use_env"] = use_env
                    break

        # Update form state
        self.update_form_for_env_mode(use_env)

    def update_form_for_env_mode(self, use_env):
        """Update form fields based on environment mode."""
        if use_env:
            # Load values from environment
            if self.current_profile_name:
                env_vars = self.env_manager.get_env_vars_for_profile(
                    self.current_profile_name
                )
                self.url_edit.setText(env_vars.get("url") or "")
                self.anon_key_edit.setText(env_vars.get("anon_key") or "")
                self.service_key_edit.setText(env_vars.get("service_key") or "")

                # Set placeholder text to show env var names
                profile_upper = self.current_profile_name.upper()
                self.url_edit.setPlaceholderText(f"From SUPABASE_{profile_upper}_URL")
                self.anon_key_edit.setPlaceholderText(
                    f"From SUPABASE_{profile_upper}_ANON_KEY"
                )
                self.service_key_edit.setPlaceholderText(
                    f"From SUPABASE_{profile_upper}_SERVICE_KEY"
                )
        else:
            # Reset placeholder text
            self.url_edit.setPlaceholderText("https://your-project.supabase.co")
            self.anon_key_edit.setPlaceholderText("eyJhbGciOiJIUzI1NiIs...")
            self.service_key_edit.setPlaceholderText("eyJhbGciOiJIUzI1NiIs...")

    def load_profiles(self):
        """Load profiles from config and environment."""
        self.profiles = self.config.get_supabase_connections().copy()
        self.profile_list.clear()

        # Add profiles from config
        for profile in self.profiles:
            name = profile.get("name", "")
            if name:
                item = QListWidgetItem(name)
                if profile.get("use_env"):
                    item.setText(f"{name} (env)")
                item.setData(Qt.ItemDataRole.UserRole, profile.copy())
                self.profile_list.addItem(item)

        # Load profiles detected from environment variables
        env_profiles = self.env_manager.get_all_supabase_profiles()
        for env_profile in env_profiles:
            # Check if this profile already exists in config
            existing = any(
                p.get("name", "").lower() == env_profile for p in self.profiles
            )
            if not existing:
                # Add as environment-only profile
                profile = {
                    "name": env_profile.title(),
                    "url": "",
                    "use_env": True,
                    "anon_key": "",
                    "service_role_key": "",
                }
                self.profiles.append(profile)

                item = QListWidgetItem(f"{env_profile.title()} (env-detected)")
                item.setData(Qt.ItemDataRole.UserRole, profile.copy())
                self.profile_list.addItem(item)

        self._rebuild_active_combo()

    def on_profile_selected(self):
        """Handle profile selection."""
        current_item = self.profile_list.currentItem()
        if not current_item:
            self.clear_form()
            self.set_form_enabled(False)
            return

        profile = current_item.data(Qt.ItemDataRole.UserRole)
        if not profile:
            return

        self.current_profile_name = profile.get("name", "")

        # Populate form
        self.name_edit.setText(profile.get("name", ""))
        self.use_env_checkbox.setChecked(profile.get("use_env", False))

        if profile.get("use_env"):
            # Load from environment
            env_vars = self.env_manager.get_env_vars_for_profile(
                self.current_profile_name
            )
            self.url_edit.setText(env_vars.get("url") or "")
            self.anon_key_edit.setText(env_vars.get("anon_key") or "")
            self.service_key_edit.setText(env_vars.get("service_key") or "")
        else:
            # Load from profile
            self.url_edit.setText(profile.get("url", ""))
            self.anon_key_edit.setText(
                profile.get("anon_key", "") or profile.get("publishable_key", "")
            )
            self.service_key_edit.setText(
                profile.get("service_role_key", "") or profile.get("secret_key", "")
            )

        self.update_form_for_env_mode(profile.get("use_env", False))
        self.set_form_enabled(True)

    def _get_profile_from_form(self):
        """Get profile data from form fields."""
        return {
            "name": self.name_edit.text().strip(),
            "url": self.url_edit.text().strip(),
            "use_env": self.use_env_checkbox.isChecked(),
            "anon_key": self.anon_key_edit.text().strip(),
            "service_role_key": self.service_key_edit.text().strip(),
        }

    def _save_current_form_to_profile(self):
        """Save current form data to the selected profile."""
        current_item = self.profile_list.currentItem()
        if not current_item or not self.current_profile_name:
            return

        # Get form data
        form_data = self._get_profile_from_form()

        # Update profile in list
        for i, profile in enumerate(self.profiles):
            if profile.get("name") == self.current_profile_name:
                self.profiles[i].update(form_data)
                break

        # Update item data
        current_item.setData(Qt.ItemDataRole.UserRole, form_data.copy())

        # Update item text
        name = form_data["name"]
        if form_data.get("use_env"):
            current_item.setText(f"{name} (env)")
        else:
            current_item.setText(name)

        # If using environment variables, save to .env file immediately
        if form_data.get("use_env") and form_data.get("name"):
            credentials = {
                "url": form_data.get("url", ""),
                "anon_key": form_data.get("anon_key", ""),
                "service_key": form_data.get("service_role_key", ""),
            }
            # Only save non-empty values
            credentials = {k: v for k, v in credentials.items() if v.strip()}
            if credentials:
                self.env_manager.set_env_vars_for_profile(
                    form_data["name"], credentials
                )
                # Reload the env display
                self.reload_env_display()
                print(f"Saved credentials to .env for profile: {form_data['name']}")

    def _rebuild_active_combo(self):
        """Rebuild the active profile combo box."""
        current_active = self.config.get_active_supabase_connection_name()
        self.active_profile_combo.clear()
        self.active_profile_combo.addItem("None")

        for profile in self.profiles:
            name = profile.get("name", "")
            if name:
                self.active_profile_combo.addItem(name)

        # Set current selection
        if current_active:
            index = self.active_profile_combo.findText(current_active)
            if index >= 0:
                self.active_profile_combo.setCurrentIndex(index)

    def add_new_profile(self):
        """Add a new profile."""
        self._save_current_form_to_profile()

        # Generate unique name
        base_name = "NewProfile"
        counter = 1
        while any(p.get("name") == f"{base_name}{counter}" for p in self.profiles):
            counter += 1

        profile_name = f"{base_name}{counter}"

        # Create new profile
        new_profile = {
            "name": profile_name,
            "url": "",
            "use_env": False,
            "anon_key": "",
            "service_role_key": "",
        }

        # Add to profiles list
        self.profiles.append(new_profile)

        # Add to list widget
        item = QListWidgetItem(profile_name)
        item.setData(Qt.ItemDataRole.UserRole, new_profile.copy())
        self.profile_list.addItem(item)

        # Select the new item
        self._rebuild_active_combo()
        self.profile_list.setCurrentItem(item)
        self.set_form_enabled(True)

    def add_env_profile(self):
        """Add a new environment-based profile."""
        self._save_current_form_to_profile()

        # Generate unique name
        base_name = "EnvProfile"
        counter = 1
        while any(p.get("name") == f"{base_name}{counter}" for p in self.profiles):
            counter += 1

        profile_name = f"{base_name}{counter}"

        # Create environment-based profile
        new_profile = {
            "name": profile_name,
            "url": "",
            "use_env": True,
            "anon_key": "",
            "service_role_key": "",
        }

        # Add to profiles list
        self.profiles.append(new_profile)

        # Add to list widget
        item = QListWidgetItem(f"{profile_name} (env)")
        item.setData(Qt.ItemDataRole.UserRole, new_profile.copy())
        self.profile_list.addItem(item)

        # Select the new item
        self._rebuild_active_combo()
        self.profile_list.setCurrentItem(item)
        self.set_form_enabled(True)

    def delete_selected_profile(self):
        """Delete the selected profile."""
        current_item = self.profile_list.currentItem()
        if not current_item:
            return

        profile = current_item.data(Qt.ItemDataRole.UserRole)
        profile_name = profile.get("name", "")

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Are you sure you want to delete the profile '{profile_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Remove from profiles list
        self.profiles = [p for p in self.profiles if p.get("name") != profile_name]

        # Remove from list widget
        row = self.profile_list.row(current_item)
        self.profile_list.takeItem(row)

        # Remove from environment if it was an env profile
        if profile.get("use_env"):
            self.env_manager.remove_profile_env_vars(profile_name)
            self.reload_env_display()

        # Clear form and rebuild combo
        self.clear_form()
        self.set_form_enabled(False)
        self._rebuild_active_combo()

    def save_profiles(self):
        """Save all profiles and environment changes."""
        try:
            # Save current form data first
            self._save_current_form_to_profile()

            # Save all environment profiles to .env file
            for profile in self.profiles:
                if profile.get("use_env") and profile.get("name"):
                    credentials = {
                        "url": profile.get("url", ""),
                        "anon_key": profile.get("anon_key", ""),
                        "service_key": profile.get("service_role_key", ""),
                    }
                    # Only save non-empty values
                    credentials = {k: v for k, v in credentials.items() if v.strip()}
                    if credentials:
                        self.env_manager.set_env_vars_for_profile(
                            profile["name"], credentials
                        )

            # Save environment file changes if modified in the editor tab
            try:
                env_content = self.env_editor.toPlainText()
                env_path = self.env_manager.get_env_file_path()
                current_content = env_path.read_text() if env_path.exists() else ""

                # Only write if content actually changed
                if env_content != current_content:
                    env_path.write_text(env_content)
                    print("Environment file updated from editor tab")

                # Reload environment after saving
                self.env_manager.reload()
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Environment Save Warning",
                    f"Failed to save environment file changes: {e}\n\nProfile changes will still be saved.",
                )

            # Clean and save profiles
            clean_profiles = []
            for profile in self.profiles:
                name = profile.get("name", "").strip()
                if name:
                    clean_profiles.append(profile.copy())

            # Update config
            self.config.config["supabase_connections"] = clean_profiles

            # Save active profile selection
            active_text = self.active_profile_combo.currentText()
            active_name = active_text if active_text != "None" else None
            self.config.set_active_supabase_connection_name(active_name)

            # Save to disk
            self.config.save_config()

            # Emit signal that profiles changed
            self.profiles_changed.emit()

            # Reload the env display to show final state
            self.reload_env_display()

            # Show success message with more details
            env_profiles = [p for p in self.profiles if p.get("use_env")]
            success_msg = f"Configuration saved successfully!\n\n"
            success_msg += f"Environment file: {self.env_manager.get_env_file_path()}\n"
            success_msg += f"Environment profiles: {len(env_profiles)}\n"
            success_msg += f"Total profiles: {len(clean_profiles)}\n"
            success_msg += f"Active profile: {active_name or 'None'}"

            QMessageBox.information(
                self,
                "Configuration Saved",
                success_msg,
            )

            # Close dialog
            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Failed to save configuration:\n{str(e)}"
            )

    def test_connection(self):
        """Test the connection for the current profile."""
        current_item = self.profile_list.currentItem()
        if not current_item:
            self.status_label.setText("No profile selected.")
            return

        profile = self._get_profile_from_form()
        profile_name = profile.get("name", "")

        self.status_label.setText("Testing connection...")

        try:
            from supabase import create_client

            # Get credentials
            if profile.get("use_env"):
                env_vars = self.env_manager.get_env_vars_for_profile(profile_name)
                url = env_vars.get("url")
                anon_key = env_vars.get("anon_key")
            else:
                url = profile.get("url")
                anon_key = profile.get("anon_key")

            if not url or not anon_key:
                missing = []
                if not url:
                    missing.append("URL")
                if not anon_key:
                    missing.append("Anon Key")
                self.status_label.setText(
                    f"❌ Missing credentials: {', '.join(missing)}"
                )
                return

            # Test connection
            client = create_client(url, anon_key)

            # Try a simple operation
            response = client.table("_test_connection_").select("*").limit(1).execute()
            self.status_label.setText("✅ Connection successful!")

        except Exception as e:
            error_msg = str(e)
            if "relation" in error_msg and "does not exist" in error_msg:
                self.status_label.setText(
                    "✅ Connection successful! (Test table doesn't exist, but auth works)"
                )
            elif "Invalid API key" in error_msg or "unauthorized" in error_msg.lower():
                self.status_label.setText(
                    "❌ Authentication failed. Check your API key."
                )
            elif "not found" in error_msg.lower() or "404" in error_msg:
                self.status_label.setText("❌ Project not found. Check your URL.")
            else:
                self.status_label.setText(f"❌ Connection failed: {error_msg}")

    def debug_connection(self):
        """Show detailed connection debug information."""
        current_item = self.profile_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Debug", "No profile selected.")
            return

        profile = self._get_profile_from_form()
        profile_name = profile.get("name", "")

        debug_info = []
        debug_info.append(f"Profile: {profile_name}")
        debug_info.append(f"Use Environment: {profile.get('use_env', False)}")

        if profile.get("use_env"):
            env_vars = self.env_manager.get_env_vars_for_profile(profile_name)
            debug_info.append("\nEnvironment Variables:")
            profile_upper = profile_name.upper()

            for var_type, env_value in env_vars.items():
                var_name = f"SUPABASE_{profile_upper}_{var_type.upper()}"
                if env_value:
                    debug_info.append(
                        f"  {var_name}: {'*' * 20}...{env_value[-4:] if len(env_value) > 4 else '****'}"
                    )
                else:
                    debug_info.append(f"  {var_name}: (not set)")
        else:
            debug_info.append("\nDirect Configuration:")
            url = profile.get("url", "")
            anon_key = profile.get("anon_key", "")

            if url:
                debug_info.append(f"  URL: {url}")
            else:
                debug_info.append("  URL: (not set)")

            if anon_key:
                debug_info.append(
                    f"  Anon Key: {'*' * 20}...{anon_key[-4:] if len(anon_key) > 4 else '****'}"
                )
            else:
                debug_info.append("  Anon Key: (not set)")

        # Validation
        if profile.get("use_env"):
            is_valid, missing = self.env_manager.validate_profile_credentials(
                profile_name
            )
        else:
            missing = []
            if not profile.get("url"):
                missing.append("URL")
            if not profile.get("anon_key"):
                missing.append("Anon Key")
            is_valid = len(missing) == 0

        debug_info.append(f"\nValidation: {'✅ Valid' if is_valid else '❌ Invalid'}")
        if missing:
            debug_info.append(f"Missing: {', '.join(missing)}")

        # Environment file info
        debug_info.append(f"\nEnvironment File: {self.env_manager.get_env_file_path()}")
        debug_info.append(
            f"File Exists: {self.env_manager.get_env_file_path().exists()}"
        )

        QMessageBox.information(self, "Connection Debug", "\n".join(debug_info))

    def clear_form(self):
        """Clear all form fields."""
        self.name_edit.clear()
        self.url_edit.clear()
        self.anon_key_edit.clear()
        self.service_key_edit.clear()
        self.use_env_checkbox.setChecked(False)
        self.status_label.clear()

    def set_form_enabled(self, enabled):
        """Enable or disable form fields."""
        self.name_edit.setEnabled(enabled)
        self.url_edit.setEnabled(enabled)
        self.anon_key_edit.setEnabled(enabled)
        self.service_key_edit.setEnabled(enabled)
        self.use_env_checkbox.setEnabled(enabled)
