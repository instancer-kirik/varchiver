"""
VArchiver Dynamic Parser Integration Module
Provides integration hooks for the dynamic parser within VArchiver's main interface

This module allows the dynamic parser to be seamlessly integrated into VArchiver's
existing workflow, providing menu items, toolbar buttons, and context menu options
for accessing the parser functionality.

Author: VArchiver Team
Version: 1.0.0
"""

import sys
from pathlib import Path
from typing import Optional, Callable

# Add paths for VArchiver imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from PyQt5.QtWidgets import (
        QAction,
        QMenu,
        QMenuBar,
        QToolBar,
        QMessageBox,
        QDialog,
        QVBoxLayout,
        QPushButton,
        QHBoxLayout,
        QLabel,
        QWidget,
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QIcon, QKeySequence
except ImportError:
    print("PyQt5 not available. Integration features disabled.")
    QAction = QMenu = QMenuBar = QToolBar = QWidget = object
    pyqtSignal = lambda: None


class ParserIntegrationManager:
    """Manages integration of dynamic parser with VArchiver main interface"""

    def __init__(self, main_window=None):
        self.main_window = main_window
        self.parser_window = None
        self.parser_actions = {}

    def integrate_with_menu(self, menu_bar: QMenuBar):
        """Add parser menu items to main menu bar"""
        try:
            # Find or create Tools menu
            tools_menu = None
            for action in menu_bar.actions():
                if action.menu() and action.text() == "&Tools":
                    tools_menu = action.menu()
                    break

            if not tools_menu:
                tools_menu = menu_bar.addMenu("&Tools")

            # Add parser submenu
            parser_menu = tools_menu.addMenu("📋 Dynamic Parser")

            # Launch Parser action
            launch_action = QAction("🚀 Launch Parser", self.main_window)
            launch_action.setShortcut(QKeySequence("Ctrl+Shift+P"))
            launch_action.setStatusTip("Launch Dynamic Anything Parser")
            launch_action.triggered.connect(self.launch_parser_window)
            parser_menu.addAction(launch_action)
            self.parser_actions["launch"] = launch_action

            # Quick Parse Current File
            parse_current_action = QAction("⚡ Parse Current File", self.main_window)
            parse_current_action.setShortcut(QKeySequence("Ctrl+Alt+P"))
            parse_current_action.setStatusTip("Parse currently selected file")
            parse_current_action.triggered.connect(self.parse_current_file)
            parser_menu.addAction(parse_current_action)
            self.parser_actions["parse_current"] = parse_current_action

            parser_menu.addSeparator()

            # Format Detection
            detect_action = QAction("🔍 Detect Format", self.main_window)
            detect_action.setStatusTip("Detect format of current file")
            detect_action.triggered.connect(self.detect_current_format)
            parser_menu.addAction(detect_action)
            self.parser_actions["detect"] = detect_action

            # Batch Processing
            batch_action = QAction("📁 Batch Process", self.main_window)
            batch_action.setStatusTip("Process multiple files")
            batch_action.triggered.connect(self.launch_batch_processor)
            parser_menu.addAction(batch_action)
            self.parser_actions["batch"] = batch_action

            return True

        except Exception as e:
            print(f"Error integrating with menu: {e}")
            return False

    def integrate_with_toolbar(self, toolbar: QToolBar):
        """Add parser buttons to main toolbar"""
        try:
            # Add separator if toolbar has items
            if toolbar.actions():
                toolbar.addSeparator()

            # Quick parse button
            parse_action = QAction("🚀 Parse", self.main_window)
            parse_action.setToolTip("Launch Dynamic Parser (Ctrl+Shift+P)")
            parse_action.triggered.connect(self.launch_parser_window)
            toolbar.addAction(parse_action)

            # Format detect button
            detect_action = QAction("🔍 Detect", self.main_window)
            detect_action.setToolTip("Detect file format")
            detect_action.triggered.connect(self.detect_current_format)
            toolbar.addAction(detect_action)

            return True

        except Exception as e:
            print(f"Error integrating with toolbar: {e}")
            return False

    def add_context_menu_items(
        self, context_menu: QMenu, file_path: Optional[str] = None
    ):
        """Add parser options to context menu"""
        try:
            context_menu.addSeparator()

            # Parse this file
            if file_path:
                parse_file_action = QAction(
                    f"🚀 Parse with Dynamic Parser", context_menu
                )
                parse_file_action.triggered.connect(
                    lambda: self.launch_parser_with_file(file_path)
                )
                context_menu.addAction(parse_file_action)

                # Detect format
                detect_action = QAction("🔍 Detect Format", context_menu)
                detect_action.triggered.connect(
                    lambda: self.detect_file_format(file_path)
                )
                context_menu.addAction(detect_action)

            return True

        except Exception as e:
            print(f"Error adding context menu items: {e}")
            return False

    def launch_parser_window(self):
        """Launch the dynamic parser GUI window"""
        try:
            # Import here to avoid circular imports and handle missing GUI
            from .dynamic_parser_widget import DynamicParserMainWindow

            if self.parser_window is None:
                self.parser_window = DynamicParserMainWindow()

            self.parser_window.show()
            self.parser_window.raise_()
            self.parser_window.activateWindow()

        except ImportError as e:
            QMessageBox.critical(
                self.main_window,
                "Parser Not Available",
                f"Dynamic Parser GUI not available: {e}\n\nPlease check your installation.",
            )
        except Exception as e:
            QMessageBox.critical(
                self.main_window, "Launch Error", f"Could not launch parser: {e}"
            )

    def launch_parser_with_file(self, file_path: str):
        """Launch parser with specific file loaded"""
        try:
            from .dynamic_parser_widget import DynamicParserMainWindow

            if self.parser_window is None:
                self.parser_window = DynamicParserMainWindow()

            # Load the file
            self.parser_window.parser_widget.load_file_path(file_path)
            self.parser_window.show()
            self.parser_window.raise_()
            self.parser_window.activateWindow()

        except ImportError as e:
            QMessageBox.critical(
                self.main_window,
                "Parser Not Available",
                f"Dynamic Parser GUI not available: {e}",
            )
        except Exception as e:
            QMessageBox.critical(
                self.main_window,
                "Launch Error",
                f"Could not launch parser with file: {e}",
            )

    def parse_current_file(self):
        """Parse the currently selected/active file"""
        try:
            # Try to get current file from main window
            current_file = self.get_current_file()
            if current_file:
                self.launch_parser_with_file(current_file)
            else:
                QMessageBox.information(
                    self.main_window,
                    "No File Selected",
                    "Please select a file to parse first.",
                )
        except Exception as e:
            QMessageBox.critical(
                self.main_window, "Parse Error", f"Could not parse current file: {e}"
            )

    def detect_current_format(self):
        """Detect format of currently selected file"""
        try:
            current_file = self.get_current_file()
            if current_file:
                self.detect_file_format(current_file)
            else:
                QMessageBox.information(
                    self.main_window,
                    "No File Selected",
                    "Please select a file to analyze first.",
                )
        except Exception as e:
            QMessageBox.critical(
                self.main_window, "Detection Error", f"Could not detect format: {e}"
            )

    def detect_file_format(self, file_path: str):
        """Detect and show format of specified file"""
        try:
            from varchiver.utils.dynamic_parser import detect_format

            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Detect format
            result = detect_format(content, Path(file_path).name)

            # Show result dialog
            self.show_detection_result(file_path, result)

        except ImportError:
            QMessageBox.critical(
                self.main_window,
                "Parser Not Available",
                "Dynamic Parser modules not available. Please check your installation.",
            )
        except Exception as e:
            QMessageBox.critical(
                self.main_window,
                "Detection Error",
                f"Could not detect format of {file_path}:\n{e}",
            )

    def show_detection_result(self, file_path: str, detection_result):
        """Show format detection results in a dialog"""
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("Format Detection Results")
        dialog.setModal(True)
        dialog.resize(400, 300)

        layout = QVBoxLayout()

        # File info
        file_label = QLabel(f"<b>File:</b> {Path(file_path).name}")
        layout.addWidget(file_label)

        # Format result
        format_label = QLabel(
            f"<b>Detected Format:</b> {detection_result.format_type.name}"
        )
        layout.addWidget(format_label)

        # Confidence
        confidence = detection_result.confidence
        confidence_color = (
            "green" if confidence >= 0.8 else "orange" if confidence >= 0.5 else "red"
        )
        confidence_label = QLabel(
            f"<b>Confidence:</b> <span style='color: {confidence_color}'>{confidence:.2f} ({confidence * 100:.0f}%)</span>"
        )
        layout.addWidget(confidence_label)

        # Indicators
        if detection_result.indicators:
            indicators_label = QLabel("<b>Detection Indicators:</b>")
            layout.addWidget(indicators_label)

            indicators_text = "\n".join(
                f"• {indicator}" for indicator in detection_result.indicators[:5]
            )
            indicators_display = QLabel(indicators_text)
            indicators_display.setStyleSheet("margin-left: 20px; color: #666;")
            layout.addWidget(indicators_display)

        # Buttons
        button_layout = QHBoxLayout()

        parse_button = QPushButton("🚀 Parse This File")
        parse_button.clicked.connect(lambda: self.launch_parser_with_file(file_path))
        parse_button.clicked.connect(dialog.accept)
        button_layout.addWidget(parse_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec_()

    def launch_batch_processor(self):
        """Launch batch processing interface"""
        try:
            from PyQt5.QtWidgets import QFileDialog

            # Get directory to process
            directory = QFileDialog.getExistingDirectory(
                self.main_window,
                "Select Directory for Batch Processing",
                str(Path.home()),
            )

            if directory:
                # Launch parser and switch to batch mode (if supported)
                self.launch_parser_window()
                QMessageBox.information(
                    self.parser_window,
                    "Batch Processing",
                    f"Load files from directory: {directory}\n\n"
                    "Use the parser's batch processing features to analyze multiple files.",
                )

        except Exception as e:
            QMessageBox.critical(
                self.main_window,
                "Batch Processing Error",
                f"Could not start batch processing: {e}",
            )

    def get_current_file(self) -> Optional[str]:
        """Get currently selected/active file from main window"""
        try:
            # This is a placeholder - actual implementation depends on VArchiver's structure
            if hasattr(self.main_window, "get_current_file"):
                return self.main_window.get_current_file()
            elif hasattr(self.main_window, "current_file"):
                return self.main_window.current_file
            elif (
                hasattr(self.main_window, "selected_files")
                and self.main_window.selected_files
            ):
                return self.main_window.selected_files[0]
            else:
                return None
        except:
            return None


class ParserStatusWidget(QWidget):
    """Status widget showing parser integration status"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.check_parser_status()

    def setup_ui(self):
        layout = QHBoxLayout()

        self.status_label = QLabel("Parser: Checking...")
        self.status_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def check_parser_status(self):
        """Check if parser components are available"""
        try:
            from varchiver.utils.dynamic_parser import DynamicAnythingParser

            self.status_label.setText("Parser: ✅ Available")
            self.status_label.setStyleSheet("color: green; font-size: 10px;")
        except ImportError:
            self.status_label.setText("Parser: ❌ Not Available")
            self.status_label.setStyleSheet("color: red; font-size: 10px;")


def integrate_parser_with_varchiver(main_window):
    """Main integration function to add parser support to VArchiver"""
    try:
        manager = ParserIntegrationManager(main_window)

        # Integrate with menu bar
        if hasattr(main_window, "menuBar") and main_window.menuBar():
            manager.integrate_with_menu(main_window.menuBar())

        # Integrate with toolbar
        if hasattr(main_window, "toolBar") and main_window.toolBar():
            manager.integrate_with_toolbar(main_window.toolBar())

        # Add status widget to status bar
        if hasattr(main_window, "statusBar") and main_window.statusBar():
            status_widget = ParserStatusWidget()
            main_window.statusBar().addPermanentWidget(status_widget)

        print("Dynamic Parser integrated successfully with VArchiver")
        return manager

    except Exception as e:
        print(f"Error integrating Dynamic Parser with VArchiver: {e}")
        return None


# Convenience function for easy integration
def setup_parser_integration(main_window):
    """Setup parser integration - call this from VArchiver main window initialization"""
    return integrate_parser_with_varchiver(main_window)
