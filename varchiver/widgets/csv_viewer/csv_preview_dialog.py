#!/usr/bin/env python3
"""
CSV Preview Dialog - Preview CSV file structure and data before loading

Provides a dialog to preview CSV file structure, columns, and sample data
before committing to load the entire file.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import csv

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QGroupBox, QTextEdit, QDialogButtonBox,
    QHeaderView, QScrollArea, QFrame, QFormLayout, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap

from .csv_data_model import CsvStructureDetector


class FileAnalysisWorker(QThread):
    """Worker thread for analyzing large CSV files"""

    analysis_complete = pyqtSignal(dict)
    progress_update = pyqtSignal(str)

    def __init__(self, file_path: Path, max_preview_rows: int = 10):
        super().__init__()
        self.file_path = file_path
        self.max_preview_rows = max_preview_rows

    def run(self):
        """Analyze the CSV file in background thread"""
        try:
            self.progress_update.emit("Detecting file structure...")

            # Get basic structure
            structure = CsvStructureDetector.detect_structure(self.file_path)

            if structure['error']:
                self.analysis_complete.emit(structure)
                return

            self.progress_update.emit("Loading preview data...")

            # Get preview data
            preview_data = []
            with open(self.file_path, 'r', encoding=structure['encoding']) as f:
                reader = csv.DictReader(f, delimiter=structure['delimiter'])
                for i, row in enumerate(reader):
                    if i >= self.max_preview_rows:
                        break
                    preview_data.append(row)

            structure['preview_data'] = preview_data

            self.progress_update.emit("Analysis complete")
            self.analysis_complete.emit(structure)

        except Exception as e:
            error_structure = {
                'error': str(e),
                'headers': [],
                'total_rows': 0,
                'preview_data': []
            }
            self.analysis_complete.emit(error_structure)


class CsvPreviewDialog(QDialog):
    """Dialog for previewing CSV file before loading"""

    def __init__(self, file_path: Path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.structure_info = None
        self.analysis_worker = None

        self.init_ui()
        self.start_analysis()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(f"CSV Preview: {self.file_path.name}")
        self.setModal(True)
        self.resize(900, 700)

        layout = QVBoxLayout(self)

        # File information section
        self.create_file_info_section(layout)

        # Structure information section
        self.create_structure_section(layout)

        # Preview table section
        self.create_preview_section(layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_label = QLabel("Analyzing file...")

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        layout.addLayout(progress_layout)

        # Buttons
        self.create_buttons(layout)

        # Initially disable OK button until analysis completes
        self.ok_button.setEnabled(False)

    def create_file_info_section(self, layout):
        """Create file information display section"""
        file_group = QGroupBox("File Information")
        file_layout = QFormLayout(file_group)

        # File details
        self.file_name_label = QLabel(self.file_path.name)
        self.file_name_label.setWordWrap(True)
        file_layout.addRow("File Name:", self.file_name_label)

        self.file_size_label = QLabel("Analyzing...")
        file_layout.addRow("File Size:", self.file_size_label)

        self.file_path_label = QLabel(str(self.file_path.parent))
        self.file_path_label.setWordWrap(True)
        self.file_path_label.setStyleSheet("color: #666;")
        file_layout.addRow("Location:", self.file_path_label)

        layout.addWidget(file_group)

    def create_structure_section(self, layout):
        """Create CSV structure information section"""
        structure_group = QGroupBox("CSV Structure")
        structure_layout = QFormLayout(structure_group)

        self.encoding_label = QLabel("Detecting...")
        structure_layout.addRow("Encoding:", self.encoding_label)

        self.delimiter_label = QLabel("Detecting...")
        structure_layout.addRow("Delimiter:", self.delimiter_label)

        self.rows_label = QLabel("Counting...")
        structure_layout.addRow("Total Rows:", self.rows_label)

        self.columns_label = QLabel("Detecting...")
        structure_layout.addRow("Columns:", self.columns_label)

        # Column names display
        self.columns_text = QTextEdit()
        self.columns_text.setMaximumHeight(80)
        self.columns_text.setReadOnly(True)
        self.columns_text.setPlainText("Analyzing columns...")
        structure_layout.addRow("Column Names:", self.columns_text)

        layout.addWidget(structure_group)

    def create_preview_section(self, layout):
        """Create data preview table section"""
        preview_group = QGroupBox("Data Preview (First 10 Rows)")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        self.preview_table.verticalHeader().setVisible(False)

        # Set reasonable maximum height
        self.preview_table.setMaximumHeight(300)

        preview_layout.addWidget(self.preview_table)
        layout.addWidget(preview_group)

    def create_buttons(self, layout):
        """Create dialog buttons"""
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("Load CSV")
        self.ok_button.setDefault(True)

        cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText("Cancel")

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)

    def start_analysis(self):
        """Start background analysis of the CSV file"""
        self.analysis_worker = FileAnalysisWorker(self.file_path)
        self.analysis_worker.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_worker.progress_update.connect(self.on_progress_update)
        self.analysis_worker.start()

    def on_progress_update(self, message: str):
        """Handle progress updates from analysis worker"""
        self.progress_label.setText(message)

    def on_analysis_complete(self, structure_info: Dict[str, Any]):
        """Handle completion of file analysis"""
        self.structure_info = structure_info

        # Hide progress bar
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        if structure_info.get('error'):
            self.show_error(structure_info['error'])
            return

        # Update UI with analysis results
        self.update_file_info()
        self.update_structure_info()
        self.update_preview_table()

        # Enable OK button
        self.ok_button.setEnabled(True)

    def show_error(self, error_message: str):
        """Show error information"""
        self.file_size_label.setText("Error")
        self.encoding_label.setText("Error")
        self.delimiter_label.setText("Error")
        self.rows_label.setText("Error")
        self.columns_label.setText("Error")
        self.columns_text.setPlainText(f"Error analyzing file: {error_message}")

        # Update button text
        self.ok_button.setText("Close")
        self.ok_button.setEnabled(True)

    def update_file_info(self):
        """Update file information display"""
        file_size = self.structure_info.get('file_size', 0)

        # Format file size
        if file_size < 1024:
            size_text = f"{file_size} bytes"
        elif file_size < 1024 * 1024:
            size_text = f"{file_size / 1024:.1f} KB"
        else:
            size_text = f"{file_size / (1024 * 1024):.1f} MB"

        self.file_size_label.setText(size_text)

    def update_structure_info(self):
        """Update CSV structure information display"""
        encoding = self.structure_info.get('encoding', 'Unknown')
        delimiter = self.structure_info.get('delimiter', 'Unknown')
        total_rows = self.structure_info.get('total_rows', 0)
        headers = self.structure_info.get('headers', [])

        self.encoding_label.setText(encoding)

        # Format delimiter display
        delimiter_display = {
            ',': 'Comma (,)',
            ';': 'Semicolon (;)',
            '\t': 'Tab',
            '|': 'Pipe (|)'
        }.get(delimiter, f"'{delimiter}'")
        self.delimiter_label.setText(delimiter_display)

        self.rows_label.setText(f"{total_rows:,}")
        self.columns_label.setText(f"{len(headers)} columns")

        # Show column names
        if headers:
            columns_text = "Columns found:\n" + "\n".join(f"• {col}" for col in headers)
        else:
            columns_text = "No columns detected"
        self.columns_text.setPlainText(columns_text)

    def update_preview_table(self):
        """Update the preview table with sample data"""
        headers = self.structure_info.get('headers', [])
        preview_data = self.structure_info.get('preview_data', [])

        if not headers or not preview_data:
            self.preview_table.setRowCount(1)
            self.preview_table.setColumnCount(1)
            self.preview_table.setHorizontalHeaderLabels(["Preview"])
            self.preview_table.setItem(0, 0, QTableWidgetItem("No preview data available"))
            return

        # Set up table dimensions
        self.preview_table.setRowCount(len(preview_data))
        self.preview_table.setColumnCount(len(headers))
        self.preview_table.setHorizontalHeaderLabels(headers)

        # Populate table with preview data
        for row_idx, row_data in enumerate(preview_data):
            for col_idx, header in enumerate(headers):
                value = row_data.get(header, "")

                # Truncate long values for display
                display_value = str(value)
                if len(display_value) > 100:
                    display_value = display_value[:97] + "..."

                item = QTableWidgetItem(display_value)
                item.setToolTip(str(value))  # Full value in tooltip
                self.preview_table.setItem(row_idx, col_idx, item)

        # Adjust column widths
        self.preview_table.resizeColumnsToContents()

        # Ensure minimum column width and maximum table width
        header = self.preview_table.horizontalHeader()
        for i in range(len(headers)):
            current_width = header.sectionSize(i)
            if current_width < 80:
                header.resizeSection(i, 80)
            elif current_width > 200:
                header.resizeSection(i, 200)

    def get_structure_info(self) -> Optional[Dict[str, Any]]:
        """Get the analyzed structure information"""
        return self.structure_info

    def closeEvent(self, event):
        """Handle dialog close event"""
        if self.analysis_worker and self.analysis_worker.isRunning():
            self.analysis_worker.quit()
            self.analysis_worker.wait()
        super().closeEvent(event)

    @staticmethod
    def preview_csv_file(file_path: Path, parent=None) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Static method to show CSV preview dialog

        Returns:
            (user_accepted, structure_info)
        """
        dialog = CsvPreviewDialog(file_path, parent)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            return True, dialog.get_structure_info()
        else:
            return False, None
