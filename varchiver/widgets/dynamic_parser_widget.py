"""
Dynamic Anything Parser GUI Widget
A comprehensive GUI interface for the dynamic parser with format detection, parsing, and conversion capabilities

Features:
- Drag & drop file loading
- Real-time format detection with confidence visualization
- Interactive parsing with structure preview
- Format conversion with visual diff
- Batch processing interface
- Settings and preferences
- Error handling with recovery options

Author: VArchiver Team
Version: 1.0.0
"""

import sys
import json
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List
import threading
import time

try:
    from PyQt5.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QGridLayout,
        QLabel,
        QTextEdit,
        QPushButton,
        QComboBox,
        QProgressBar,
        QTabWidget,
        QSplitter,
        QGroupBox,
        QCheckBox,
        QSpinBox,
        QFileDialog,
        QMessageBox,
        QTreeWidget,
        QTreeWidgetItem,
        QTableWidget,
        QTableWidgetItem,
        QStatusBar,
        QFrame,
        QScrollArea,
        QSlider,
        QRadioButton,
        QButtonGroup,
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QMimeData
    from PyQt5.QtGui import (
        QFont,
        QColor,
        QPalette,
        QDragEnterEvent,
        QDropEvent,
        QPixmap,
    )
except ImportError:
    print("PyQt5 not available. GUI features disabled.")
    sys.exit(1)

# Add path for dynamic parser imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from varchiver.utils.dynamic_parser import (
        DynamicAnythingParser,
        FormatType,
        FormatDetector,
        ParseResult,
        FormatDetectionResult,
        parse_anything,
        parse_file,
        detect_format,
    )
except ImportError as e:
    print(f"Warning: Dynamic parser not available: {e}")
    DynamicAnythingParser = None


class FormatDetectionWorker(QThread):
    """Background worker for format detection"""

    detection_complete = pyqtSignal(object)  # FormatDetectionResult
    error_occurred = pyqtSignal(str)

    def __init__(self, content: str, filename: Optional[str] = None):
        super().__init__()
        self.content = content
        self.filename = filename

    def run(self):
        try:
            if DynamicAnythingParser is None:
                self.error_occurred.emit("Dynamic parser not available")
                return

            detector = FormatDetector()
            result = detector.detect_format(self.content, self.filename)
            self.detection_complete.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


class ParseWorker(QThread):
    """Background worker for parsing operations"""

    parse_complete = pyqtSignal(object)  # ParseResult
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(int)

    def __init__(
        self,
        content: str,
        filename: Optional[str] = None,
        format_hint: Optional[FormatType] = None,
        **options,
    ):
        super().__init__()
        self.content = content
        self.filename = filename
        self.format_hint = format_hint
        self.options = options

    def run(self):
        try:
            if DynamicAnythingParser is None:
                self.error_occurred.emit("Dynamic parser not available")
                return

            parser = DynamicAnythingParser()

            # Simulate progress for large content
            content_size = len(self.content)
            if content_size > 10000:
                for i in range(0, 100, 20):
                    self.progress_update.emit(i)
                    time.sleep(0.1)

            result = parser.parse(
                self.content,
                filename=self.filename,
                format_hint=self.format_hint,
                **self.options,
            )

            self.progress_update.emit(100)
            self.parse_complete.emit(result)

        except Exception as e:
            self.error_occurred.emit(str(e))


