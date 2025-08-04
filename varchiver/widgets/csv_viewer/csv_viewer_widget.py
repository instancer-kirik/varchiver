#!/usr/bin/env python3
"""
CSV Viewer/Editor Widget - Schema-agnostic CSV file viewer and editor

A clean, focused widget for viewing and editing CSV files without making
assumptions about the data structure or content.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QFileDialog, QMessageBox, QLabel, QHeaderView,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QTextEdit,
    QSplitter, QGroupBox, QToolBar, QStatusBar, QAbstractItemView,
    QMenu, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QAction, QFont, QKeySequence, QShortcut

from .csv_data_model import CsvDataModel, CsvRow, ColumnInfo
from .csv_filter_widget import CsvFilterWidget
from .csv_comparison import CsvComparison, CsvComparisonResult
from .status_inference_module import StatusInferenceModule, StatusType
from .csv_preview_dialog import CsvPreviewDialog


class RowEditDialog(QDialog):
    """Dialog for editing a single CSV row"""

    def __init__(self, columns: List[ColumnInfo], row_data: Dict[str, str] = None, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.row_data = row_data or {}
        self.field_widgets = {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Edit Row")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # Form for all fields
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)

        for col in self.columns:
            current_value = self.row_data.get(col.name, "")

            # Use QTextEdit for longer text, QLineEdit for shorter
            if col.max_length > 100 or '\n' in current_value:
                widget = QTextEdit()
                widget.setPlainText(current_value)
                widget.setMaximumHeight(80)
            else:
                widget = QLineEdit()
                widget.setText(current_value)

            self.field_widgets[col.name] = widget
            form_layout.addRow(f"{col.name}:", widget)

        layout.addWidget(form_widget)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_row_data(self) -> Dict[str, str]:
        """Get the edited row data"""
        data = {}
        for col_name, widget in self.field_widgets.items():
            if isinstance(widget, QTextEdit):
                data[col_name] = widget.toPlainText()
            else:
                data[col_name] = widget.text()
        return data


class CsvTableWidget(QWidget):
    """Enhanced table widget for CSV data display with frozen first column"""

    row_double_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.frozen_table = None
        self.main_table = None
        self.sticky_columns = 1  # Number of sticky columns (0, 1, or 2)
        self.auto_detect_sticky = True  # Auto-detect narrow/ID columns
        self._syncing_selection = False  # Flag to prevent selection sync loops
        self.setup_table()

    def setup_table(self):
        """Configure table appearance and behavior with configurable frozen columns"""
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create frozen table for sticky columns
        self.frozen_table = QTableWidget()
        self.frozen_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.frozen_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Create main table for remaining columns
        self.main_table = QTableWidget()

        # Configure both tables
        for table in [self.frozen_table, self.main_table]:
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            table.setAlternatingRowColors(True)
            table.setWordWrap(False)
            table.setSortingEnabled(False)  # Disable sorting to avoid sync issues
            table.itemDoubleClicked.connect(self._on_item_double_clicked)
            table.itemClicked.connect(self._on_item_clicked)

        # Configure headers
        self.frozen_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.frozen_table.verticalHeader().setVisible(True)

        self.main_table.horizontalHeader().setStretchLastSection(True)
        self.main_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.main_table.verticalHeader().setVisible(False)  # Hide to avoid duplication

        # Synchronize scrolling
        self.frozen_table.verticalScrollBar().valueChanged.connect(
            self.main_table.verticalScrollBar().setValue
        )
        self.main_table.verticalScrollBar().valueChanged.connect(
            self.frozen_table.verticalScrollBar().setValue
        )

        # Synchronize selection
        self.frozen_table.selectionModel().selectionChanged.connect(self._sync_selection_to_main)
        self.main_table.selectionModel().selectionChanged.connect(self._sync_selection_to_frozen)

        # Add to layout
        layout.addWidget(self.frozen_table)
        layout.addWidget(self.main_table)

    def _on_item_double_clicked(self, item):
        """Handle double-click on table item"""
        if item:
            self.row_double_clicked.emit(item.row())

    def _on_item_clicked(self, item):
        """Handle single-click on table item - ensure selection sync"""
        if item and not getattr(self, '_syncing_selection', False):
            # Ensure both tables have the same row selected
            row = item.row()
            sender = self.sender()

            self._syncing_selection = True
            try:
                if sender == self.frozen_table and self.main_table:
                    self.main_table.selectRow(row)
                elif sender == self.main_table and self.frozen_table:
                    self.frozen_table.selectRow(row)
            finally:
                self._syncing_selection = False

    def _sync_selection_to_main(self, selected, deselected):
        """Sync selection from frozen table to main table"""
        if not self.main_table.selectionModel() or not hasattr(self, '_syncing_selection'):
            return

        if getattr(self, '_syncing_selection', False):
            return

        self._syncing_selection = True
        try:
            # Get selected rows from frozen table
            selected_rows = self._get_selected_rows_from_table(self.frozen_table)

            # Apply same selection to main table
            self.main_table.clearSelection()
            for row in selected_rows:
                if row < self.main_table.rowCount():
                    self.main_table.selectRow(row)
        finally:
            self._syncing_selection = False

    def _sync_selection_to_frozen(self, selected, deselected):
        """Sync selection from main table to frozen table"""
        if not self.frozen_table.selectionModel() or not hasattr(self, '_syncing_selection'):
            return

        if getattr(self, '_syncing_selection', False):
            return

        self._syncing_selection = True
        try:
            # Get selected rows from main table
            selected_rows = self._get_selected_rows_from_table(self.main_table)

            # Apply same selection to frozen table
            self.frozen_table.clearSelection()
            for row in selected_rows:
                if row < self.frozen_table.rowCount():
                    self.frozen_table.selectRow(row)
        finally:
            self._syncing_selection = False

    def _get_selected_rows_from_table(self, table):
        """Get selected row indices from a table"""
        selected_rows = set()
        for item in table.selectedItems():
            selected_rows.add(item.row())
        return sorted(selected_rows)

    def load_data(self, model: CsvDataModel):
        """Load data from CSV model into tables with configurable frozen columns"""
        if not model.columns or not model.rows:
            self.clear()
            return

        # Auto-detect optimal sticky columns if enabled
        if self.auto_detect_sticky:
            self.sticky_columns = self._detect_optimal_sticky_columns(model)

        # If sticky columns disabled, use single table
        if self.sticky_columns == 0:
            self._load_data_single_table(model)
            return

        # Set up table dimensions
        row_count = len(model.rows)
        sticky_cols = min(self.sticky_columns, len(model.columns))

        # Frozen table: sticky columns
        self.frozen_table.setRowCount(row_count)
        self.frozen_table.setColumnCount(sticky_cols)

        # Main table: remaining columns
        main_col_count = max(0, len(model.columns) - sticky_cols)
        self.main_table.setRowCount(row_count)
        self.main_table.setColumnCount(main_col_count)

        # Set headers
        if len(model.columns) > 0:
            # Sticky columns headers for frozen table
            sticky_headers = [col.name for col in model.columns[:sticky_cols]]
            self.frozen_table.setHorizontalHeaderLabels(sticky_headers)

            # Remaining column headers for main table
            if len(model.columns) > sticky_cols:
                main_headers = [col.name for col in model.columns[sticky_cols:]]
                self.main_table.setHorizontalHeaderLabels(main_headers)

        # Populate data
        for row_idx, csv_row in enumerate(model.rows):
            # Sticky columns in frozen table
            for col_idx in range(sticky_cols):
                col = model.columns[col_idx]
                value = csv_row.get_value(col.name, "")
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.frozen_table.setItem(row_idx, col_idx, item)

            # Remaining columns in main table
            for col_idx, col in enumerate(model.columns[sticky_cols:]):
                value = csv_row.get_value(col.name, "")
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.main_table.setItem(row_idx, col_idx, item)

        # Adjust column widths
        self.frozen_table.resizeColumnsToContents()
        self.main_table.resizeColumnsToContents()

        # Calculate frozen table width more accurately
        frozen_width = 0
        for i in range(sticky_cols):
            self.frozen_table.resizeColumnToContents(i)
            col_width = self.frozen_table.columnWidth(i)
            # Ensure minimum useful width for each column
            col_width = max(col_width, 80)  # Minimum 80px per column
            self.frozen_table.setColumnWidth(i, col_width)
            frozen_width += col_width

        # Add padding for borders and scrollbar space, but keep it tight
        total_width = frozen_width + 10  # Minimal padding
        self.frozen_table.setFixedWidth(total_width)

        # Show/hide frozen table based on sticky columns
        self.frozen_table.setVisible(sticky_cols > 0)

    def _detect_optimal_sticky_columns(self, model: CsvDataModel) -> int:
        """Auto-detect optimal number of sticky columns based on data"""
        if len(model.columns) < 2:
            return min(1, len(model.columns))

        # Don't use sticky for very narrow tables
        if len(model.columns) <= 3:
            return 0  # Too few columns to benefit from sticky

        first_col = model.columns[0]

        # Check if first column is already a good main identifier
        is_first_descriptive = (
            'term' in first_col.name.lower() or
            'title' in first_col.name.lower() or
            'name' in first_col.name.lower() or
            'label' in first_col.name.lower() or
            first_col.name.lower() in ['term', 'title', 'name', 'label', 'item']
        )

        # Check if first column looks like an ID (narrow, numeric/short)
        is_first_id_like = (
            'id' in first_col.name.lower() or
            first_col.name.lower() in ['id', 'key', 'pk', 'index', '#', 'num'] or
            self._column_appears_narrow(model, 0)
        )

        # Check if second column looks useful for context (but avoid type columns)
        second_col_useful = False
        if len(model.columns) >= 2:
            second_col = model.columns[1]
            # Exclude type columns as they're not useful for context
            is_type_column = (
                'type' in second_col.name.lower() or
                second_col.name.lower() in ['type', 'category', 'class', 'kind']
            )

            if not is_type_column:
                second_col_useful = (
                    'name' in second_col.name.lower() or
                    'title' in second_col.name.lower() or
                    'description' in second_col.name.lower() or
                    'label' in second_col.name.lower() or
                    not self._column_appears_narrow(model, 1)
                )

        # Check if first two columns are both narrow/similar - skip sticky if so
        if (len(model.columns) >= 2 and
            self._column_appears_narrow(model, 0) and
            self._column_appears_narrow(model, 1)):
            # Both first columns are narrow - probably not useful for context
            if len(model.columns) >= 3 and not self._column_appears_narrow(model, 2):
                return 1  # Skip to third column as single sticky
            else:
                return 0  # All columns seem narrow, disable sticky

        # Main decision logic:
        # If first column is already descriptive (term, title, name), prefer single sticky
        if is_first_descriptive and len(model.columns) >= 4:
            return 1  # First column is perfect identifier, no need for second
        # If first is ID-like and second is useful, consider double sticky
        elif is_first_id_like and second_col_useful and len(model.columns) >= 5:
            return 2  # ID + descriptive column, but only if we have enough columns
        # If first is neither descriptive nor ID-like, use single sticky if reasonable
        elif not is_first_id_like and not is_first_descriptive and len(model.columns) >= 4:
            return 1  # Generic first column
        # If first is ID-like but second isn't useful, just use first
        elif is_first_id_like and len(model.columns) >= 4:
            return 1  # ID column only
        else:
            return 0  # Default to no sticky for smaller tables

    def _column_appears_narrow(self, model: CsvDataModel, col_idx: int) -> bool:
        """Check if a column appears to contain narrow data (like IDs)"""
        if col_idx >= len(model.columns):
            return False

        col = model.columns[col_idx]
        sample_size = min(15, len(model.rows))

        # Check average length of values in this column
        total_length = 0
        numeric_count = 0
        unique_values = set()

        for i, row in enumerate(model.rows[:sample_size]):
            value = str(row.get_value(col.name, "")).strip()
            total_length += len(value)
            unique_values.add(value)

            # Check if numeric or ID-like pattern
            try:
                float(value)
                numeric_count += 1
            except (ValueError, TypeError):
                # Check for ID-like patterns (e.g., "ID001", "USER_123")
                if len(value) <= 10 and any(char.isdigit() for char in value):
                    numeric_count += 0.5  # Partial credit for ID-like strings

        if sample_size == 0:
            return False

        avg_length = total_length / sample_size
        numeric_ratio = numeric_count / sample_size
        uniqueness = len(unique_values) / sample_size if sample_size > 0 else 0

        # Consider narrow if:
        # - Average length < 8 chars (reasonable threshold)
        # - Mostly numeric/ID-like (> 60%)
        # - High uniqueness suggests ID column (> 85% unique and short)
        # - Very short average length (< 4 chars)
        return (avg_length < 4 or
                (avg_length < 8 and numeric_ratio > 0.6) or
                (uniqueness > 0.85 and avg_length < 12))

    def _load_data_single_table(self, model: CsvDataModel):
        """Load data into main table only (no sticky columns)"""
        self.frozen_table.setVisible(False)

        row_count = len(model.rows)
        self.main_table.setRowCount(row_count)
        self.main_table.setColumnCount(len(model.columns))

        # Set headers
        headers = [col.name for col in model.columns]
        self.main_table.setHorizontalHeaderLabels(headers)

        # Populate data
        for row_idx, csv_row in enumerate(model.rows):
            for col_idx, col in enumerate(model.columns):
                value = csv_row.get_value(col.name, "")
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.main_table.setItem(row_idx, col_idx, item)

        # Adjust column widths
        self.main_table.resizeColumnsToContents()

    def set_sticky_columns(self, count: int):
        """Set the number of sticky columns (0, 1, or 2)"""
        self.sticky_columns = max(0, min(2, count))

    def toggle_sticky_columns(self):
        """Cycle through sticky column options: 0 -> 1 -> 2 -> 0"""
        self.sticky_columns = (self.sticky_columns + 1) % 3

    def set_auto_detect_sticky(self, enabled: bool):
        """Enable/disable auto-detection of optimal sticky columns"""
        self.auto_detect_sticky = enabled

    def get_selected_rows(self) -> List[int]:
        """Get indices of selected rows"""
        # Use main table selection (both tables should be synced)
        if self.sticky_columns > 0:
            return self._get_selected_rows_from_table(self.main_table)
        else:
            return self._get_selected_rows_from_table(self.main_table)

    def clear(self):
        """Clear both tables"""
        if self.frozen_table:
            self.frozen_table.clear()
        if self.main_table:
            self.main_table.clear()

    def selectedItems(self):
        """Get selected items from both tables"""
        items = []
        if self.frozen_table:
            items.extend(self.frozen_table.selectedItems())
        if self.main_table:
            items.extend(self.main_table.selectedItems())
        return items

    def clearSelection(self):
        """Clear selection in both tables"""
        if self.frozen_table:
            self.frozen_table.clearSelection()
        if self.main_table:
            self.main_table.clearSelection()

    def selectRow(self, row):
        """Select a row in both tables"""
        if self.frozen_table:
            self.frozen_table.selectRow(row)
        if self.main_table:
            self.main_table.selectRow(row)

    def setCurrentCell(self, row, column):
        """Set current cell (delegate to appropriate table)"""
        if self.sticky_columns == 0:
            if self.main_table:
                self.main_table.setCurrentCell(row, column)
        elif column < self.sticky_columns and self.frozen_table:
            self.frozen_table.setCurrentCell(row, column)
        elif column >= self.sticky_columns and self.main_table:
            self.main_table.setCurrentCell(row, column - self.sticky_columns)

    def currentRow(self):
        """Get current row from main table"""
        if self.main_table:
            return self.main_table.currentRow()
        elif self.frozen_table:
            return self.frozen_table.currentRow()
        return -1

    def rowCount(self):
        """Get row count"""
        if self.main_table:
            return self.main_table.rowCount()
        elif self.frozen_table:
            return self.frozen_table.rowCount()
        return 0

    def columnCount(self):
        """Get total column count (frozen + main)"""
        if self.sticky_columns == 0:
            return self.main_table.columnCount() if self.main_table else 0
        else:
            frozen_cols = self.frozen_table.columnCount() if self.frozen_table else 0
            main_cols = self.main_table.columnCount() if self.main_table else 0
            return frozen_cols + main_cols


class CsvViewerWidget(QWidget):
    """Main CSV Viewer/Editor widget"""

    file_changed = pyqtSignal(str)  # Emitted when file is loaded
    data_changed = pyqtSignal()     # Emitted when data is modified

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = CsvDataModel()
        self.filtered_rows = []  # Cache for filtered data

        # Feature modules
        self.status_inference = StatusInferenceModule()

        self.init_ui()
        self.update_ui_state()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        # Toolbar
        self.create_toolbar(layout)

        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - filters
        self.filter_widget = CsvFilterWidget()
        self.filter_widget.filters_changed.connect(self.apply_filters)
        self.filter_widget.setMaximumWidth(300)
        splitter.addWidget(self.filter_widget)

        # Right panel - table
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.table = CsvTableWidget()
        self.table.row_double_clicked.connect(self.edit_selected_row)
        table_layout.addWidget(self.table)

        splitter.addWidget(table_widget)

        # Set splitter proportions (1:3 ratio)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_label = QLabel("No file loaded")
        self.status_bar.addWidget(self.status_label)
        layout.addWidget(self.status_bar)

        # Keyboard shortcuts
        self.setup_shortcuts()

    def create_toolbar(self, layout):
        """Create toolbar with file and row operations"""
        toolbar_layout = QHBoxLayout()

        # File operations
        self.open_btn = QPushButton("Open CSV")
        self.open_btn.clicked.connect(self.open_file)
        self.open_btn.setToolTip("Open CSV file (Ctrl+O)")
        toolbar_layout.addWidget(self.open_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_file)
        self.save_btn.setToolTip("Save current file (Ctrl+S)")
        self.save_btn.setEnabled(False)
        toolbar_layout.addWidget(self.save_btn)

        self.save_as_btn = QPushButton("Save As")
        self.save_as_btn.clicked.connect(self.save_as_file)
        self.save_as_btn.setToolTip("Save as new file (Ctrl+Shift+S)")
        self.save_as_btn.setEnabled(False)
        toolbar_layout.addWidget(self.save_as_btn)

        toolbar_layout.addWidget(QLabel("|"))  # Separator

        # Sticky column controls
        sticky_label = QLabel("Sticky:")
        toolbar_layout.addWidget(sticky_label)

        self.sticky_toggle_btn = QPushButton("Auto")
        self.sticky_toggle_btn.setMaximumWidth(60)
        self.sticky_toggle_btn.setToolTip("Toggle sticky columns: Auto -> 0 -> 1 -> 2")
        self.sticky_toggle_btn.clicked.connect(self._toggle_sticky_columns)
        toolbar_layout.addWidget(self.sticky_toggle_btn)

        toolbar_layout.addWidget(QLabel("|"))  # Separator

        # Global search
        search_label = QLabel("Search:")
        toolbar_layout.addWidget(search_label)

        self.toolbar_search = QLineEdit()
        self.toolbar_search.setPlaceholderText("Search all columns...")
        self.toolbar_search.setMaximumWidth(200)
        self.toolbar_search.textChanged.connect(self._on_toolbar_search_changed)
        toolbar_layout.addWidget(self.toolbar_search)

        clear_search_btn = QPushButton("✕")
        clear_search_btn.setMaximumWidth(25)
        clear_search_btn.setToolTip("Clear search")
        clear_search_btn.clicked.connect(self._clear_toolbar_search)
        toolbar_layout.addWidget(clear_search_btn)

        toolbar_layout.addWidget(QLabel("|"))  # Separator

        # Row operations
        self.add_row_btn = QPushButton("Add Row")
        self.add_row_btn.clicked.connect(self.add_row)
        self.add_row_btn.setToolTip("Add new row with same structure (Ctrl+N)")
        self.add_row_btn.setEnabled(False)
        toolbar_layout.addWidget(self.add_row_btn)

        self.edit_row_btn = QPushButton("Edit Row")
        self.edit_row_btn.clicked.connect(self.edit_selected_row)
        self.edit_row_btn.setToolTip("Edit selected row (Enter)")
        self.edit_row_btn.setEnabled(False)
        toolbar_layout.addWidget(self.edit_row_btn)

        self.delete_row_btn = QPushButton("Delete Row")
        self.delete_row_btn.clicked.connect(self.delete_selected_rows)
        self.delete_row_btn.setToolTip("Delete selected rows (Delete)")
        self.delete_row_btn.setEnabled(False)
        toolbar_layout.addWidget(self.delete_row_btn)

        toolbar_layout.addWidget(QLabel("|"))  # Separator

        # Analysis operations
        self.compare_btn = QPushButton("Compare Files")
        self.compare_btn.clicked.connect(self.compare_csv_files)
        self.compare_btn.setToolTip("Compare with another CSV file")
        toolbar_layout.addWidget(self.compare_btn)

        self.set_database_btn = QPushButton("Set Database")
        self.set_database_btn.clicked.connect(self.set_status_database)
        self.set_database_btn.setToolTip("Set JSON database for status inference")
        toolbar_layout.addWidget(self.set_database_btn)

        toolbar_layout.addStretch()

        # Info label
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #666; font-style: italic;")
        toolbar_layout.addWidget(self.info_label)

        layout.addLayout(toolbar_layout)

    def _update_sticky_button_display(self):
        """Update sticky button to show current auto-detection result"""
        if self.table.auto_detect_sticky:
            detected = self.table.sticky_columns if hasattr(self.table, 'sticky_columns') else 1
            self.sticky_toggle_btn.setText(f"Auto({detected})")
            self.sticky_toggle_btn.setToolTip(f"Auto-detected {detected} sticky columns. Click to toggle.")
        elif self.table.sticky_columns == 0:
            self.sticky_toggle_btn.setText("0")
            self.sticky_toggle_btn.setToolTip("No sticky columns")
        elif self.table.sticky_columns == 1:
            self.sticky_toggle_btn.setText("1")
            self.sticky_toggle_btn.setToolTip("1 sticky column")
        else:
            self.sticky_toggle_btn.setText("2")
            self.sticky_toggle_btn.setToolTip("2 sticky columns")

    def _toggle_sticky_columns(self):
        """Toggle between sticky column modes"""
        if self.table.auto_detect_sticky:
            # Auto -> 0 sticky
            self.table.set_auto_detect_sticky(False)
            self.table.set_sticky_columns(0)
        elif self.table.sticky_columns == 0:
            # 0 -> 1 sticky
            self.table.set_sticky_columns(1)
        elif self.table.sticky_columns == 1:
            # 1 -> 2 sticky
            self.table.set_sticky_columns(2)
        else:
            # 2 -> Auto
            self.table.set_auto_detect_sticky(True)

        # Reload data with new sticky settings
        if self.model:
            self.table.load_data(self.model)

        # Update button display
        self._update_sticky_button_display()

    def _on_toolbar_search_changed(self, text: str):
        """Handle search text change in toolbar"""
        if self.filter_widget and hasattr(self.filter_widget, 'search_input') and self.filter_widget.search_input:
            self.filter_widget.search_input.setText(text)

    def _clear_toolbar_search(self):
        """Clear the toolbar search"""
        if hasattr(self, 'toolbar_search') and self.toolbar_search:
            self.toolbar_search.clear()

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # File operations
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_file)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_file)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self.save_as_file)

        # Row operations
        QShortcut(QKeySequence("Ctrl+N"), self, self.add_row)
        QShortcut(QKeySequence("Return"), self, self.edit_selected_row)
        QShortcut(QKeySequence("Delete"), self, self.delete_selected_rows)

    def open_file(self):
        """Open CSV file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV File", "", "CSV files (*.csv);;All files (*)"
        )

        if file_path:
            # Show preview dialog first
            accepted, structure_info = CsvPreviewDialog.preview_csv_file(Path(file_path), self)
            if accepted and structure_info and not structure_info.get('error'):
                self.load_csv_file(Path(file_path))

    def load_csv_file(self, file_path: Path):
        """Load CSV file into the viewer"""
        success, message = self.model.load_from_file(file_path)

        if success:
            # Set up filter widget with new model
            self.filter_widget.set_model(self.model)

            # Connect filter widget search to toolbar search (bidirectional)
            if (hasattr(self.filter_widget, 'search_input') and self.filter_widget.search_input and
                hasattr(self, 'toolbar_search') and self.toolbar_search):
                self.filter_widget.search_input.textChanged.connect(
                    lambda text: self.toolbar_search.setText(text) if self.toolbar_search.text() != text else None
                )

            # Load data and apply any existing filters
            self.apply_filters()
            self.update_ui_state()
            self.status_label.setText(message)

            # Update sticky button to show auto-detection result
            self._update_sticky_button_display()

            self.file_changed.emit(str(file_path))
        else:
            QMessageBox.critical(self, "Error Loading File", message)

    def save_file(self):
        """Save current file"""
        if not self.model.file_path:
            self.save_as_file()
            return

        success, message = self.model.save_to_file()
        if success:
            self.status_label.setText(message)
            self.update_ui_state()
        else:
            QMessageBox.critical(self, "Error Saving File", message)

    def save_as_file(self):
        """Save as new file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV File", "", "CSV files (*.csv);;All files (*)"
        )

        if file_path:
            success, message = self.model.save_to_file(Path(file_path))
            if success:
                self.status_label.setText(message)
                self.update_ui_state()
                self.file_changed.emit(str(file_path))
            else:
                QMessageBox.critical(self, "Error Saving File", message)

    def add_row(self):
        """Add new row with same structure"""
        if not self.model.columns:
            QMessageBox.warning(self, "No Data", "Load a CSV file first")
            return

        # Create template row
        template_data = self.model.create_template_row()

        # Show edit dialog
        dialog = RowEditDialog(self.model.columns, template_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            row_data = dialog.get_row_data()
            self.model.add_row(row_data)
            self.refresh_table()
            self.data_changed.emit()

    def edit_selected_row(self):
        """Edit the selected row"""
        selected_rows = self.table.get_selected_rows()
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select a row to edit")
            return

        if len(selected_rows) > 1:
            QMessageBox.information(self, "Multiple Selection", "Please select only one row to edit")
            return

        row_index = selected_rows[0]
        csv_row = self.model.get_row(row_index)
        if not csv_row:
            return

    def compare_csv_files(self):
        """Compare current CSV with another file"""
        if not self.model or not self.model.file_path:
            QMessageBox.warning(self, "No File", "Load a CSV file first")
            return

        # Get second file to compare
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File to Compare", "", "CSV files (*.csv);;All files (*)"
        )

        if not file_path:
            return

        try:
            # For simplicity, use automatic column mapping
            # In a full implementation, you'd show mapping dialogs
            file1_mapping = {col.name: col.name for col in self.model.columns}
            file2_mapping = {col.name: col.name for col in self.model.columns}

            success, message, result = CsvComparison.compare_files(
                self.model.file_path, Path(file_path),
                file1_mapping, file2_mapping
            )

            if success and result:
                self.show_comparison_results(result)
            else:
                QMessageBox.critical(self, "Comparison Error", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to compare files: {str(e)}")

    def show_comparison_results(self, result: CsvComparisonResult):
        """Show comparison results in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("CSV Comparison Results")
        dialog.setModal(True)
        dialog.resize(800, 600)

        layout = QVBoxLayout(dialog)

        # Summary
        summary = result.get_summary()
        summary_text = f"""
<b>Comparison Summary:</b><br>
File 1: {summary['file1_name']} ({summary['total_file1_records']} records)<br>
File 2: {summary['file2_name']} ({summary['total_file2_records']} records)<br><br>
Only in {summary['file1_name']}: {summary['only_in_file1_count']}<br>
Only in {summary['file2_name']}: {summary['only_in_file2_count']}<br>
Common records: {summary['common_records_count']}<br>
Total unique records: {summary['total_unique_keys']}
        """

        summary_label = QLabel(summary_text)
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        # Detailed report
        report_text = QTextEdit()
        report_text.setPlainText(CsvComparison.create_comparison_report(result))
        report_text.setReadOnly(True)
        layout.addWidget(report_text)

        # Buttons
        button_layout = QHBoxLayout()

        if result.only_in_file2:
            export_btn = QPushButton("Export Missing Records")
            export_btn.clicked.connect(lambda: self.export_comparison_results(result))
            button_layout.addWidget(export_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        dialog.exec()

    def export_comparison_results(self, result: CsvComparisonResult):
        """Export comparison results to CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Missing Records",
            f"missing_from_{result.file1_path.stem}.csv",
            "CSV files (*.csv)"
        )

        if file_path:
            success, message = CsvComparison.export_missing_records(
                result, Path(file_path), 'file1_missing'
            )
            if success:
                QMessageBox.information(self, "Export Complete", message)
            else:
                QMessageBox.critical(self, "Export Error", message)

    def set_status_database(self):
        """Set JSON database for status inference"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select JSON Database", "", "JSON files (*.json);;All files (*)"
        )

        if file_path:
            success, message = self.status_inference.set_database(Path(file_path))
            if success:
                self.status_label.setText(f"Database set: {message}")
                # Refresh table to show status if we have data
                if self.model and self.model.rows:
                    self.refresh_table()
            else:
                QMessageBox.critical(self, "Database Error", message)

        # Show edit dialog
        dialog = RowEditDialog(self.model.columns, csv_row.get_all_values(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            row_data = dialog.get_row_data()
            self.model.update_row(row_index, row_data)
            self.refresh_table()
            self.data_changed.emit()

    def delete_selected_rows(self):
        """Delete selected rows"""
        selected_rows = self.table.get_selected_rows()
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select rows to delete")
            return

        # Confirm deletion
        count = len(selected_rows)
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Delete {count} row{'s' if count > 1 else ''}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Delete in reverse order to maintain indices
            for row_index in reversed(selected_rows):
                self.model.delete_row(row_index)

            self.refresh_table()
            self.data_changed.emit()

    def apply_filters(self):
        """Apply current filters and refresh table display"""
        if not self.model or not self.model.rows:
            self.filtered_rows = []
            self.table.clear()
            return

        # Get filtered rows
        self.filtered_rows = self.filter_widget.get_filtered_rows(self.model.rows)

        # Create temporary model with filtered data for display
        display_model = CsvDataModel()
        display_model.columns = self.model.columns
        display_model.rows = self.filtered_rows
        display_model.delimiter = self.model.delimiter
        display_model.encoding = self.model.encoding

        self.table.load_data(display_model)
        self.update_filter_status()

    def update_filter_status(self):
        """Update status bar with filter information"""
        total_rows = len(self.model.rows) if self.model else 0
        filtered_rows = len(self.filtered_rows)

        if self.filter_widget.has_active_filters() and total_rows > 0:
            filter_text = f" (filtered: {filtered_rows}/{total_rows})"
        else:
            filter_text = ""

        self.status_label.setText(f"Loaded {total_rows} rows{filter_text}")

    def refresh_table(self):
        """Refresh table display with current data"""
        self.apply_filters()
        self.update_ui_state()

    def update_ui_state(self):
        """Update UI state based on current data"""
        has_data = self.model.get_row_count() > 0
        has_file = self.model.file_path is not None
        has_selection = len(self.table.get_selected_rows()) > 0

        # File operations
        self.save_btn.setEnabled(has_data and has_file and self.model.has_changes)
        self.save_as_btn.setEnabled(has_data)

        # Row operations
        self.add_row_btn.setEnabled(has_data or len(self.model.columns) > 0)
        self.edit_row_btn.setEnabled(has_selection)
        self.delete_row_btn.setEnabled(has_selection)

        # Analysis operations
        self.compare_btn.setEnabled(has_data)
        self.set_database_btn.setEnabled(True)

        # Info display
        if has_data:
            info = self.model.get_structure_info()
            changes_text = " (modified)" if self.model.has_changes else ""

            # Add status info if database is loaded
            status_info = ""
            if self.status_inference.get_database_info()['loaded']:
                status_info = " | Status: ON"

            self.info_label.setText(
                f"{info['rows']} rows × {info['columns']} columns{changes_text}{status_info}"
            )
        else:
            self.info_label.setText("")

    def get_current_file(self) -> Optional[Path]:
        """Get currently loaded file path"""
        return self.model.file_path

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes"""
        return self.model.has_changes

    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of current data"""
        return self.model.get_structure_info()

    # Connect table selection changes to UI updates
    def showEvent(self, event):
        """Handle widget show event"""
        super().showEvent(event)
        if hasattr(self.table, 'selectionModel'):
            self.table.selectionModel().selectionChanged.connect(self.update_ui_state)
