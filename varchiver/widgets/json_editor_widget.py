from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QFileDialog, QMessageBox, QHeaderView, QLabel, QTextEdit
from PyQt6.QtCore import Qt
import json
import os

# Attempt to import jsonschema and set a flag
JSONSCHEMA_AVAILABLE = False
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    print("WARNING: jsonschema library not found. Formal schema validation will be disabled. Pip install jsonschema to enable.")

class JsonEditorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JSON Editor")
        self._data = None  # To store the loaded JSON data
        self._current_file_path = None
        self._is_populating = False # Flag to prevent itemChanged during population
        self._current_schema = None # To store the loaded JSON schema
        self._current_schema_path = None # Path to the loaded schema file
        self._inferred_model_structure = None # For inferred structure

        main_layout = QVBoxLayout(self)

        # Toolbar for file operations
        file_toolbar_layout = QHBoxLayout()
        self.open_button = QPushButton("Open JSON File")
        self.open_button.clicked.connect(self.open_file_dialog)
        file_toolbar_layout.addWidget(self.open_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_file)
        self.save_button.setEnabled(False)
        file_toolbar_layout.addWidget(self.save_button)
        
        self.save_as_button = QPushButton("Save As...")
        self.save_as_button.clicked.connect(self.save_as_file_dialog)
        self.save_as_button.setEnabled(False)
        file_toolbar_layout.addWidget(self.save_as_button)
        main_layout.addLayout(file_toolbar_layout)

        # Toolbar for schema operations & inference
        validation_toolbar_layout = QHBoxLayout()
        self.load_schema_button = QPushButton("Load Schema")
        self.load_schema_button.clicked.connect(self.load_schema_dialog)
        validation_toolbar_layout.addWidget(self.load_schema_button)

        self.validate_button = QPushButton("Validate (Schema)")
        self.validate_button.clicked.connect(self.validate_document_with_schema)
        self.validate_button.setEnabled(False)
        validation_toolbar_layout.addWidget(self.validate_button)

        self.infer_check_button = QPushButton("Infer & Check Structure")
        self.infer_check_button.clicked.connect(self.infer_and_check_structure)
        self.infer_check_button.setEnabled(False) # Enabled when document is loaded
        validation_toolbar_layout.addWidget(self.infer_check_button)
        
        self.schema_name_label = QLabel("Schema: None")
        validation_toolbar_layout.addWidget(self.schema_name_label)
        validation_toolbar_layout.addStretch()
        main_layout.addLayout(validation_toolbar_layout)

        # JSON Tree View
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Key/Index", "Value", "Type"])
        self.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_widget.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree_widget.itemChanged.connect(self._handle_item_changed)
        main_layout.addWidget(self.tree_widget)

        # Validation/Error Display
        self.error_display = QTextEdit()
        self.error_display.setReadOnly(True)
        self.error_display.setPlaceholderText("Validation or structural check results will appear here.")
        self.error_display.setFixedHeight(150) # Slightly taller
        main_layout.addWidget(self.error_display)

        if not JSONSCHEMA_AVAILABLE:
            self.load_schema_button.setEnabled(False)
            self.load_schema_button.setToolTip("jsonschema library not installed.")
            self.validate_button.setEnabled(False)
            self.validate_button.setToolTip("jsonschema library not installed.")
            self.schema_name_label.setText("Schema: (jsonschema not installed)")
            self.error_display.setText("Formal schema validation is disabled because the 'jsonschema' library was not found.\\nTo enable it, please install the library (e.g., 'pip install jsonschema').\\n\\nYou can still use 'Infer & Check Structure' for basic structural consistency checks.")


    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open JSON File", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            self.load_json_file(file_path)

    def load_json_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
            self._current_file_path = file_path
            self.setWindowTitle(f"JSON Editor - {os.path.basename(file_path)}")
            self.populate_tree()
            self.save_button.setEnabled(True)
            self.save_as_button.setEnabled(True)
            self.infer_check_button.setEnabled(True) # Enable infer button
            if not JSONSCHEMA_AVAILABLE: # Preserve message if jsonschema is missing
                if not self.error_display.toPlainText().startswith("Formal schema validation is disabled"):
                    self.error_display.clear()
            else:
                 self.error_display.clear()
            self._update_validate_button_state()
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Error Loading JSON", f"Failed to decode JSON: {e}")
            self._data = None
            self._current_file_path = None
            self.tree_widget.clear()
            self.save_button.setEnabled(False)
            self.save_as_button.setEnabled(False)
            self.infer_check_button.setEnabled(False)
            self._update_validate_button_state()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
            self._data = None
            self._current_file_path = None
            self.tree_widget.clear()
            self.save_button.setEnabled(False)
            self.save_as_button.setEnabled(False)
            self.infer_check_button.setEnabled(False)
            self._update_validate_button_state()

    def load_schema_dialog(self):
        if not JSONSCHEMA_AVAILABLE: return
        file_path, _ = QFileDialog.getOpenFileName(self, "Load JSON Schema", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self._current_schema = json.load(f)
                self._current_schema_path = file_path
                self.schema_name_label.setText(f"Schema: {os.path.basename(file_path)}")
                QMessageBox.information(self, "Schema Loaded", f"Schema '{os.path.basename(file_path)}' loaded successfully.")
                self.error_display.clear()
            except json.JSONDecodeError as e:
                QMessageBox.critical(self, "Error Loading Schema", f"Failed to decode JSON schema: {e}")
                self._current_schema = None
                self._current_schema_path = None
                self.schema_name_label.setText("Schema: None")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while loading schema: {e}")
                self._current_schema = None
                self._current_schema_path = None
                self.schema_name_label.setText("Schema: None")
            self._update_validate_button_state()

    def validate_document_with_schema(self):
        if not JSONSCHEMA_AVAILABLE: return
        if self._data is None:
            QMessageBox.warning(self, "No JSON Loaded", "Please load a JSON document first.")
            return
        if self._current_schema is None:
            QMessageBox.warning(self, "No Schema Loaded", "Please load a JSON schema first.")
            return

        self.error_display.clear()
        try:
            validator = jsonschema.Draft7Validator(self._current_schema)
            errors = sorted(validator.iter_errors(self._data), key=str)

            if not errors:
                self.error_display.setText("Validation successful: Document conforms to the schema.")
                QMessageBox.information(self, "Validation Success", "Document conforms to the schema.")
            else:
                error_messages = [f"Validation Error at `{' -> '.join(map(str, e.path))}`: {e.message}" for e in errors]
                self.error_display.setText("\\n\\n".join(error_messages))
                QMessageBox.warning(self, "Validation Failed", f"{len(errors)} error(s) found. See details below the tree view.")
        except jsonschema.SchemaError as e:
            self.error_display.setText(f"Invalid Schema: {e.message}")
            QMessageBox.critical(self, "Schema Error", f"The loaded schema is invalid: {e.message}")
        except Exception as e:
            self.error_display.setText(f"An unexpected error occurred during validation: {e}")
            QMessageBox.critical(self, "Validation Error", f"An unexpected error occurred: {e}")
            
    def _update_validate_button_state(self):
        if JSONSCHEMA_AVAILABLE and self._data is not None and self._current_schema is not None:
            self.validate_button.setEnabled(True)
        else:
            self.validate_button.setEnabled(False)
        
        if self._data is not None:
            self.infer_check_button.setEnabled(True)
        else:
            self.infer_check_button.setEnabled(False)

    def infer_and_check_structure(self):
        if self._data is None:
            QMessageBox.warning(self, "No JSON Data", "Please load a JSON document first.")
            return

        self.error_display.clear()
        self._inferred_model_structure = None
        results = []

        if isinstance(self._data, list):
            if not self._data:
                self.error_display.setText("JSON array is empty. Cannot infer structure.")
                return

            first_item = self._data[0]
            if not isinstance(first_item, dict):
                self.error_display.setText("Structural inference and check is designed for JSON arrays of objects. The first item is not an object.")
                return

            self._inferred_model_structure = {key: type(value).__name__ for key, value in first_item.items()}
            results.append(f"Inferred structure from first item (Index 0):\\n{json.dumps(self._inferred_model_structure, indent=2)}\\n")

            if len(self._data) > 1:
                for i, item in enumerate(self._data[1:], start=1):
                    if not isinstance(item, dict):
                        results.append(f"Item at Index {i}: SKIPPED - Not an object (type: {type(item).__name__}).")
                        continue

                    item_structure = {key: type(value).__name__ for key, value in item.items()}
                    
                    model_keys = set(self._inferred_model_structure.keys())
                    item_keys = set(item_structure.keys())

                    missing_keys = model_keys - item_keys
                    extra_keys = item_keys - model_keys
                    common_keys = model_keys.intersection(item_keys)
                    type_mismatches = {}

                    for key in common_keys:
                        if self._inferred_model_structure[key] != item_structure[key]:
                            type_mismatches[key] = f"Expected type '{self._inferred_model_structure[key]}', found '{item_structure[key]}'"
                    
                    if missing_keys or extra_keys or type_mismatches:
                        results.append(f"--- Item at Index {i} ---")
                        if missing_keys: results.append(f"  Missing keys: {', '.join(sorted(list(missing_keys)))}")
                        if extra_keys: results.append(f"  Extra keys: {', '.join(sorted(list(extra_keys)))}")
                        if type_mismatches:
                            results.append("  Type mismatches:")
                            for k, v_err in type_mismatches.items():
                                results.append(f"    '{k}': {v_err}")
                if not any(res.startswith("--- Item at Index") for res in results):
                     results.append("\\nAll subsequent items match the inferred structure from the first item.")
            else:
                results.append("\\nOnly one item in the array; structure noted.")

        elif isinstance(self._data, dict):
            self._inferred_model_structure = {key: type(value).__name__ for key, value in self._data.items()}
            results.append(f"Document is a single object. Inferred structure:\\n{json.dumps(self._inferred_model_structure, indent=2)}")
            results.append("\\nStructural check is most useful for arrays of objects.")
        else:
            self.error_display.setText(f"Data is not a JSON array or object (type: {type(self._data).__name__}). Cannot infer structure.")
            return
        
        self.error_display.setText("\\n".join(results))
        if any(res.startswith("--- Item at Index") for res in results):
            QMessageBox.warning(self, "Structural Differences Found", "Differences found against the first item's structure. See details below.")
        elif isinstance(self._data, list) and len(self._data) > 0:
             QMessageBox.information(self, "Structure Check Complete", "All items appear structurally consistent with the first item.")

    def populate_tree(self):
        self.tree_widget.clear()
        if self._data is not None:
            self._is_populating = True # Set flag before populating
            try:
                self._add_items(self.tree_widget, self._data)
            finally:
                self._is_populating = False # Unset flag after populating

    def _add_items(self, parent_item_or_widget, value):
        if isinstance(value, dict):
            for key, val in value.items():
                child_item = QTreeWidgetItem(parent_item_or_widget)
                child_item.setText(0, str(key))
                child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsEditable if not isinstance(val, (dict, list)) else child_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                child_item.setData(0, Qt.ItemDataRole.UserRole, key) # Store original key
                if isinstance(val, (dict, list)):
                    child_item.setText(1, "") # No value for parent nodes in value column
                    child_item.setText(2, "object" if isinstance(val, dict) else "array")
                    self._add_items(child_item, val)
                else:
                    child_item.setText(1, str(val) if val is not None else "null")
                    child_item.setText(2, self._get_type_string(val))
        elif isinstance(value, list):
            for index, val in enumerate(value):
                child_item = QTreeWidgetItem(parent_item_or_widget)
                child_item.setText(0, str(index))
                child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsEditable if not isinstance(val, (dict, list)) else child_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                child_item.setData(0, Qt.ItemDataRole.UserRole, index) # Store original index
                if isinstance(val, (dict, list)):
                    child_item.setText(1, "")
                    child_item.setText(2, "object" if isinstance(val, dict) else "array")
                    self._add_items(child_item, val)
                else:
                    child_item.setText(1, str(val) if val is not None else "null")
                    child_item.setText(2, self._get_type_string(val))
        else: # Should not happen for root if JSON is valid, but handle for completeness
            item = QTreeWidgetItem(parent_item_or_widget)
            item.setText(0, "Value")
            item.setText(1, str(value))
            item.setText(2, self._get_type_string(value))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            
    def _get_type_string(self, value):
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int): # Keep int and float distinct if possible
            return "integer"
        elif isinstance(value, float):
            return "number" # JSON schema often uses "number" for float/double
        elif isinstance(value, str):
            return "string"
        # Fallback for other complex types not directly representable or if jsonschema not used.
        # For schema inference, type(value).__name__ is more precise.
        # For tree display, aligning with JSON types (string, number, boolean, object, array, null) is good.
        return type(value).__name__

    def _handle_item_changed(self, item, column):
        if self._is_populating: # Check flag
            return

        if column == 1: # Value column changed
            if not self._data:
                return

            path = []
            current = item
            while current:
                parent = current.parent()
                if parent:
                    key_or_index = current.data(0, Qt.ItemDataRole.UserRole)
                    path.insert(0, key_or_index)
                else: 
                    pass 
                current = parent
            
            data_node = self._data 
            
            for i, p_item in enumerate(path[:-1]):
                if isinstance(data_node, list) and isinstance(p_item, int) and p_item < len(data_node):
                    data_node = data_node[p_item]
                elif isinstance(data_node, dict) and p_item in data_node:
                    data_node = data_node[p_item]
                else:
                    print(f"Error: Path item '{p_item}' not found or invalid type in data structure at path {path[:i+1]}.")
                    return
            
            try:
                original_key_or_index = path[-1]
                new_value_str = item.text(1)
                
                original_value = None
                if isinstance(data_node, dict) and original_key_or_index in data_node:
                    original_value = data_node[original_key_or_index]
                elif isinstance(data_node, list) and isinstance(original_key_or_index, int) and original_key_or_index < len(data_node):
                     original_value = data_node[original_key_or_index]
                else:
                    print(f"Warning: Could not find original_key_or_index '{original_key_or_index}' in data_node for path {path}")

                new_value = None
                if new_value_str == "null":
                    new_value = None
                elif new_value_str.lower() == "true":
                    new_value = True
                elif new_value_str.lower() == "false":
                    new_value = False
                else:
                    try:
                        if isinstance(original_value, int) and not ('.' in new_value_str or 'e' in new_value_str.lower()): # Try to keep int if it was int
                            new_value = int(new_value_str)
                        elif isinstance(original_value, float):
                            new_value = float(new_value_str)
                        # If original was string or type is ambiguous or new
                        elif '.' in new_value_str or 'e' in new_value_str.lower():
                             new_value = float(new_value_str)
                        else: 
                            new_value = int(new_value_str)
                    except ValueError:
                        new_value = new_value_str 

                if isinstance(data_node, dict):
                    data_node[original_key_or_index] = new_value
                elif isinstance(data_node, list) and isinstance(original_key_or_index, int):
                    if original_key_or_index < len(data_node):
                        data_node[original_key_or_index] = new_value
                    else:
                        print(f"Error: Index {original_key_or_index} out of bounds for list data_node.")
                        return
                else:
                    print(f"Error: data_node is not a dict or list, or key/index '{original_key_or_index}' is invalid type.")
                    return

                self.tree_widget.blockSignals(True)
                item.setText(2, self._get_type_string(new_value))
                self.tree_widget.blockSignals(False)

            except Exception as e:
                print(f"Error updating data from tree: {e}, Path: {path}")
                self.tree_widget.blockSignals(False)


    def _build_data_from_tree(self, parent_widget_item=None):
        if parent_widget_item is None:
            count = self.tree_widget.topLevelItemCount()
            if count == 0:
                return None 

            is_list_root = True
            if count > 0:
                for i in range(count):
                    item = self.tree_widget.topLevelItem(i)
                    key_text = item.text(0)
                    if not (key_text.isdigit() and int(key_text) == i):
                        is_list_root = False
                        break
            else: 
                if isinstance(self._data, list): 
                    return []
                return {}


            if is_list_root:
                data = []
                for i in range(count):
                    data.append(self._build_data_from_tree_item(self.tree_widget.topLevelItem(i)))
            else:
                data = {}
                for i in range(count):
                    item = self.tree_widget.topLevelItem(i)
                    key = item.text(0) 
                    data[key] = self._build_data_from_tree_item(item)
            return data
        
        return None 


    def _build_data_from_tree_item(self, tree_item):
        num_children = tree_item.childCount()
        item_type_text = tree_item.text(2) 

        if item_type_text == "object":
            obj = {}
            for i in range(num_children):
                child = tree_item.child(i)
                key = child.text(0) 
                obj[key] = self._build_data_from_tree_item(child)
            return obj
        elif item_type_text == "array":
            arr = []
            for i in range(num_children):
                child = tree_item.child(i)
                arr.append(self._build_data_from_tree_item(child))
            return arr
        else: 
            value_str = tree_item.text(1) 
            if item_type_text == "null": return None
            if item_type_text == "boolean": return value_str.lower() == 'true'
            if item_type_text == "integer": # Distinguish from general "number"
                try: return int(value_str)
                except ValueError: return value_str # fallback
            if item_type_text == "number": # Typically float from JSON schema perspective
                try:
                    if '.' in value_str or 'e' in value_str.lower():
                        return float(value_str)
                    return int(value_str) # If it looks like an int, parse as int
                except ValueError:
                    return value_str 
            return value_str


    def save_file_content(self, file_path):
        data_to_save = self._data 

        if data_to_save is None : 
            QMessageBox.warning(self, "No Data", "No data loaded to save.")
            return False
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            self._current_file_path = file_path
            self.setWindowTitle(f"JSON Editor - {os.path.basename(file_path)}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error Saving File", f"Could not save file: {e}")
            return False

    def save_file(self):
        if self._current_file_path:
            self.save_file_content(self._current_file_path)
        else:
            self.save_as_file_dialog()

    def save_as_file_dialog(self):
        if self._data is None: 
            QMessageBox.warning(self, "No Data", "No data loaded to save.")
            return

        default_name = os.path.basename(self._current_file_path) if self._current_file_path else "untitled.json"
        default_dir = os.path.dirname(self._current_file_path) if self._current_file_path else os.getcwd() 
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Save JSON File As...", 
                                                   os.path.join(default_dir, default_name),
                                                   "JSON Files (*.json);;All Files (*)")
        if file_path:
            self.save_file_content(file_path) 