class FormatVisualizationWidget(QWidget):
    """Widget for visualizing format detection results"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Detection results display
        self.detection_label = QLabel("No format detected")
        self.detection_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
        """)
        layout.addWidget(self.detection_label)

        # Confidence meter
        confidence_group = QGroupBox("Detection Confidence")
        confidence_layout = QVBoxLayout()

        self.confidence_bar = QProgressBar()
        self.confidence_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff4444, stop:0.5 #ffaa00, stop:1.0 #44ff44);
                border-radius: 3px;
            }
        """)
        confidence_layout.addWidget(self.confidence_bar)

        self.confidence_text = QLabel("0% confidence")
        confidence_layout.addWidget(self.confidence_text)

        confidence_group.setLayout(confidence_layout)
        layout.addWidget(confidence_group)

        # Indicators list
        indicators_group = QGroupBox("Detection Indicators")
        indicators_layout = QVBoxLayout()

        self.indicators_list = QTreeWidget()
        self.indicators_list.setHeaderLabels(["Indicator", "Type"])
        self.indicators_list.setMaximumHeight(150)
        indicators_layout.addWidget(self.indicators_list)

        indicators_group.setLayout(indicators_layout)
        layout.addWidget(indicators_group)

        self.setLayout(layout)

    def update_detection_result(self, result: FormatDetectionResult):
        """Update display with detection results"""
        # Update main label
        format_name = result.format_type.name
        confidence = result.confidence

        if confidence >= 0.8:
            color = "#4CAF50"  # Green
            status = "High Confidence"
        elif confidence >= 0.5:
            color = "#FF9800"  # Orange
            status = "Medium Confidence"
        else:
            color = "#F44336"  # Red
            status = "Low Confidence"

        self.detection_label.setText(f"Format: {format_name}")
        self.detection_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                border: 2px solid {color};
                border-radius: 5px;
                background-color: {color}20;
                color: {color};
            }}
        """)

        # Update confidence bar
        confidence_percent = min(int(confidence * 100), 100)
        self.confidence_bar.setValue(confidence_percent)
        self.confidence_text.setText(f"{confidence_percent}% confidence - {status}")

        # Update indicators
        self.indicators_list.clear()
        for indicator in result.indicators:
            item = QTreeWidgetItem([indicator, "Detection"])
            self.indicators_list.addTopLevelItem(item)

        if result.sample_structure:
            structure_item = QTreeWidgetItem(["Structure Analysis", ""])
            for key, value in result.sample_structure.items():
                child_item = QTreeWidgetItem([f"{key}: {value}", "Structure"])
                structure_item.addChild(child_item)
            self.indicators_list.addTopLevelItem(structure_item)
            structure_item.setExpanded(True)

        self.indicators_list.expandAll()


