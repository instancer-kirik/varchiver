"""
Format Converter Widget for Varchiver

GUI widget for converting between TOON, JSON, and CSV formats with real-time preview,
token savings estimation, and batch conversion capabilities.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QComboBox,
    QLabel,
    QFileDialog,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QGroupBox,
    QCheckBox,
    QSpinBox,
    QProgressBar,
    QListWidget,
    QListWidgetItem,
    QGridLayout,
    QFrame,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QFont,
    QTextCharFormat,
    QColor,
    QSyntaxHighlighter,
    QTextDocument,
)

from ..utils.format_converter import FormatConverter


class ConversionWorker(QThread):
    """Background worker for format conversions"""

    finished = pyqtSignal(str, bool, str)  # result, success, error_msg
    progress = pyqtSignal(int)

    def __init__(self, converter, input_data, input_format, output_format, options):
        super().__init__()
        self.converter = converter
        self.input_data = input_data
        self.input_format = input_format
        self.output_format = output_format
        self.options = options

    def run(self):
        try:
            if self.input_format == "json" and self.output_format == "toon":
                result = self.converter.json_to_toon(self.input_data, **self.options)
            elif self.input_format == "toon" and self.output_format == "json":
                result = self.converter.toon_to_json(self.input_data, **self.options)
            elif self.input_format == "json" and self.output_format == "csv":
                result = self.converter.json_to_csv(self.input_data)
            elif self.input_format == "csv" and self.output_format == "json":
                result = self.converter.csv_to_json(self.input_data, **self.options)
            elif self.input_format == "toon" and self.output_format == "csv":
                result = self.converter.toon_to_csv(self.input_data)
            elif self.input_format == "csv" and self.output_format == "toon":
                result = self.converter.csv_to_toon(self.input_data, **self.options)
            else:
                raise ValueError(
                    f"Unsupported conversion: {self.input_format} -> {self.output_format}"
                )

            self.finished.emit(result, True, "")
        except Exception as e:
            self.finished.emit("", False, str(e))


class SyntaxHighlighter(QSyntaxHighlighter):
    """Simple syntax highlighter for JSON and TOON"""

    def __init__(self, document: QTextDocument, format_type: str):
        super().__init__(document)
        self.format_type = format_type
        self.setup_formats()

    def setup_formats(self):
        self.formats = {}

        # JSON highlighting
        if self.format_type == "json":
            # Strings
            string_format = QTextCharFormat()
            string_format.setForeground(QColor("#d69e2e"))
            self.formats["string"] = string_format

            # Keys
            key_format = QTextCharFormat()
            key_format.setForeground(QColor("#3182ce"))
            key_format.setFontWeight(QFont.Weight.Bold)
            self.formats["key"] = key_format

            # Numbers
            number_format = QTextCharFormat()
            number_format.setForeground(QColor("#38a169"))
            self.formats["number"] = number_format

        # TOON highlighting
        elif self.format_type == "toon":
            # Keys/headers
            key_format = QTextCharFormat()
            key_format.setForeground(QColor("#3182ce"))
            key_format.setFontWeight(QFont.Weight.Bold)
            self.formats["key"] = key_format

            # Array headers
            array_format = QTextCharFormat()
            array_format.setForeground(QColor("#805ad5"))
            array_format.setFontWeight(QFont.Weight.Bold)
            self.formats["array"] = array_format

            # Values
            value_format = QTextCharFormat()
            value_format.setForeground(QColor("#38a169"))
            self.formats["value"] = value_format

    def highlightBlock(self, text: str):
        if self.format_type == "json":
            self.highlight_json(text)
        elif self.format_type == "toon":
            self.highlight_toon(text)

    def highlight_json(self, text: str):
        # Simple JSON highlighting
        import re

        # Highlight strings
        string_pattern = r'"[^"\\]*(\\.[^"\\]*)*"'
        for match in re.finditer(string_pattern, text):
            start, end = match.span()
            if text[start - 1 : start] == ":":  # It's a key
                self.setFormat(
                    start, end - start, self.formats.get("key", QTextCharFormat())
                )
            else:
                self.setFormat(
                    start, end - start, self.formats.get("string", QTextCharFormat())
                )

        # Highlight numbers
        number_pattern = r"\b-?\d+\.?\d*\b"
        for match in re.finditer(number_pattern, text):
            start, end = match.span()
            self.setFormat(
                start, end - start, self.formats.get("number", QTextCharFormat())
            )

    def highlight_toon(self, text: str):
        import re

        # Highlight array headers
        array_pattern = r"\[[^\]]+\](\{[^}]+\})?:"
        for match in re.finditer(array_pattern, text):
            start, end = match.span()
            self.setFormat(
                start, end - start, self.formats.get("array", QTextCharFormat())
            )

        # Highlight keys
        key_pattern = r"^[\s]*([^:\s]+):"
        for match in re.finditer(key_pattern, text, re.MULTILINE):
            start, end = match.span(1)
            self.setFormat(
                start, end - start, self.formats.get("key", QTextCharFormat())
            )


class FormatConverterWidget(QWidget):
    """Main format converter widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.converter = FormatConverter()
        self.current_worker = None
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Format Converter - TOON, JSON, CSV")
        layout = QVBoxLayout(self)

        # Control panel
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Input panel
        input_panel = self.create_input_panel()
        splitter.addWidget(input_panel)

        # Output panel
        output_panel = self.create_output_panel()
        splitter.addWidget(output_panel)

        # Set splitter proportions
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)

        # Status bar
        status_panel = self.create_status_panel()
        layout.addWidget(status_panel)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

    def create_control_panel(self) -> QWidget:
        """Create the control panel with format selection and options"""
        panel = QGroupBox("Conversion Settings")
        layout = QGridLayout(panel)

        # Format selection
        layout.addWidget(QLabel("From:"), 0, 0)
        self.input_format_combo = QComboBox()
        self.input_format_combo.addItems(["json", "toon", "csv"])
        layout.addWidget(self.input_format_combo, 0, 1)

        layout.addWidget(QLabel("To:"), 0, 2)
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(["toon", "json", "csv"])
        layout.addWidget(self.output_format_combo, 0, 3)

        # File operations
        self.load_btn = QPushButton("Load File")
        layout.addWidget(self.load_btn, 0, 4)

        self.save_btn = QPushButton("Save As...")
        layout.addWidget(self.save_btn, 0, 5)

        # TOON options
        toon_options = QGroupBox("TOON Options")
        toon_layout = QHBoxLayout(toon_options)

        toon_layout.addWidget(QLabel("Delimiter:"))
        self.delimiter_combo = QComboBox()
        self.delimiter_combo.addItems(["Comma (,)", "Tab (\\t)", "Pipe (|)"])
        toon_layout.addWidget(self.delimiter_combo)

        toon_layout.addWidget(QLabel("Indent:"))
        self.indent_spin = QSpinBox()
        self.indent_spin.setRange(1, 8)
        self.indent_spin.setValue(2)
        toon_layout.addWidget(self.indent_spin)

        self.length_marker_check = QCheckBox("Length Markers (#)")
        toon_layout.addWidget(self.length_marker_check)

        layout.addWidget(toon_options, 1, 0, 1, 6)

        # Convert button
        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 8px; }"
        )
        layout.addWidget(self.convert_btn, 2, 0, 1, 6)

        return panel

    def create_input_panel(self) -> QWidget:
        """Create input text panel"""
        panel = QGroupBox("Input")
        layout = QVBoxLayout(panel)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Paste your data here or load from file...")
        self.input_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.input_text)

        # Input info
        self.input_info = QLabel("Ready")
        self.input_info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.input_info)

        return panel

    def create_output_panel(self) -> QWidget:
        """Create output text panel with tabs for different views"""
        panel = QGroupBox("Output")
        layout = QVBoxLayout(panel)

        # Output tabs
        self.output_tabs = QTabWidget()

        # Converted output tab
        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setReadOnly(True)
        self.output_tabs.addTab(self.output_text, "Converted")

        # Stats tab
        self.stats_widget = self.create_stats_widget()
        self.output_tabs.addTab(self.stats_widget, "Statistics")

        layout.addWidget(self.output_tabs)

        # Output info
        self.output_info = QLabel("No conversion yet")
        self.output_info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.output_info)

        return panel

    def create_stats_widget(self) -> QWidget:
        """Create statistics widget"""
        widget = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)

        self.stats_labels = {}
        stats_items = [
            ("input_size", "Input Size:"),
            ("output_size", "Output Size:"),
            ("size_reduction", "Size Reduction:"),
            ("estimated_tokens_input", "Est. Input Tokens:"),
            ("estimated_tokens_output", "Est. Output Tokens:"),
            ("token_savings", "Token Savings:"),
            ("conversion_time", "Conversion Time:"),
        ]

        for key, label in stats_items:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            value_label = QLabel("-")
            value_label.setStyleSheet("font-weight: bold;")
            row.addWidget(value_label)
            row.addStretch()

            self.stats_labels[key] = value_label
            layout.addLayout(row)

        layout.addStretch()
        widget.setWidget(content)
        return widget

    def create_status_panel(self) -> QWidget:
        """Create status panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(panel)

        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Token efficiency indicator
        self.efficiency_label = QLabel("")
        self.efficiency_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.efficiency_label)

        return panel

    def setup_connections(self):
        """Setup signal connections"""
        self.convert_btn.clicked.connect(self.convert)
        self.load_btn.clicked.connect(self.load_file)
        self.save_btn.clicked.connect(self.save_file)
        self.input_text.textChanged.connect(self.on_input_changed)
        self.input_format_combo.currentTextChanged.connect(
            self.update_syntax_highlighting
        )
        self.output_format_combo.currentTextChanged.connect(
            self.update_syntax_highlighting
        )

        # Auto-convert timer
        self.auto_convert_timer = QTimer()
        self.auto_convert_timer.setSingleShot(True)
        self.auto_convert_timer.timeout.connect(self.auto_convert)

        # Update highlighting initially
        self.update_syntax_highlighting()

    def update_syntax_highlighting(self):
        """Update syntax highlighting based on format selection"""
        input_format = self.input_format_combo.currentText()
        output_format = self.output_format_combo.currentText()

        # Input highlighting
        if hasattr(self, "input_highlighter"):
            self.input_highlighter.setDocument(None)
        self.input_highlighter = SyntaxHighlighter(
            self.input_text.document(), input_format
        )

        # Output highlighting
        if hasattr(self, "output_highlighter"):
            self.output_highlighter.setDocument(None)
        self.output_highlighter = SyntaxHighlighter(
            self.output_text.document(), output_format
        )

    def on_input_changed(self):
        """Handle input text changes"""
        text = self.input_text.toPlainText().strip()

        if text:
            char_count = len(text)
            line_count = text.count("\n") + 1
            self.input_info.setText(f"{char_count} chars, {line_count} lines")

            # Auto-convert with delay
            self.auto_convert_timer.start(1000)  # 1 second delay
        else:
            self.input_info.setText("Ready")
            self.output_text.clear()
            self.output_info.setText("No conversion yet")

    def auto_convert(self):
        """Auto-convert with current settings (if input is small enough)"""
        text = self.input_text.toPlainText().strip()
        if text and len(text) < 10000:  # Only auto-convert small inputs
            self.convert()

    def get_conversion_options(self) -> Dict[str, Any]:
        """Get current conversion options"""
        delimiter_map = {"Comma (,)": ",", "Tab (\\t)": "\t", "Pipe (|)": "|"}

        return {
            "indent": self.indent_spin.value(),
            "delimiter": delimiter_map[self.delimiter_combo.currentText()],
            "length_marker": self.length_marker_check.isChecked(),
            "table_name": "data",
        }

    def convert(self):
        """Perform conversion"""
        input_text = self.input_text.toPlainText().strip()
        if not input_text:
            QMessageBox.warning(self, "Warning", "Please enter some data to convert.")
            return

        input_format = self.input_format_combo.currentText()
        output_format = self.output_format_combo.currentText()
        options = self.get_conversion_options()

        # Validate input format
        try:
            if input_format == "json":
                json.loads(input_text)  # Validate JSON
        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self, "Invalid JSON", f"Input is not valid JSON:\n{str(e)}"
            )
            return

        self.status_label.setText("Converting...")
        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Start conversion in background thread
        self.current_worker = ConversionWorker(
            self.converter, input_text, input_format, output_format, options
        )
        self.current_worker.finished.connect(self.on_conversion_finished)
        self.current_worker.start()

    def on_conversion_finished(self, result: str, success: bool, error_msg: str):
        """Handle conversion completion"""
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)

        if success:
            self.output_text.setPlainText(result)

            # Update stats
            self.update_statistics(result)

            self.status_label.setText("Conversion completed successfully")
            self.output_info.setText(
                f"Converted to {self.output_format_combo.currentText().upper()}"
            )

            # Update efficiency indicator
            if self.output_format_combo.currentText() == "toon":
                self.show_efficiency_indicator()
        else:
            self.status_label.setText(f"Conversion failed: {error_msg}")
            QMessageBox.critical(
                self, "Conversion Error", f"Conversion failed:\n{error_msg}"
            )

        self.current_worker = None

    def update_statistics(self, output: str):
        """Update conversion statistics"""
        input_text = self.input_text.toPlainText()

        input_size = len(input_text)
        output_size = len(output)
        size_reduction = (
            ((input_size - output_size) / input_size * 100) if input_size > 0 else 0
        )

        # Simple token estimation
        input_tokens = (
            len(input_text.split())
            + input_text.count(",")
            + input_text.count("{")
            + input_text.count("}")
        )
        output_tokens = len(output.split()) + output.count(",") + output.count(":")
        token_savings = (
            ((input_tokens - output_tokens) / input_tokens * 100)
            if input_tokens > 0
            else 0
        )

        self.stats_labels["input_size"].setText(f"{input_size} bytes")
        self.stats_labels["output_size"].setText(f"{output_size} bytes")
        self.stats_labels["size_reduction"].setText(f"{size_reduction:.1f}%")
        self.stats_labels["estimated_tokens_input"].setText(str(input_tokens))
        self.stats_labels["estimated_tokens_output"].setText(str(output_tokens))
        self.stats_labels["token_savings"].setText(f"{token_savings:.1f}%")

        # Color code the savings
        savings_color = (
            "green" if token_savings > 0 else "red" if token_savings < 0 else "gray"
        )
        self.stats_labels["token_savings"].setStyleSheet(
            f"color: {savings_color}; font-weight: bold;"
        )
        self.stats_labels["size_reduction"].setStyleSheet(
            f"color: {savings_color}; font-weight: bold;"
        )

    def show_efficiency_indicator(self):
        """Show token efficiency indicator"""
        token_savings = float(self.stats_labels["token_savings"].text().rstrip("%"))

        if token_savings > 30:
            self.efficiency_label.setText("🟢 Excellent efficiency")
            self.efficiency_label.setStyleSheet("color: green; font-weight: bold;")
        elif token_savings > 15:
            self.efficiency_label.setText("🟡 Good efficiency")
            self.efficiency_label.setStyleSheet("color: orange; font-weight: bold;")
        elif token_savings > 0:
            self.efficiency_label.setText("🟠 Moderate efficiency")
            self.efficiency_label.setStyleSheet("color: #ff6600; font-weight: bold;")
        else:
            self.efficiency_label.setText("🔴 No savings")
            self.efficiency_label.setStyleSheet("color: red; font-weight: bold;")

    def load_file(self):
        """Load file into input area"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load File",
            "",
            "All Supported (*.json *.toon *.csv);;JSON Files (*.json);;TOON Files (*.toon);;CSV Files (*.csv);;All Files (*.*)",
        )

        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.input_text.setPlainText(content)

                # Auto-detect format from extension
                ext = Path(file_path).suffix.lower().lstrip(".")
                if ext in ["json", "toon", "csv"]:
                    index = self.input_format_combo.findText(ext)
                    if index >= 0:
                        self.input_format_combo.setCurrentIndex(index)

                self.status_label.setText(f"Loaded: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")

    def save_file(self):
        """Save output to file"""
        output_text = self.output_text.toPlainText()
        if not output_text.strip():
            QMessageBox.warning(self, "Warning", "No output to save.")
            return

        output_format = self.output_format_combo.currentText()
        file_filter = {
            "json": "JSON Files (*.json)",
            "toon": "TOON Files (*.toon)",
            "csv": "CSV Files (*.csv)",
        }.get(output_format, "All Files (*.*)")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Output",
            f"converted.{output_format}",
            f"{file_filter};;All Files (*.*)",
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(output_text)
                self.status_label.setText(f"Saved: {os.path.basename(file_path)}")
                QMessageBox.information(
                    self, "Success", f"Output saved to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")
