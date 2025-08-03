import sys
import json
import csv
import io
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QFileDialog, QMessageBox, QLineEdit, QComboBox,
    QTextEdit, QLabel, QSplitter, QGroupBox, QFormLayout, QCheckBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
    QDialog, QDialogButtonBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QFont


class ColumnMappingDialog(QDialog):
    """Dialog for mapping CSV columns to glossary fields"""

    def __init__(self, csv_columns: List[str], parent=None):
        super().__init__(parent)
        self.csv_columns = csv_columns
        self.mapping = {}
        self.comparison_key = 'term'
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Map CSV Columns")
        self.setFixedSize(500, 400)

        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel("Map your CSV columns to glossary fields:")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Mapping form
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)

        # Standard glossary fields
        self.field_mappings = {}
        glossary_fields = [
            ('term', 'Term (Primary Key)', True),
            ('type', 'Type/Category Type', False),
            ('category', 'Category', False),
            ('description', 'Description', False),
            ('source', 'Source', False),
            ('related_terms', 'Related Terms (semicolon-separated)', False),
            ('etymology_notes', 'Etymology Notes', False)
        ]

        for field, label, required in glossary_fields:
            combo = QComboBox()
            combo.addItem("-- Skip --")
            combo.addItems(self.csv_columns)

            # Try to auto-detect matching columns
            for i, col in enumerate(self.csv_columns):
                if field.lower() in col.lower() or col.lower() in field.lower():
                    combo.setCurrentIndex(i + 1)
                    break

            self.field_mappings[field] = combo

            if required:
                label += " *"
            form_layout.addRow(label, combo)

        layout.addWidget(form_widget)

        # Comparison key selection
        key_group = QGroupBox("Comparison Key for CSV Merging")
        key_layout = QVBoxLayout(key_group)

        self.key_combo = QComboBox()
        self.key_combo.addItems(['term', 'id', 'name', 'title'])
        key_layout.addWidget(QLabel("Field to use as unique identifier:"))
        key_layout.addWidget(self.key_combo)

        layout.addWidget(key_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_mapping(self) -> Tuple[Dict[str, str], str]:
        """Returns (field_mapping, comparison_key)"""
        mapping = {}
        for field, combo in self.field_mappings.items():
            if combo.currentIndex() > 0:  # Not "-- Skip --"
                csv_column = combo.currentText()
                mapping[field] = csv_column

        comparison_key = self.key_combo.currentText()
        return mapping, comparison_key


class CsvStructureDetector:
    """Utility class for detecting and analyzing CSV structure"""

    @staticmethod
    def detect_structure(file_path: Path) -> Dict[str, Any]:
        """Analyze CSV structure and return metadata"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read first few lines to detect structure
                sample = f.read(8192)
                f.seek(0)

                # Detect delimiter
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter

                # Get column names
                reader = csv.DictReader(f, delimiter=delimiter)
                columns = list(reader.fieldnames) if reader.fieldnames else []

                # Count rows
                f.seek(0)
                row_count = sum(1 for _ in reader) if columns else 0

                # Detect potential key columns
                potential_keys = []
                for col in columns:
                    col_lower = col.lower()
                    if any(key_word in col_lower for key_word in ['id', 'key', 'term', 'name', 'title']):
                        potential_keys.append(col)

                return {
                    'columns': columns,
                    'delimiter': delimiter,
                    'row_count': row_count,
                    'potential_keys': potential_keys,
                    'encoding': 'utf-8'
                }
        except Exception as e:
            return {
                'error': str(e),
                'columns': [],
                'delimiter': ',',
                'row_count': 0,
                'potential_keys': []
            }

    @staticmethod
    def preview_data(file_path: Path, max_rows: int = 5) -> List[Dict[str, str]]:
        """Get a preview of CSV data"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)[:max_rows]
        except Exception:
            return []


class GlossaryEntry:
    """Data class for glossary entries"""
    def __init__(self, term: str = "", entry_type: str = "", category: str = "",
                 description: str = "", source: str = "",
                 related_terms: List[str] = None, etymology_notes: str = ""):
        self.term = term
        self.type = entry_type
        self.category = category
        self.description = description
        self.source = source
        self.related_terms = related_terms or []
        self.etymology_notes = etymology_notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            'term': self.term,
            'type': self.type,
            'category': self.category,
            'description': self.description,
            'source': self.source,
            'related_terms': self.related_terms,
            'etymology_notes': self.etymology_notes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlossaryEntry':
        return cls(
            term=data.get('term', ''),
            entry_type=data.get('type', ''),
            category=data.get('category', ''),
            description=data.get('description', ''),
            source=data.get('source', ''),
            related_terms=data.get('related_terms', []),
            etymology_notes=data.get('etymology_notes', '')
        )


class GlossaryEntryDialog(QDialog):
    """Dialog for editing individual glossary entries"""

    def __init__(self, entry: GlossaryEntry = None, existing_terms: List[str] = None, parent=None):
        super().__init__(parent)
        self.entry = entry or GlossaryEntry()
        self.existing_terms = existing_terms or []
        self.init_ui()
        self.populate_fields()

    def init_ui(self):
        self.setWindowTitle("Edit Glossary Entry")
        self.setModal(True)
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # Main form
        form_layout = QFormLayout()

        self.term_edit = QLineEdit()
        form_layout.addRow("Term:", self.term_edit)

        self.type_combo = QComboBox()
        self.type_combo.setEditable(True)
        self.type_combo.addItems([
            "Core Technology", "System", "Utility", "Weapon", "Tool", "Consumable",
            "Faction", "Location", "Concept", "Entity", "Knowledge", "Material",
            "Currency", "Enemy", "Pet", "Movement", "Effect", "Language",
            "Architecture", "Style", "Information", "Magic System", "Propulsion",
            "Power", "Defense", "Trap", "Augment", "Field", "Thermal", "Interface"
        ])
        form_layout.addRow("Type:", self.type_combo)

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems([
            "Foundation", "Core", "World", "Fishing", "Trapping", "Hybrid"
        ])
        form_layout.addRow("Category:", self.category_combo)

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.description_edit.setPlaceholderText("Brief description of the term")
        form_layout.addRow("Description:", self.description_edit)

        self.source_combo = QComboBox()
        self.source_combo.setEditable(True)
        self.source_combo.addItems(["varchiver", "naming", "new", "loreum"])
        form_layout.addRow("Source:", self.source_combo)

        self.related_terms_edit = QTextEdit()
        self.related_terms_edit.setMaximumHeight(80)
        self.related_terms_edit.setPlaceholderText("Enter related terms separated by semicolons")
        form_layout.addRow("Related Terms:", self.related_terms_edit)

        self.etymology_edit = QTextEdit()
        self.etymology_edit.setMaximumHeight(80)
        self.etymology_edit.setPlaceholderText("Etymology notes (optional)")
        form_layout.addRow("Etymology Notes:", self.etymology_edit)

        layout.addLayout(form_layout)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def populate_fields(self):
        """Populate form with entry data"""
        self.term_edit.setText(self.entry.term)
        self.type_combo.setCurrentText(self.entry.type)
        self.category_combo.setCurrentText(self.entry.category)
        self.description_edit.setPlainText(self.entry.description)
        self.source_combo.setCurrentText(self.entry.source)
        self.related_terms_edit.setPlainText('; '.join(self.entry.related_terms))
        self.etymology_edit.setPlainText(self.entry.etymology_notes)

    def get_entry(self) -> GlossaryEntry:
        """Get the entry with form data"""
        related_terms = [term.strip() for term in self.related_terms_edit.toPlainText().split(';') if term.strip()]

        return GlossaryEntry(
            term=self.term_edit.text().strip(),
            entry_type=self.type_combo.currentText().strip(),
            category=self.category_combo.currentText().strip(),
            description=self.description_edit.toPlainText().strip(),
            source=self.source_combo.currentText().strip(),
            related_terms=related_terms,
            etymology_notes=self.etymology_edit.toPlainText().strip()
        )


class GlossaryManagerWidget(QWidget):
    """Main widget for managing glossary entries"""

    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.glossary_data: Dict[str, GlossaryEntry] = {}
        self.current_file: Optional[Path] = None
        self.item_database_path: Optional[Path] = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)

        # Toolbar
        # File operations toolbar
        file_toolbar_layout = QHBoxLayout()

        # Primary actions (most common)
        self.open_csv_btn = QPushButton("Open CSV")
        self.open_csv_btn.clicked.connect(self.open_csv_file)
        self.open_csv_btn.setToolTip("Load glossary from CSV file")
        file_toolbar_layout.addWidget(self.open_csv_btn)

        self.save_csv_btn = QPushButton("Save CSV")
        self.save_csv_btn.clicked.connect(self.save_csv_file)
        self.save_csv_btn.setEnabled(False)
        self.save_csv_btn.setToolTip("Save current glossary to CSV file")
        file_toolbar_layout.addWidget(self.save_csv_btn)

        file_toolbar_layout.addWidget(QLabel("|"))  # Separator



        file_toolbar_layout.addStretch()

        # Utility actions (right side)
        self.new_btn = QPushButton("New CSV")
        self.new_btn.clicked.connect(self.new_glossary)
        self.new_btn.setToolTip("Create new empty CSV glossary")
        file_toolbar_layout.addWidget(self.new_btn)

        layout.addLayout(file_toolbar_layout)

        # Search and filter row
        search_layout = QHBoxLayout()

        # Search box (prominent)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search terms and descriptions...")
        self.search_edit.textChanged.connect(self.filter_entries)
        search_layout.addWidget(self.search_edit)

        # Filter dropdowns (compact)
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types")
        self.type_filter.currentTextChanged.connect(self.filter_entries)
        self.type_filter.setToolTip("Filter by term type")
        search_layout.addWidget(self.type_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem("All Status")
        self.status_filter.currentTextChanged.connect(self.filter_entries)
        self.status_filter.setToolTip("Filter by implementation status")
        search_layout.addWidget(self.status_filter)

        layout.addLayout(search_layout)

        # Tools row (secondary actions)
        tools_layout = QHBoxLayout()

        self.set_db_btn = QPushButton("Set Item Database")
        self.set_db_btn.clicked.connect(self.set_item_database)
        self.set_db_btn.setToolTip("Point to JSON item database for status inference")
        tools_layout.addWidget(self.set_db_btn)

        self.compare_csv_btn = QPushButton("Compare CSV Files")
        self.compare_csv_btn.clicked.connect(self.compare_csv_files)
        self.compare_csv_btn.setToolTip("Compare two CSV files with flexible column mapping")
        tools_layout.addWidget(self.compare_csv_btn)

        tools_layout.addStretch()
        layout.addLayout(tools_layout)

        # Main content area
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - entry list
        left_panel = QGroupBox("Glossary Entries")
        left_layout = QVBoxLayout(left_panel)

        # Entry management buttons
        entry_buttons = QHBoxLayout()
        self.add_entry_btn = QPushButton("Add Entry")
        self.add_entry_btn.clicked.connect(self.add_entry)
        entry_buttons.addWidget(self.add_entry_btn)

        self.edit_entry_btn = QPushButton("Edit Entry")
        self.edit_entry_btn.clicked.connect(self.edit_entry)
        entry_buttons.addWidget(self.edit_entry_btn)

        self.delete_entry_btn = QPushButton("Delete Entry")
        self.delete_entry_btn.clicked.connect(self.delete_entry)
        entry_buttons.addWidget(self.delete_entry_btn)

        left_layout.addLayout(entry_buttons)

        # Entries tree
        self.entries_tree = QTreeWidget()
        self.entries_tree.setHeaderLabels(["Term", "Type", "Category", "Status", "Source"])
        self.entries_tree.itemSelectionChanged.connect(self.on_entry_selected)
        self.entries_tree.itemDoubleClicked.connect(self.edit_entry)
        left_layout.addWidget(self.entries_tree)

        splitter.addWidget(left_panel)

        # Right panel - entry details
        right_panel = QGroupBox("Entry Details")
        right_layout = QVBoxLayout(right_panel)

        self.details_form = QFormLayout()

        self.detail_term = QLabel()
        self.detail_term.setFont(QFont("", 12, QFont.Weight.Bold))
        self.details_form.addRow("Term:", self.detail_term)

        self.detail_type = QLabel()
        self.details_form.addRow("Type:", self.detail_type)

        self.detail_category = QLabel()
        self.details_form.addRow("Category:", self.detail_category)

        self.detail_status = QLabel()
        self.details_form.addRow("Status:", self.detail_status)

        self.detail_source = QLabel()
        self.details_form.addRow("Source:", self.detail_source)

        self.detail_description = QTextEdit()
        self.detail_description.setReadOnly(True)
        self.detail_description.setMaximumHeight(100)
        self.details_form.addRow("Description:", self.detail_description)

        self.detail_related = QTextEdit()
        self.detail_related.setReadOnly(True)
        self.detail_related.setMaximumHeight(80)
        self.details_form.addRow("Related Terms:", self.detail_related)

        self.detail_etymology = QTextEdit()
        self.detail_etymology.setReadOnly(True)
        self.detail_etymology.setMaximumHeight(80)
        self.details_form.addRow("Etymology:", self.detail_etymology)

        right_layout.addLayout(self.details_form)
        right_layout.addStretch()

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        self.update_ui_state()

    def new_glossary(self):
        """Create a new empty glossary"""
        if self.glossary_data:
            reply = QMessageBox.question(
                self, "New Glossary",
                "This will clear the current glossary. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.glossary_data.clear()
        self.current_file = None
        self.refresh_entries_tree()
        self.update_ui_state()
        self.status_label.setText("New empty glossary created")

    def open_csv_file(self):
        """Open a CSV glossary file with structure preview and column mapping"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV Glossary", "", "CSV files (*.csv)"
        )
        if file_path:
            try:
                path = Path(file_path)

                # Show CSV preview first
                if not self._show_csv_preview(path):
                    return

                # Load with flexible column mapping
                self.load_csv(path)
                self.current_file = path
                self.refresh_entries_tree()
                self.update_ui_state()
                self.status_label.setText(f"Loaded {len(self.glossary_data)} terms from {path.name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV file: {str(e)}")




    def save_csv_file(self):
        """Save current glossary to CSV file"""
        if self.current_file and self.current_file.suffix.lower() == '.csv':
            # Save to current CSV file
            try:
                self.save_csv(self.current_file)
                self.status_label.setText(f"Saved {len(self.glossary_data)} terms to {self.current_file.name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save CSV: {str(e)}")
        else:
            # Save As CSV
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save CSV Glossary", "", "CSV files (*.csv)"
            )
            if file_path:
                try:
                    path = Path(file_path)
                    self.save_csv(path)
                    self.current_file = path
                    self.update_ui_state()
                    self.status_label.setText(f"Saved {len(self.glossary_data)} terms to {path.name}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save CSV: {str(e)}")



    def load_csv(self, file_path: Path, column_mapping: Dict[str, str] = None):
        """Load glossary from CSV file with flexible column mapping"""
        # Detect CSV structure
        structure = CsvStructureDetector.detect_structure(file_path)

        if 'error' in structure:
            QMessageBox.critical(self, "CSV Error", f"Error reading CSV: {structure['error']}")
            return

        # If no mapping provided, show mapping dialog
        if column_mapping is None:
            if not structure['columns']:
                QMessageBox.warning(self, "Empty CSV", "The CSV file appears to be empty or invalid.")
                return

            dialog = ColumnMappingDialog(structure['columns'], self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            column_mapping, _ = dialog.get_mapping()

        # Ensure we have at least a term mapping
        if 'term' not in column_mapping:
            QMessageBox.warning(self, "Missing Term Field",
                              "You must map at least the 'term' field to load entries.")
            return

        self.glossary_data.clear()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=structure['delimiter'])
                loaded_count = 0

                for row in reader:
                    # Use mapped column names
                    term_col = column_mapping.get('term', 'term')
                    term = row.get(term_col, '').strip()

                    if term:
                        # Handle related terms with flexible mapping
                        related_terms = []
                        related_col = column_mapping.get('related_terms')
                        if related_col and related_col in row and row[related_col]:
                            related_terms = [t.strip() for t in row[related_col].split(';') if t.strip()]

                        entry = GlossaryEntry(
                            term=term,
                            entry_type=row.get(column_mapping.get('type', 'type'), '').strip(),
                            category=row.get(column_mapping.get('category', 'category'), '').strip(),
                            description=row.get(column_mapping.get('description', 'description'), '').strip(),
                            source=row.get(column_mapping.get('source', 'source'), '').strip(),
                            related_terms=related_terms,
                            etymology_notes=row.get(column_mapping.get('etymology_notes', 'etymology_notes'), '').strip()
                        )
                        self.glossary_data[term] = entry
                        loaded_count += 1

                QMessageBox.information(self, "CSV Loaded",
                                      f"Successfully loaded {loaded_count} entries from CSV.")

        except Exception as e:
            QMessageBox.critical(self, "Loading Error", f"Failed to load CSV: {str(e)}")

    def save_csv(self, file_path: Path):
        """Save glossary to CSV file"""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['term', 'type', 'category', 'description', 'source', 'related_terms', 'etymology_notes']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for entry in sorted(self.glossary_data.values(), key=lambda x: x.term.lower()):
                row = entry.to_dict()
                row['related_terms'] = '; '.join(row['related_terms'])
                writer.writerow(row)



    def add_entry(self):
        """Add a new glossary entry"""
        existing_terms = list(self.glossary_data.keys())
        dialog = GlossaryEntryDialog(existing_terms=existing_terms, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            entry = dialog.get_entry()
            if entry.term:
                if entry.term in self.glossary_data:
                    reply = QMessageBox.question(
                        self, "Entry Exists",
                        f"Entry '{entry.term}' already exists. Replace it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return

                self.glossary_data[entry.term] = entry
                self.refresh_entries_tree()
                self.update_ui_state()
                self.data_changed.emit()
                self.status_label.setText(f"Added entry: {entry.term}")

    def edit_entry(self):
        """Edit the selected glossary entry"""
        current_item = self.entries_tree.currentItem()
        if current_item is None:
            return

        term = current_item.text(0)
        entry = self.glossary_data.get(term)
        if entry is None:
            return

        existing_terms = [t for t in self.glossary_data.keys() if t != term]
        dialog = GlossaryEntryDialog(entry=entry, existing_terms=existing_terms, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_entry = dialog.get_entry()
            if new_entry.term != term:
                # Term changed, remove old and add new
                del self.glossary_data[term]
                if new_entry.term in self.glossary_data:
                    reply = QMessageBox.question(
                        self, "Entry Exists",
                        f"Entry '{new_entry.term}' already exists. Replace it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        # Restore old entry
                        self.glossary_data[term] = entry
                        return

            self.glossary_data[new_entry.term] = new_entry
            self.refresh_entries_tree()
            self.update_ui_state()
            self.data_changed.emit()
            self.status_label.setText(f"Updated entry: {new_entry.term}")

    def delete_entry(self):
        """Delete the selected glossary entry"""
        current_item = self.entries_tree.currentItem()
        if current_item is None:
            return

        term = current_item.text(0)

        reply = QMessageBox.question(
            self, "Delete Entry",
            f"Are you sure you want to delete '{term}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.glossary_data[term]
            self.refresh_entries_tree()
            self.update_ui_state()
            self.data_changed.emit()

    def set_item_database(self):
        """Set the path to the item database for status inference"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Item Database", "", "JSON files (*.json)"
        )
        if file_path:
            self.item_database_path = Path(file_path)
            self.status_label.setText(f"Item database: {self.item_database_path.name}")
            self.refresh_entries_tree()  # Refresh to update inferred statuses

    def infer_status(self, term: str) -> str:
        """Infer status by checking against item database"""
        if not self.item_database_path or not self.item_database_path.exists():
            return "unknown"

        try:
            with open(self.item_database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if term exists in items array with full specs
            if 'items' in data and isinstance(data['items'], list):
                for item in data['items']:
                    if isinstance(item, dict):
                        # Check by ID or name
                        if (item.get('id', '').lower() == term.lower() or
                            item.get('name', '').lower() == term.lower()):
                            # Check if it has substantial implementation details
                            if self._has_full_implementation(item):
                                return "implemented"
                            else:
                                return "partial"

            # Check if mentioned in glossary but not fully implemented
            entry = self.glossary_data.get(term)
            if entry and entry.description and len(entry.description) > 50:
                return "conceptual"

            return "pending"

        except Exception as e:
            print(f"Error inferring status for {term}: {e}")
            return "unknown"

    def _has_full_implementation(self, item: dict) -> bool:
        """Check if item has full implementation details"""
        required_fields = ['id', 'name', 'description', 'tech_tier', 'category']
        detailed_fields = ['lore_notes', 'properties', 'blueprint', 'crafting_recipe_id']

        # Must have all required fields
        if not all(item.get(field) for field in required_fields):
            return False

        # Must have at least some detailed fields
        detail_count = sum(1 for field in detailed_fields if item.get(field))
        return detail_count >= 2

    def compare_csv_files(self):
        """Compare CSV files with flexible column mapping"""
        # Get first CSV file
        file1, _ = QFileDialog.getOpenFileName(
            self, "Select First CSV File", "", "CSV files (*.csv)"
        )
        if not file1:
            return

        # Get second CSV file
        file2, _ = QFileDialog.getOpenFileName(
            self, "Select Second CSV File", "", "CSV files (*.csv)"
        )
        if not file2:
            return

        try:
            # Detect structure for both files
            structure1 = CsvStructureDetector.detect_structure(Path(file1))
            structure2 = CsvStructureDetector.detect_structure(Path(file2))

            if 'error' in structure1 or 'error' in structure2:
                QMessageBox.critical(self, "CSV Error", "Error reading one or both CSV files.")
                return

            # Get column mapping for first file
            dialog1 = ColumnMappingDialog(structure1['columns'], self)
            dialog1.setWindowTitle("Map Columns for First CSV File")
            if dialog1.exec() != QDialog.DialogCode.Accepted:
                return
            mapping1, key1 = dialog1.get_mapping()

            # Get column mapping for second file
            dialog2 = ColumnMappingDialog(structure2['columns'], self)
            dialog2.setWindowTitle("Map Columns for Second CSV File")
            if dialog2.exec() != QDialog.DialogCode.Accepted:
                return
            mapping2, key2 = dialog2.get_mapping()

            # Load terms from both files
            terms1 = self._load_csv_terms_for_comparison(Path(file1), structure1, mapping1, key1)
            terms2 = self._load_csv_terms_for_comparison(Path(file2), structure2, mapping2, key2)

            # Compare and show results
            self._show_csv_comparison_results(Path(file1), Path(file2), terms1, terms2, key1, key2)

        except Exception as e:
            QMessageBox.critical(self, "Comparison Error", f"Failed to compare CSV files: {str(e)}")

    def _load_csv_terms_for_comparison(self, csv_path: Path, structure: Dict,
                                     mapping: Dict[str, str], comparison_key: str) -> Dict[str, Dict[str, str]]:
        """Load terms from CSV file for comparison with flexible mapping"""
        terms = {}

        # Determine which column to use as the key
        key_column = mapping.get(comparison_key, comparison_key)
        if key_column not in structure['columns']:
            # Fallback to first available key
            for fallback in ['term', 'id', 'name', 'title']:
                fallback_col = mapping.get(fallback, fallback)
                if fallback_col in structure['columns']:
                    key_column = fallback_col
                    break

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=structure['delimiter'])
            for row in reader:
                key_value = row.get(key_column, '').strip()
                if key_value:
                    terms[key_value.lower()] = row
        return terms

    def _get_display_value(self, row_data: Dict[str, str], key_field: str, fallback: str) -> str:
        """Get display value for a row using the specified key field"""
        # Try the key field first
        if key_field in row_data and row_data[key_field]:
            return row_data[key_field]

        # Try common fallback fields
        for field in ['term', 'name', 'title', 'id']:
            if field in row_data and row_data[field]:
                return row_data[field]

        # Use the fallback key
        return fallback

    def _show_csv_comparison_results(self, file1: Path, file2: Path,
                                   terms1: Dict[str, Dict[str, str]],
                                   terms2: Dict[str, Dict[str, str]],
                                   key1: str = 'term', key2: str = 'term'):
        """Show CSV comparison results in a dialog with flexible keys"""

        # Calculate differences
        only_in_1 = set(terms1.keys()) - set(terms2.keys())
        only_in_2 = set(terms2.keys()) - set(terms1.keys())
        common_terms = set(terms1.keys()) & set(terms2.keys())

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("CSV Comparison Results")
        dialog.setModal(True)
        dialog.resize(800, 600)

        layout = QVBoxLayout(dialog)

        # Summary
        summary_label = QLabel(f"""
<b>Comparison Summary:</b><br>
File 1: {file1.name} ({len(terms1)} terms)<br>
File 2: {file2.name} ({len(terms2)} terms)<br><br>
Terms only in {file1.name}: {len(only_in_1)}<br>
Terms only in {file2.name}: {len(only_in_2)}<br>
Terms in both files: {len(common_terms)}<br>
Total unique terms: {len(terms1) + len(terms2) - len(common_terms)}
        """)
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        # Results tabs
        tab_widget = QTabWidget()

        # Tab 1: Missing from file 2
        if only_in_1:
            missing_text = QTextEdit()
            missing_content = f"Items in {file1.name} but NOT in {file2.name}:\n\n"
            for term_key in sorted(only_in_1):
                row_data = terms1[term_key]
                # Get the actual display value using flexible key mapping
                display_value = self._get_display_value(row_data, key1, term_key)
                missing_content += f"• {display_value}\n"
                missing_content += f"  Type: {row_data.get('type', 'N/A')}\n"
                missing_content += f"  Category: {row_data.get('category', 'N/A')}\n"
                description = row_data.get('description', 'N/A')
                if description and len(description) > 100:
                    description = description[:100] + "..."
                missing_content += f"  Description: {description}\n\n"

            missing_text.setPlainText(missing_content)
            tab_widget.addTab(missing_text, f"Missing from {file2.name}")

        # Tab 2: Missing from file 1
        if only_in_2:
            missing_text2 = QTextEdit()
            missing_content2 = f"Items in {file2.name} but NOT in {file1.name}:\n\n"
            for term_key in sorted(only_in_2):
                row_data = terms2[term_key]
                # Get the actual display value using flexible key mapping
                display_value = self._get_display_value(row_data, key2, term_key)
                missing_content2 += f"• {display_value}\n"
                missing_content2 += f"  Type: {row_data.get('type', 'N/A')}\n"
                missing_content2 += f"  Category: {row_data.get('category', 'N/A')}\n"
                description = row_data.get('description', 'N/A')
                if description and len(description) > 100:
                    description = description[:100] + "..."
                missing_content2 += f"  Description: {description}\n\n"

            missing_text2.setPlainText(missing_content2)
            missing_text2.setReadOnly(True)
            tab_widget.addTab(missing_text2, f"Missing from {file1.name}")

        # Tab 3: Common terms
        common_text = QTextEdit()
        common_content = f"Terms in BOTH files ({len(common_terms)}):\n\n"
        for term in sorted(list(common_terms)[:20]):  # Show first 20
            row_data = terms1[term]
            original_term = row_data.get('term', term)
            common_content += f"• {original_term}\n"
        if len(common_terms) > 20:
            common_content += f"\n... and {len(common_terms) - 20} more"

        common_text.setPlainText(common_content)
        common_text.setReadOnly(True)
        tab_widget.addTab(common_text, f"Common Terms ({len(common_terms)})")

        layout.addWidget(tab_widget)

        # Buttons
        button_layout = QHBoxLayout()

        if only_in_1:
            export_missing_btn = QPushButton("Export Missing Terms")
            export_missing_btn.clicked.connect(lambda: self._export_missing_terms(only_in_1, terms1, file1, file2))
            button_layout.addWidget(export_missing_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def _export_missing_terms(self, missing_terms: Set[str], terms_data: Dict[str, Dict[str, str]],
                            source_file: Path, target_file: Path):
        """Export missing terms to a CSV file preserving original structure"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Missing Terms", f"missing_from_{target_file.stem}.csv", "CSV files (*.csv)"
        )

        if not file_path:
            return

        try:
            # Detect original CSV structure to preserve field names
            structure = CsvStructureDetector.detect_structure(source_file)
            fieldnames = structure['columns'] if structure['columns'] else ['term', 'type', 'category', 'description', 'source']

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=structure.get('delimiter', ','))
                writer.writeheader()

                for term_key in sorted(missing_terms):
                    row_data = terms_data[term_key]
                    # Write row preserving original field names and structure
                    clean_row = {}
                    for field in fieldnames:
                        clean_row[field] = row_data.get(field, '')
                    writer.writerow(clean_row)

            QMessageBox.information(self, "Export Complete",
                                  f"Exported {len(missing_terms)} missing terms to {Path(file_path).name}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export missing terms: {str(e)}")

    def _show_csv_preview(self, file_path: Path) -> bool:
        """Show CSV structure preview dialog and return True if user wants to proceed"""
        # Detect structure
        structure = CsvStructureDetector.detect_structure(file_path)

        if 'error' in structure:
            QMessageBox.critical(self, "CSV Error", f"Error reading CSV: {structure['error']}")
            return False

        # Get preview data
        preview_data = CsvStructureDetector.preview_data(file_path, max_rows=5)

        # Create preview dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"CSV Preview: {file_path.name}")
        dialog.setModal(True)
        dialog.resize(800, 600)

        layout = QVBoxLayout(dialog)

        # Structure info
        info_text = f"""
<b>CSV Structure Analysis:</b><br>
File: {file_path.name}<br>
Columns: {len(structure['columns'])}<br>
Rows: {structure['row_count']}<br>
Delimiter: '{structure['delimiter']}'<br>
Potential key fields: {', '.join(structure['potential_keys']) if structure['potential_keys'] else 'None detected'}
        """
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Column list
        columns_group = QGroupBox("Detected Columns")
        columns_layout = QVBoxLayout(columns_group)
        columns_text = QTextEdit()
        columns_text.setMaximumHeight(100)
        columns_content = "Columns found:\n" + "\n".join(f"• {col}" for col in structure['columns'])
        columns_text.setPlainText(columns_content)
        columns_text.setReadOnly(True)
        columns_layout.addWidget(columns_text)
        layout.addWidget(columns_group)

        # Preview table
        if preview_data:
            preview_group = QGroupBox("Data Preview (first 5 rows)")
            preview_layout = QVBoxLayout(preview_group)

            table = QTableWidget()
            table.setColumnCount(len(structure['columns']))
            table.setHorizontalHeaderLabels(structure['columns'])
            table.setRowCount(len(preview_data))

            for row_idx, row_data in enumerate(preview_data):
                for col_idx, col_name in enumerate(structure['columns']):
                    value = row_data.get(col_name, '')
                    # Truncate long values for display
                    if len(value) > 50:
                        value = value[:47] + "..."
                    table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

            # Resize columns to content
            table.resizeColumnsToContents()
            table.setMaximumHeight(200)
            preview_layout.addWidget(table)
            layout.addWidget(preview_group)

        # Buttons
        button_layout = QHBoxLayout()

        proceed_btn = QPushButton("Proceed with Column Mapping")
        proceed_btn.setDefault(True)
        proceed_btn.clicked.connect(dialog.accept)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(proceed_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        return dialog.exec() == QDialog.DialogCode.Accepted

    def refresh_entries_tree(self):
        """Refresh the entries tree widget"""
        self.entries_tree.clear()

        # Update filter options
        types = set(entry.type for entry in self.glossary_data.values() if entry.type)
        current_type = self.type_filter.currentText()
        self.type_filter.clear()
        self.type_filter.addItem("All Types")
        self.type_filter.addItems(sorted(types))
        if current_type in types or current_type == "All Types":
            self.type_filter.setCurrentText(current_type)

        # Update status filter options with inferred statuses
        statuses = set()
        for term in self.glossary_data.keys():
            statuses.add(self.infer_status(term))

        current_status = self.status_filter.currentText()
        self.status_filter.clear()
        self.status_filter.addItem("All Status")
        self.status_filter.addItems(sorted(statuses))
        if current_status in statuses or current_status == "All Status":
            self.status_filter.setCurrentText(current_status)

        self.filter_entries()

    def filter_entries(self):
        """Filter entries based on search and filter criteria"""
        self.entries_tree.clear()

        search_text = self.search_edit.text().lower()
        type_filter = self.type_filter.currentText()
        status_filter = self.status_filter.currentText()

        for entry in sorted(self.glossary_data.values(), key=lambda x: x.term.lower()):
            inferred_status = self.infer_status(entry.term)

            # Apply filters
            if type_filter != "All Types" and entry.type != type_filter:
                continue
            if status_filter != "All Status" and inferred_status != status_filter:
                continue
            if search_text and search_text not in entry.term.lower() and search_text not in entry.description.lower():
                continue

            item = QTreeWidgetItem([
                entry.term,
                entry.type,
                entry.category,
                inferred_status,
                entry.source
            ])
            self.entries_tree.addTopLevelItem(item)

    def on_entry_selected(self):
        """Handle entry selection"""
        current_item = self.entries_tree.currentItem()
        if current_item is None:
            self.clear_details()
            return

        term = current_item.text(0)
        entry = self.glossary_data.get(term)
        if entry:
            self.show_entry_details(entry)

    def show_entry_details(self, entry: GlossaryEntry):
        """Show entry details in the right panel"""
        self.detail_term.setText(entry.term)
        self.detail_type.setText(entry.type)
        self.detail_category.setText(entry.category)
        self.detail_status.setText(self.infer_status(entry.term))
        self.detail_source.setText(entry.source)
        self.detail_description.setPlainText(entry.description)
        self.detail_related.setPlainText('; '.join(entry.related_terms))
        self.detail_etymology.setPlainText(entry.etymology_notes)

    def clear_details(self):
        """Clear the details panel"""
        self.detail_term.setText("")
        self.detail_type.setText("")
        self.detail_category.setText("")
        self.detail_status.setText("")
        self.detail_source.setText("")
        self.detail_description.setPlainText("")
        self.detail_related.setPlainText("")
        self.detail_etymology.setPlainText("")

    def update_ui_state(self):
        """Update UI state based on current data"""
        has_data = bool(self.glossary_data)
        self.save_csv_btn.setEnabled(has_data)

        has_selection = self.entries_tree.currentItem() is not None
        self.edit_entry_btn.setEnabled(has_selection)
        self.delete_entry_btn.setEnabled(has_selection)

    def confirm_unsaved_changes(self) -> bool:
        """Check for unsaved changes and confirm with user"""
        # For now, always return True. In a real implementation,
        # you'd track modification state and prompt the user.
        return True

    def get_glossary_data(self) -> Dict[str, GlossaryEntry]:
        """Get the current glossary data"""
        return self.glossary_data.copy()

    def set_glossary_data(self, data: Dict[str, GlossaryEntry]):
        """Set the glossary data"""
        self.glossary_data = data.copy()
        self.refresh_entries_tree()
        self.update_ui_state()


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = GlossaryManagerWidget()
    widget.show()
    sys.exit(app.exec())