class DataPreviewWidget(QWidget):
    """Widget for previewing parsed data structure"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Control bar
        control_layout = QHBoxLayout()

        self.view_mode = QComboBox()
        self.view_mode.addItems(["Tree View", "Table View", "Raw JSON", "Summary"])
        self.view_mode.currentTextChanged.connect(self.on_view_mode_changed)
        control_layout.addWidget(QLabel("View Mode:"))
        control_layout.addWidget(self.view_mode)

        control_layout.addStretch()

        self.expand_all_btn = QPushButton("Expand All")
        self.collapse_all_btn = QPushButton("Collapse All")
        self.expand_all_btn.clicked.connect(self.expand_all)
        self.collapse_all_btn.clicked.connect(self.collapse_all)
        control_layout.addWidget(self.expand_all_btn)
        control_layout.addWidget(self.collapse_all_btn)

        layout.addLayout(control_layout)

        # Data display area
        self.data_display = QTabWidget()

        # Tree view tab
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Key", "Value", "Type"])
        self.data_display.addTab(self.tree_widget, "Tree View")

        # Table view tab
        self.table_widget = QTableWidget()
        self.data_display.addTab(self.table_widget, "Table View")

        # Raw JSON tab
        self.json_text = QTextEdit()
        self.json_text.setFont(QFont("Courier", 10))
        self.json_text.setReadOnly(True)
        self.data_display.addTab(self.json_text, "Raw JSON")

        # Summary tab
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.data_display.addTab(self.summary_text, "Summary")

        layout.addWidget(self.data_display)
        self.setLayout(layout)

    def update_data(self, result: ParseResult):
        """Update display with parse results"""
        if not result.is_successful or not result.data:
            self.clear_display()
            return

        # Update tree view
        self.populate_tree_view(result.data)

        # Update table view
        self.populate_table_view(result.data)

        # Update JSON view
        json_str = json.dumps(result.data, indent=2, ensure_ascii=False, default=str)
        self.json_text.setPlainText(json_str)

        # Update summary
        self.populate_summary(result)

    def populate_tree_view(self, data: Any, parent: Optional[QTreeWidgetItem] = None):
        """Populate tree view with data structure"""
        self.tree_widget.clear()

        def add_item(key: str, value: Any, parent: Optional[QTreeWidgetItem] = None):
            value_type = type(value).__name__

            if isinstance(value, dict):
                item = QTreeWidgetItem([key, f"{{}} ({len(value)} items)", "dict"])
                if parent:
                    parent.addChild(item)
                else:
                    self.tree_widget.addTopLevelItem(item)

                for k, v in value.items():
                    add_item(str(k), v, item)

            elif isinstance(value, list):
                item = QTreeWidgetItem([key, f"[] ({len(value)} items)", "list"])
                if parent:
                    parent.addChild(item)
                else:
                    self.tree_widget.addTopLevelItem(item)

                for i, v in enumerate(value):
                    add_item(f"[{i}]", v, item)

            else:
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."
                item = QTreeWidgetItem([key, value_str, value_type])
                if parent:
                    parent.addChild(item)
                else:
                    self.tree_widget.addTopLevelItem(item)

        if isinstance(data, dict):
            for key, value in data.items():
                add_item(str(key), value)
        elif isinstance(data, list):
            for i, value in enumerate(data):
                add_item(f"[{i}]", value)
        else:
            add_item("data", data)

    def populate_table_view(self, data: Any):
        """Populate table view for tabular data"""
        self.table_widget.clear()

        if isinstance(data, list) and data and isinstance(data[0], dict):
            # Tabular data
            headers = list(data[0].keys())
            self.table_widget.setRowCount(len(data))
            self.table_widget.setColumnCount(len(headers))
            self.table_widget.setHorizontalHeaderLabels(headers)

            for row, item in enumerate(data):
                for col, header in enumerate(headers):
                    value = str(item.get(header, ""))
                    self.table_widget.setItem(row, col, QTableWidgetItem(value))

        elif isinstance(data, dict):
            # Key-value pairs
            items = list(data.items())
            self.table_widget.setRowCount(len(items))
            self.table_widget.setColumnCount(2)
            self.table_widget.setHorizontalHeaderLabels(["Key", "Value"])

            for row, (key, value) in enumerate(items):
                self.table_widget.setItem(row, 0, QTableWidgetItem(str(key)))
                self.table_widget.setItem(row, 1, QTableWidgetItem(str(value)))
        else:
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)

    def populate_summary(self, result: ParseResult):
        """Populate summary view with parsing statistics"""
        summary = f"""
<h2>Parse Results Summary</h2>

<h3>Basic Information</h3>
<ul>
<li><b>Format:</b> {result.format_type.name}</li>
<li><b>Success:</b> {"✓ Yes" if result.is_successful else "✗ No"}</li>
<li><b>Confidence:</b> {result.confidence:.2f}</li>
<li><b>Parse Time:</b> {result.parsing_time:.4f}s</li>
</ul>

