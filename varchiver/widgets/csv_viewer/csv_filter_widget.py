#!/usr/bin/env python3
"""
CSV Filter Widget - Search and filtering functionality for CSV data

Provides text search, column-specific filtering, and filter management
for CSV data without making assumptions about the data structure.
"""

from typing import Dict, List, Optional, Set, Callable, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QPushButton, QLabel, QGroupBox, QFormLayout, QCheckBox,
    QScrollArea, QFrame, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from .csv_data_model import CsvDataModel, CsvRow, ColumnInfo


class ColumnFilter:
    """Represents a filter for a specific column"""

    def __init__(self, column_name: str, filter_type: str = "contains"):
        self.column_name = column_name
        self.filter_type = filter_type  # "contains", "equals", "starts_with", "ends_with"
        self.value = ""
        self.case_sensitive = False
        self.enabled = True

    def matches(self, row: CsvRow) -> bool:
        """Check if a row matches this filter"""
        if not self.enabled or not self.value:
            return True

        cell_value = row.get_value(self.column_name, "")
        filter_value = self.value

        if not self.case_sensitive:
            cell_value = cell_value.lower()
            filter_value = filter_value.lower()

        if self.filter_type == "contains":
            return filter_value in cell_value
        elif self.filter_type == "equals":
            return cell_value == filter_value
        elif self.filter_type == "starts_with":
            return cell_value.startswith(filter_value)
        elif self.filter_type == "ends_with":
            return cell_value.endswith(filter_value)

        return True