<h3>Data Structure</h3>
<ul>
"""

        if result.data:
            if isinstance(result.data, dict):
                summary += (
                    f"<li><b>Type:</b> Dictionary with {len(result.data)} keys</li>"
                )
                summary += "<li><b>Keys:</b> " + ", ".join(
                    list(result.data.keys())[:10]
                )
                if len(result.data) > 10:
                    summary += f" ... and {len(result.data) - 10} more"
                summary += "</li>"
            elif isinstance(result.data, list):
                summary += f"<li><b>Type:</b> Array with {len(result.data)} items</li>"
                if result.data:
                    summary += (
                        f"<li><b>Item Type:</b> {type(result.data[0]).__name__}</li>"
                    )
            else:
                summary += f"<li><b>Type:</b> {type(result.data).__name__}</li>"
                summary += f"<li><b>Value:</b> {str(result.data)[:100]}</li>"

        summary += "</ul>"

        # Metadata section
        if result.metadata:
            summary += "<h3>Parsing Metadata</h3><ul>"

            if "structure_types" in result.metadata:
                types = result.metadata["structure_types"]
                if types:
                    summary += f"<li><b>Structure Types:</b> {', '.join(types)}</li>"

            if "array_stats" in result.metadata:
                arrays = result.metadata["array_stats"]
                if arrays:
                    total_items = sum(arrays.values())
                    summary += f"<li><b>Arrays Found:</b> {len(arrays)} arrays with {total_items} total items</li>"

            if "line_count" in result.metadata:
                summary += (
                    f"<li><b>Lines Processed:</b> {result.metadata['line_count']}</li>"
                )

            summary += "</ul>"

        # Warnings and errors
        if result.warnings:
            summary += f"<h3>⚠️ Warnings ({len(result.warnings)})</h3><ul>"
            for warning in result.warnings:
                summary += f"<li>{warning}</li>"
            summary += "</ul>"

        if result.errors:
            summary += f"<h3>❌ Errors ({len(result.errors)})</h3><ul>"
            for error in result.errors:
                summary += f"<li>{error}</li>"
            summary += "</ul>"

        self.summary_text.setHtml(summary)

    def clear_display(self):
        """Clear all display widgets"""
        self.tree_widget.clear()
        self.table_widget.clear()
        self.json_text.clear()
        self.summary_text.clear()

    def on_view_mode_changed(self, mode: str):
        """Handle view mode changes"""
        mode_mapping = {"Tree View": 0, "Table View": 1, "Raw JSON": 2, "Summary": 3}
        self.data_display.setCurrentIndex(mode_mapping.get(mode, 0))

    def expand_all(self):
        """Expand all tree items"""
        self.tree_widget.expandAll()

    def collapse_all(self):
        """Collapse all tree items"""
        self.tree_widget.collapseAll()


class DynamicParserWidget(QWidget):
    """Main GUI widget for the dynamic anything parser"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_content = ""
        self.current_filename = None
        self.current_result = None

        # Workers
        self.detection_worker = None
        self.parse_worker = None

        self.setup_ui()
        self.setup_connections()

        # Enable drag and drop
        self.setAcceptDrops(True)

    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QVBoxLayout()

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Dynamic Anything Parser")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2196F3;
                padding: 10px;
            }
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Load file button
        self.load_file_btn = QPushButton("📁 Load File")
        self.load_file_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 10px 20px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        header_layout.addWidget(self.load_file_btn)

        main_layout.addLayout(header_layout)

        # Main content area
        content_splitter = QSplitter(Qt.Horizontal)

        # Left panel - Input and controls
        left_panel = QWidget()
        left_layout = QVBoxLayout()

        # Input area
        input_group = QGroupBox("Input Content")
        input_layout = QVBoxLayout()

        # File info
        self.file_info = QLabel(
            "No file loaded - Drag & drop a file or paste content below"
        )
        self.file_info.setStyleSheet(
            "padding: 5px; background-color: #f0f0f0; border-radius: 3px;"
        )
        input_layout.addWidget(self.file_info)

        # Content text area
        self.content_text = QTextEdit()
        self.content_text.setPlaceholderText("""
Paste your data here or drag & drop a file...

Supported formats:
• TOON (Token-Optimized Object Notation)
• JSON (JavaScript Object Notation)
• CSV (Comma-Separated Values)
• YAML (YAML Ain't Markup Language)
• XML (eXtensible Markup Language)
• TSV, pipe-delimited, key-value, INI, properties
        """)
        self.content_text.setFont(QFont("Courier", 10))
        self.content_text.setMaximumHeight(200)
        input_layout.addWidget(self.content_text)

        input_group.setLayout(input_layout)
        left_layout.addWidget(input_group)

        # Controls
        controls_group = QGroupBox("Parser Settings")
        controls_layout = QGridLayout()

        # Format hint
        controls_layout.addWidget(QLabel("Format Hint:"), 0, 0)
        self.format_hint = QComboBox()
        self.format_hint.addItems(
            ["Auto-detect", "TOON", "JSON", "CSV", "YAML", "XML", "TSV"]
        )
        controls_layout.addWidget(self.format_hint, 0, 1)

        # Parser options
        self.strict_mode = QCheckBox("Strict parsing (fail on errors)")
        controls_layout.addWidget(self.strict_mode, 1, 0, 1, 2)

        self.enable_recovery = QCheckBox("Enable error recovery")
        self.enable_recovery.setChecked(True)
        controls_layout.addWidget(self.enable_recovery, 2, 0, 1, 2)

        # Delimiter for tabular formats
        controls_layout.addWidget(QLabel("Delimiter:"), 3, 0)
        self.delimiter = QComboBox()
        self.delimiter.addItems(["Comma (,)", "Tab", "Pipe (|)", "Semicolon (;)"])
        controls_layout.addWidget(self.delimiter, 3, 1)

        controls_group.setLayout(controls_layout)
        left_layout.addWidget(controls_group)

        # Action buttons
        actions_layout = QHBoxLayout()

        self.detect_btn = QPushButton("🔍 Detect Format")
        self.parse_btn = QPushButton("🚀 Parse Content")
        self.convert_btn = QPushButton("🔄 Convert Format")

        self.detect_btn.setStyleSheet(self.get_button_style("#2196F3"))
        self.parse_btn.setStyleSheet(self.get_button_style("#4CAF50"))
        self.convert_btn.setStyleSheet(self.get_button_style("#FF9800"))

        actions_layout.addWidget(self.detect_btn)
        actions_layout.addWidget(self.parse_btn)
        actions_layout.addWidget(self.convert_btn)

        left_layout.addLayout(actions_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        left_panel.setLayout(left_layout)
        content_splitter.addWidget(left_panel)

        # Right panel - Results
        right_panel = QWidget()
        right_layout = QVBoxLayout()

        # Results tabs
        self.results_tabs = QTabWidget()

        # Format detection tab
        self.format_viz = FormatVisualizationWidget()
        self.results_tabs.addTab(self.format_viz, "🔍 Format Detection")

        # Data preview tab
        self.data_preview = DataPreviewWidget()
        self.results_tabs.addTab(self.data_preview, "📊 Data Preview")

        # Conversion tab
        self.setup_conversion_tab()

        right_layout.addWidget(self.results_tabs)
        right_panel.setLayout(right_layout)
        content_splitter.addWidget(right_panel)

        # Set splitter proportions
        content_splitter.setSizes([400, 600])
        main_layout.addWidget(content_splitter)

        # Status bar
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)

    def setup_conversion_tab(self):
        """Setup the format conversion tab"""
        conversion_widget = QWidget()
        conversion_layout = QVBoxLayout()

        # Conversion controls
        controls_group = QGroupBox("Format Conversion")
        controls_layout = QGridLayout()

        controls_layout.addWidget(QLabel("Convert to:"), 0, 0)
        self.target_format = QComboBox()
        self.target_format.addItems(["TOON", "JSON", "CSV", "YAML"])
        controls_layout.addWidget(self.target_format, 0, 1)

        # Conversion options
        self.indent_size = QSpinBox()
        self.indent_size.setRange(1, 8)
        self.indent_size.setValue(2)
        controls_layout.addWidget(QLabel("Indent Size:"), 1, 0)
        controls_layout.addWidget(self.indent_size, 1, 1)

        self.length_markers = QCheckBox("Use length markers (TOON)")
        controls_layout.addWidget(self.length_markers, 2, 0, 1, 2)

        controls_group.setLayout(controls_layout)
        conversion_layout.addWidget(controls_group)

        # Convert button
        self.do_convert_btn = QPushButton("🔄 Convert Now")
        self.do_convert_btn.setStyleSheet(self.get_button_style("#FF9800"))
        conversion_layout.addWidget(self.do_convert_btn)

        # Results area
        results_group = QGroupBox("Conversion Results")
        results_layout = QVBoxLayout()

        # Statistics
        self.conversion_stats = QLabel("No conversion performed yet")
        results_layout.addWidget(self.conversion_stats)

        # Output text
        self.conversion_output = QTextEdit()
        self.conversion_output.setFont(QFont("Courier", 10))
        self.conversion_output.setReadOnly(True)
        results_layout.addWidget(self.conversion_output)

        # Export button
        self.export_btn = QPushButton("💾 Export Converted Data")
        self.export_btn.setStyleSheet(self.get_button_style("#4CAF50"))
        results_layout.addWidget(self.export_btn)

        results_group.setLayout(results_layout)
        conversion_layout.addWidget(results_group)

        conversion_widget.setLayout(conversion_layout)
        self.results_tabs.addTab(conversion_widget, "🔄 Format Conversion")

    def setup_connections(self):
        """Setup signal connections"""
        self.load_file_btn.clicked.connect(self.load_file)
        self.detect_btn.clicked.connect(self.detect_format)
        self.parse_btn.clicked.connect(self.parse_content)
        self.convert_btn.clicked.connect(self.show_conversion_tab)
        self.do_convert_btn.clicked.connect(self.convert_format)
        self.export_btn.clicked.connect(self.export_converted)

        self.content_text.textChanged.connect(self.on_content_changed)

    def get_button_style(self, color: str) -> str:
        """Get button stylesheet with given color"""
        return f"""
            QPushButton {{
                font-size: 12px;
                padding: 8px 16px;
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}
        """

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle drop events"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.load_file_path(files[0])

    def load_file(self):
        """Load file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select file to parse",
            "",
            "All files (*.*);;"
            "TOON files (*.toon);;"
            "JSON files (*.json);;"
            "CSV files (*.csv);;"
            "YAML files (*.yaml *.yml);;"
            "XML files (*.xml);;"
            "Text files (*.txt)",
        )

        if file_path:
            self.load_file_path(file_path)

    def load_file_path(self, file_path: str):
        """Load file from path"""
        try:
            path = Path(file_path)
            self.current_filename = path.name

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self.content_text.setPlainText(content)
            self.file_info.setText(
                f"📁 {self.current_filename} ({len(content)} characters)"
            )
            self.file_info.setStyleSheet(
                "padding: 5px; background-color: #e8f5e8; border-radius: 3px; color: #2e7d32;"
            )

            # Auto-detect format
            QTimer.singleShot(500, self.detect_format)

        except Exception as e:
            QMessageBox.critical(
                self, "Error Loading File", f"Could not load file: {str(e)}"
            )

    def on_content_changed(self):
        """Handle content text changes"""
        self.current_content = self.content_text.toPlainText()
        if not self.current_filename and self.current_content:
            self.file_info.setText(
                f"📝 Manual input ({len(self.current_content)} characters)"
            )
            self.file_info.setStyleSheet(
                "padding: 5px; background-color: #fff3e0; border-radius: 3px; color: #e65100;"
            )

    def detect_format(self):
        """Detect format of current content"""
        if not self.current_content:
            QMessageBox.information(
                self, "No Content", "Please load a file or enter content first."
            )
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.detect_btn.setEnabled(False)
        self.status_bar.showMessage("Detecting format...")

        # Start detection worker
        self.detection_worker = FormatDetectionWorker(
            self.current_content, self.current_filename
        )
        self.detection_worker.detection_complete.connect(self.on_detection_complete)
        self.detection_worker.error_occurred.connect(self.on_detection_error)
        self.detection_worker.start()

    def on_detection_complete(self, result: FormatDetectionResult):
        """Handle detection completion"""
        self.progress_bar.setVisible(False)
        self.detect_btn.setEnabled(True)
        self.status_bar.showMessage(
            f"Format detected: {result.format_type.name} (confidence: {result.confidence:.2f})"
        )

        # Update visualization
        self.format_viz.update_detection_result(result)
        self.results_tabs.setCurrentIndex(0)  # Show detection tab

        # Update format hint
        format_name = result.format_type.name
        if format_name in ["TOON", "JSON", "CSV", "YAML", "XML", "TSV"]:
            index = self.format_hint.findText(format_name)
            if index >= 0:
                self.format_hint.setCurrentIndex(index)

    def on_detection_error(self, error: str):
        """Handle detection error"""
        self.progress_bar.setVisible(False)
        self.detect_btn.setEnabled(True)
        self.status_bar.showMessage("Detection failed")
        QMessageBox.critical(
            self, "Detection Error", f"Format detection failed: {error}"
        )

    def parse_content(self):
        """Parse current content"""
        if not self.current_content:
            QMessageBox.information(
                self, "No Content", "Please load a file or enter content first."
            )
            return

        # Get parsing options
        format_hint = None
        if self.format_hint.currentText() != "Auto-detect":
            try:
                format_hint = FormatType[self.format_hint.currentText()]
            except KeyError:
                pass

        delimiter_map = {
            "Comma (,)": ",",
            "Tab": "\t",
            "Pipe (|)": "|",
            "Semicolon (;)": ";",
        }
        delimiter = delimiter_map.get(self.delimiter.currentText(), ",")

        options = {
            "strict": self.strict_mode.isChecked(),
            "recovery": self.enable_recovery.isChecked(),
            "delimiter": delimiter,
        }

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.parse_btn.setEnabled(False)
        self.status_bar.showMessage("Parsing content...")

        # Start parse worker
        self.parse_worker = ParseWorker(
            self.current_content, self.current_filename, format_hint, **options
        )
        self.parse_worker.parse_complete.connect(self.on_parse_complete)
        self.parse_worker.error_occurred.connect(self.on_parse_error)
        self.parse_worker.progress_update.connect(self.progress_bar.setValue)
        self.parse_worker.start()

    def on_parse_complete(self, result: ParseResult):
        """Handle parse completion"""
        self.current_result = result
        self.progress_bar.setVisible(False)
        self.parse_btn.setEnabled(True)

        if result.is_successful:
            self.status_bar.showMessage(
                f"Parse successful: {result.format_type.name} ({result.parsing_time:.4f}s)"
            )
            # Update data preview
            self.data_preview.update_data(result)
            self.results_tabs.setCurrentIndex(1)  # Show data preview tab
        else:
            self.status_bar.showMessage("Parse failed")
            error_msg = (
                "\n".join(result.errors) if result.errors else "Unknown parsing error"
            )
            QMessageBox.warning(self, "Parse Error", f"Parsing failed:\n{error_msg}")

    def on_parse_error(self, error: str):
        """Handle parse error"""
        self.progress_bar.setVisible(False)
        self.parse_btn.setEnabled(True)
        self.status_bar.showMessage("Parse failed")
        QMessageBox.critical(self, "Parse Error", f"Parsing failed: {error}")

    def show_conversion_tab(self):
        """Show the conversion tab"""
        if not self.current_result or not self.current_result.is_successful:
            QMessageBox.information(
                self,
                "No Parsed Data",
                "Please parse content successfully first before converting.",
            )
            return

        self.results_tabs.setCurrentIndex(2)  # Show conversion tab

    def convert_format(self):
        """Convert current data to target format"""
        if not self.current_result or not self.current_result.is_successful:
            QMessageBox.information(
                self,
                "No Parsed Data",
                "Please parse content successfully first before converting.",
            )
            return

        try:
            from varchiver.utils.format_converter import FormatConverter

            converter = FormatConverter()
            target = self.target_format.currentText().lower()

            # Get conversion options
            options = {
                "indent": self.indent_size.value(),
                "delimiter": ",",  # Could be made configurable
                "length_marker": self.length_markers.isChecked(),
            }

            # Perform conversion
            if target == "toon":
                converted = converter.json_to_toon(self.current_result.data, **options)
            elif target == "json":
                converted = json.dumps(
                    self.current_result.data,
                    indent=options["indent"],
                    ensure_ascii=False,
                )
            elif target == "csv":
                converted = converter.json_to_csv(self.current_result.data)
            else:
                QMessageBox.warning(
                    self,
                    "Unsupported Conversion",
                    f"Conversion to {target} not implemented yet.",
                )
                return

            # Show results
            self.conversion_output.setPlainText(converted)

            # Calculate statistics
            original_size = len(self.current_content)
            converted_size = len(converted)
            reduction = (
                ((original_size - converted_size) / original_size * 100)
                if original_size > 0
                else 0
            )

            stats_text = f"""
            <b>Conversion Statistics:</b><br>
            Original format: {self.current_result.format_type.name}<br>
            Target format: {target.upper()}<br>
            Original size: {original_size:,} characters<br>
            Converted size: {converted_size:,} characters<br>
            Size change: {reduction:+.1f}%<br>
            """

            self.conversion_stats.setText(stats_text)
            self.export_btn.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(
                self, "Conversion Error", f"Conversion failed: {str(e)}"
            )

    def export_converted(self):
        """Export converted content to file"""
        if not self.conversion_output.toPlainText():
            return

        target_format = self.target_format.currentText().lower()
        ext_map = {"toon": ".toon", "json": ".json", "csv": ".csv", "yaml": ".yaml"}
        default_ext = ext_map.get(target_format, ".txt")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Converted Data",
            f"converted_data{default_ext}",
            f"{target_format.upper()} files (*{default_ext});;All files (*.*)",
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.conversion_output.toPlainText())
                QMessageBox.information(
                    self, "Export Successful", f"Data exported to: {file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Export failed: {str(e)}")


class DynamicParserMainWindow(QWidget):
    """Main window for the dynamic parser application"""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup main window UI"""
        self.setWindowTitle("VArchiver - Dynamic Anything Parser")
        self.setGeometry(100, 100, 1400, 800)

        # Apply application stylesheet
        self.setStyleSheet("""
            QWidget {
                background-color: #fafafa;
                color: #333;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 5px;
                margin: 10px 0;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 12px;
                margin-right: 2px;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
        """)

        layout = QVBoxLayout()

        # Add the main parser widget
        self.parser_widget = DynamicParserWidget()
        layout.addWidget(self.parser_widget)

        self.setLayout(layout)


def main():
    """Main application entry point"""
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    app.setApplicationName("VArchiver Dynamic Parser")
    app.setApplicationVersion("1.0.0")

    # Create and show main window
    window = DynamicParserMainWindow()
    window.show()

    # Show welcome message
    QMessageBox.information(
        window,
        "Welcome to Dynamic Parser",
        """
        <h2>Welcome to VArchiver Dynamic Parser!</h2>

        <p><b>Features:</b></p>
        <ul>
        <li>🎯 Automatic format detection for 10+ formats</li>
        <li>🚀 Full TOON parsing with advanced features</li>
        <li>📊 Interactive data preview and analysis</li>
        <li>🔄 Format conversion capabilities</li>
        <li>📁 Drag & drop file loading</li>
        </ul>

        <p><b>Getting Started:</b></p>
        <ol>
        <li>Load a file using the "Load File" button or drag & drop</li>
        <li>Or paste content directly into the text area</li>
        <li>Click "Detect Format" to analyze the data</li>
        <li>Click "Parse Content" to extract structured data</li>
        <li>Use "Convert Format" to transform between formats</li>
        </ol>

        <p><i>Supports TOON, JSON, CSV, YAML, XML, TSV, and more!</i></p>
        """,
    )

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