class CsvFilterWidget(QWidget):
    """Widget for filtering and searching CSV data"""

    # Signals
    filters_changed = pyqtSignal()  # Emitted when filters change

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: Optional[CsvDataModel] = None
        self.column_filters: Dict[str, ColumnFilter] = {}
        self.global_search_text = ""
        self.case_sensitive_search = False

        # UI elements
        self.search_input = None
        self.case_sensitive_cb = None
        self.column_filters_area = None
        self.filter_widgets = {}

        # Debounce timer for live search
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.filters_changed.emit)

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        # Simple search section
        self.create_search_section(layout)

        # Column filters section
        self.create_column_filters_section(layout)

        # Filter controls
        self.create_filter_controls(layout)

    def create_search_section(self, layout):
        """Create a simple, compact search section"""
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Global search...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_input)

        self.case_sensitive_cb = QCheckBox("Case")
        self.case_sensitive_cb.setToolTip("Case sensitive search")
        self.case_sensitive_cb.toggled.connect(self._on_case_sensitive_changed)
        search_layout.addWidget(self.case_sensitive_cb)

        layout.addLayout(search_layout)



    def create_column_filters_section(self, layout):
        """Create column-specific filters section"""
        filters_group = QGroupBox("Column Filters")
        filters_layout = QVBoxLayout(filters_group)

        # Scroll area for column filters
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)

        self.column_filters_area = QWidget()
        self.column_filters_layout = QVBoxLayout(self.column_filters_area)
        self.column_filters_layout.addStretch()

        scroll.setWidget(self.column_filters_area)
        filters_layout.addWidget(scroll)

        layout.addWidget(filters_group)

    def create_filter_controls(self, layout):
        """Create filter control buttons"""
        controls_layout = QHBoxLayout()

        clear_btn = QPushButton("Clear All Filters")
        clear_btn.clicked.connect(self.clear_all_filters)
        controls_layout.addWidget(clear_btn)

        controls_layout.addStretch()

        # Filter status label
        self.status_label = QLabel("No filters active")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        controls_layout.addWidget(self.status_label)

        layout.addLayout(controls_layout)



    def set_model(self, model: CsvDataModel):
        """Set the CSV data model and update filter options"""
        self.model = model
        self.update_column_filters()

    def update_column_filters(self):
        """Update column filter widgets based on current model"""
        # Clear existing filter widgets
        self.clear_column_filter_widgets()

        if not self.model or not self.model.columns:
            return

        # Create filter widget for each column
        for col in self.model.columns:
            self.create_column_filter_widget(col)

        self.update_status()

    def clear_column_filter_widgets(self):
        """Remove all column filter widgets"""
        for widget_dict in self.filter_widgets.values():
            widget = widget_dict['widget']
            widget.setParent(None)
            widget.deleteLater()
        self.filter_widgets.clear()
        self.column_filters.clear()

    def create_column_filter_widget(self, column: ColumnInfo):
        """Create filter widget for a specific column"""
        # Create filter object
        col_filter = ColumnFilter(column.name)
        self.column_filters[column.name] = col_filter

        # Create UI widget
        filter_widget = QFrame()
        filter_widget.setFrameStyle(QFrame.Shape.Box)
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(5, 5, 5, 5)

        # Column name label
        name_label = QLabel(column.name)
        name_label.setMinimumWidth(100)
        font = QFont()
        font.setBold(True)
        name_label.setFont(font)
        filter_layout.addWidget(name_label)

        # Filter type combo
        type_combo = QComboBox()
        type_combo.addItems(["contains", "equals", "starts with", "ends with"])
        type_combo.currentTextChanged.connect(
            lambda text, col=column.name: self._on_filter_type_changed(col, text)
        )
        filter_layout.addWidget(type_combo)

        # Filter value input
        value_input = QLineEdit()
        value_input.setPlaceholderText(f"Filter {column.name}...")
        value_input.textChanged.connect(
            lambda text, col=column.name: self._on_filter_value_changed(col, text)
        )
        filter_layout.addWidget(value_input)

        # Enable/disable checkbox
        enable_cb = QCheckBox("Active")
        enable_cb.setChecked(True)
        enable_cb.toggled.connect(
            lambda checked, col=column.name: self._on_filter_enabled_changed(col, checked)
        )
        filter_layout.addWidget(enable_cb)

        # Store references
        self.filter_widgets[column.name] = {
            'widget': filter_widget,
            'type_combo': type_combo,
            'value_input': value_input,
            'enable_cb': enable_cb
        }

        # Insert before the stretch
        self.column_filters_layout.insertWidget(
            self.column_filters_layout.count() - 1, filter_widget
        )

    def _on_search_text_changed(self, text: str):
        """Handle global search text change"""
        self.global_search_text = text
        self.search_timer.start(300)  # Debounce 300ms
        self.update_status()

    def _on_case_sensitive_changed(self, checked: bool):
        """Handle case sensitivity change"""
        self.case_sensitive_search = checked
        self.filters_changed.emit()
        self.update_status()

    def _on_filter_type_changed(self, column_name: str, filter_type: str):
        """Handle column filter type change"""
        if column_name in self.column_filters:
            # Convert display text to internal format
            type_map = {
                "contains": "contains",
                "equals": "equals",
                "starts with": "starts_with",
                "ends with": "ends_with"
            }
            self.column_filters[column_name].filter_type = type_map.get(filter_type, "contains")
            self.filters_changed.emit()
            self.update_status()

    def _on_filter_value_changed(self, column_name: str, value: str):
        """Handle column filter value change"""
        if column_name in self.column_filters:
            self.column_filters[column_name].value = value
            self.search_timer.start(300)  # Debounce
            self.update_status()

    def _on_filter_enabled_changed(self, column_name: str, enabled: bool):
        """Handle column filter enable/disable"""
        if column_name in self.column_filters:
            self.column_filters[column_name].enabled = enabled
            self.filters_changed.emit()
            self.update_status()

    def clear_all_filters(self):
        """Clear all filters"""
        # Clear global search
        if self.search_input:
            self.search_input.clear()
        self.global_search_text = ""
        self.case_sensitive_search = False
        if self.case_sensitive_cb:
            self.case_sensitive_cb.setChecked(False)

        # Clear column filters
        for col_name, widgets in self.filter_widgets.items():
            if 'value_input' in widgets and widgets['value_input']:
                widgets['value_input'].clear()
            if 'enable_cb' in widgets and widgets['enable_cb']:
                widgets['enable_cb'].setChecked(True)
            if 'type_combo' in widgets and widgets['type_combo']:
                widgets['type_combo'].setCurrentIndex(0)


            if col_name in self.column_filters:
                col_filter = self.column_filters[col_name]
                col_filter.value = ""
                col_filter.filter_type = "contains"
                col_filter.enabled = True

        self.filters_changed.emit()
        self.update_status()

    def update_status(self):
        """Update filter status display"""
        active_filters = []

        # Check global search
        if self.global_search_text:
            active_filters.append("Global search")

        # Check column filters
        for col_filter in self.column_filters.values():
            if col_filter.enabled and col_filter.value:
                active_filters.append(f"{col_filter.column_name}")

        if active_filters:
            status = f"Active filters: {', '.join(active_filters)}"
        else:
            status = "No filters active"

        self.status_label.setText(status)

    def matches_filters(self, row: CsvRow) -> bool:
        """Check if a row matches all active filters"""
        # Check global search
        if self.global_search_text:
            search_text = self.global_search_text
            if not self.case_sensitive_search:
                search_text = search_text.lower()

            found_in_any_column = False
            for col in self.model.columns if self.model else []:
                cell_value = row.get_value(col.name, "")
                if not self.case_sensitive_search:
                    cell_value = cell_value.lower()

                if search_text in cell_value:
                    found_in_any_column = True
                    break

            if not found_in_any_column:
                return False

        # Check column filters
        for col_filter in self.column_filters.values():
            if not col_filter.matches(row):
                return False

        return True

    def get_filtered_rows(self, rows: List[CsvRow]) -> List[CsvRow]:
        """Return list of rows that match current filters"""
        if not self.has_active_filters():
            return rows

        return [row for row in rows if self.matches_filters(row)]

    def has_active_filters(self) -> bool:
        """Check if any filters are currently active"""
        # Check global search
        if self.global_search_text:
            return True

        # Check column filters
        for col_filter in self.column_filters.values():
            if col_filter.enabled and col_filter.value:
                return True

        return False

    def get_filter_summary(self) -> Dict[str, Any]:
        """Get summary of current filter state"""
        return {
            'global_search': self.global_search_text,
            'case_sensitive': self.case_sensitive_search,
            'column_filters': {
                name: {
                    'type': f.filter_type,
                    'value': f.value,
                    'enabled': f.enabled
                }
                for name, f in self.column_filters.items()
                if f.value  # Only include non-empty filters
            },
            'has_active_filters': self.has_active_filters()
        }
