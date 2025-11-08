#!/usr/bin/env python3
"""
Dynamic Anything Parser - GUI Launcher
Standalone launcher for the dynamic parser GUI with VArchiver integration

Usage:
    python launch_dynamic_parser.py
    python launch_dynamic_parser.py --file data.toon
    python launch_dynamic_parser.py --demo

Features:
- Standalone GUI application
- Integration with VArchiver theming
- Command line file loading
- Demo mode with sample data
- Error handling and fallback modes

Author: VArchiver Team
Version: 1.0.0
"""

import sys
import argparse
from pathlib import Path
import traceback

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "varchiver"))


def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []

    # Check PyQt5
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        missing_deps.append("PyQt5")

    # Check YAML (optional but recommended)
    try:
        import yaml
    except ImportError:
        print("Warning: PyYAML not installed. YAML format support will be limited.")

    # Check dynamic parser
    try:
        from varchiver.utils.dynamic_parser import DynamicAnythingParser
    except ImportError:
        missing_deps.append("varchiver.utils.dynamic_parser")

    if missing_deps:
        print("Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nInstall missing dependencies:")
        if "PyQt5" in missing_deps:
            print("  pip install PyQt5")
        if "PyYAML" not in sys.modules:
            print("  pip install PyYAML")
        return False

    return True


def create_demo_data():
    """Create demo data files for testing"""
    demo_dir = Path("demo_data")
    demo_dir.mkdir(exist_ok=True)

    # Create sample TOON file
    toon_content = """# VArchiver Inventory Demo Data
tech_components[3]{id,name,tier,rarity}:
  resonator_t1,Basic Resonator,Tier 1,common
  magitek_core_t2,Advanced Magitek Core,Tier 2,rare
  crystal_t3,Prismatic Crystal,Tier 3,legendary

player_stats:
  name: Demo Player
  level: 25
  gold: 1500
  location: Tutorial Zone

settings:
  auto_save: true
  difficulty: normal
  sound_enabled: true
"""

    # Create sample JSON file
    json_content = """{
  "inventory": [
    {"item": "Health Potion", "quantity": 5, "value": 25},
    {"item": "Mana Elixir", "quantity": 3, "value": 50},
    {"item": "Magic Sword", "quantity": 1, "value": 500}
  ],
  "player": {
    "name": "Demo Player",
    "class": "Warrior",
    "level": 25,
    "experience": 12500
  },
  "metadata": {
    "version": "1.0",
    "created": "2025-01-27T15:00:00Z"
  }
}"""

    # Create sample CSV file
    csv_content = """id,name,category,price,stock
1,Widget Pro,Tools,19.99,150
2,Super Gadget,Electronics,89.99,45
3,Mega Tool,Hardware,149.99,23
4,Basic Kit,Starter,9.99,500
5,Premium Set,Professional,299.99,12
"""

    # Write demo files
    demo_files = [
        ("inventory.toon", toon_content),
        ("player_data.json", json_content),
        ("products.csv", csv_content),
    ]

    created_files = []
    for filename, content in demo_files:
        file_path = demo_dir / filename
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            created_files.append(str(file_path))
        except Exception as e:
            print(f"Warning: Could not create demo file {filename}: {e}")

    return created_files


def setup_application():
    """Setup the PyQt application"""
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QIcon

    app = QApplication(sys.argv)
    app.setApplicationName("VArchiver Dynamic Parser")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VArchiver")
    app.setOrganizationDomain("varchiver.org")

    # Set application icon if available
    icon_path = Path("varchiver.svg")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Apply VArchiver theme if available
    try:
        from varchiver.utils.theme_manager import ThemeManager

        theme_manager = ThemeManager()
        theme_manager.apply_theme(app)
    except ImportError:
        # Use default theme
        app.setStyleSheet("""
            QApplication {
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 9pt;
            }
        """)

    return app


def show_error_dialog(title, message, details=None):
    """Show error dialog with details"""
    from PyQt5.QtWidgets import QMessageBox

    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)

    if details:
        msg_box.setDetailedText(details)

    msg_box.exec_()


def launch_gui(initial_file=None, demo_mode=False):
    """Launch the GUI application"""
    try:
        # Check dependencies first
        if not check_dependencies():
            return False

        # Setup PyQt application
        app = setup_application()

        # Import GUI components
        try:
            from varchiver.widgets.dynamic_parser_widget import DynamicParserMainWindow
        except ImportError as e:
            print(f"Error importing GUI widget: {e}")
            print("Trying alternative import path...")
            try:
                sys.path.insert(0, str(Path(__file__).parent / "varchiver" / "widgets"))
                from dynamic_parser_widget import DynamicParserMainWindow
            except ImportError as e2:
                show_error_dialog(
                    "Import Error",
                    "Could not import Dynamic Parser GUI components.",
                    f"Primary error: {e}\nSecondary error: {e2}",
                )
                return False

        # Create main window
        window = DynamicParserMainWindow()

        # Handle demo mode
        if demo_mode:
            print("Creating demo data...")
            demo_files = create_demo_data()
            if demo_files:
                print(f"Demo files created: {demo_files}")
                # Load first demo file
                if demo_files:
                    window.parser_widget.load_file_path(demo_files[0])

        # Handle initial file
        if initial_file:
            file_path = Path(initial_file)
            if file_path.exists():
                window.parser_widget.load_file_path(str(file_path))
            else:
                from PyQt5.QtWidgets import QMessageBox

                QMessageBox.warning(
                    window, "File Not Found", f"Could not find file: {initial_file}"
                )

        # Show window
        window.show()

        # Show welcome message for first-time users
        settings_file = Path.home() / ".varchiver" / "dynamic_parser_welcomed"
        if not settings_file.exists():
            show_welcome_message(window)
            # Create settings directory and file
            settings_file.parent.mkdir(exist_ok=True)
            settings_file.touch()

        # Run application
        return app.exec_() == 0

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error launching GUI: {e}")
        print(error_details)

        try:
            show_error_dialog(
                "Launch Error",
                f"Failed to launch Dynamic Parser GUI: {str(e)}",
                error_details,
            )
        except:
            print("Could not show error dialog. Printing to console.")

        return False


def show_welcome_message(parent_window):
    """Show welcome message for new users"""
    from PyQt5.QtWidgets import QMessageBox

    QMessageBox.information(
        parent_window,
        "Welcome to Dynamic Parser",
        """
        <h2>🚀 VArchiver Dynamic Parser</h2>

        <p><b>What is this?</b><br>
        A smart data parser that automatically detects and processes multiple file formats
        including TOON, JSON, CSV, YAML, XML, and more!</p>

        <p><b>Key Features:</b></p>
        <ul>
        <li>🎯 Automatic format detection</li>
        <li>📊 Interactive data visualization</li>
        <li>🔄 Format conversion tools</li>
        <li>📁 Drag & drop file loading</li>
        <li>⚡ High performance parsing</li>
        </ul>

        <p><b>Quick Start:</b></p>
        <ol>
        <li>Click "Load File" or drag a file onto the window</li>
        <li>Click "Detect Format" to analyze your data</li>
        <li>Click "Parse Content" to see structured results</li>
        <li>Use the conversion tab to transform formats</li>
        </ol>

        <p><i>Tip: Try the demo mode (--demo flag) to explore with sample data!</i></p>
        """,
    )


def launch_fallback_cli():
    """Launch fallback CLI mode if GUI fails"""
    print("\n" + "=" * 50)
    print("🔧 Dynamic Parser - CLI Fallback Mode")
    print("=" * 50)
    print("GUI mode failed. Starting command-line interface...")

    try:
        from varchiver.utils.dynamic_parser import parse_anything, detect_format

        while True:
            print("\nOptions:")
            print("1. Parse content from clipboard/input")
            print("2. Detect format only")
            print("3. Parse file")
            print("4. Exit")

            choice = input("\nEnter choice (1-4): ").strip()

            if choice == "1":
                print("Enter/paste your content (Ctrl+D or empty line to finish):")
                lines = []
                try:
                    while True:
                        line = input()
                        if not line:
                            break
                        lines.append(line)
                except EOFError:
                    pass

                content = "\n".join(lines)
                if content:
                    result = parse_anything(content)
                    print(f"\nFormat: {result.format_type.name}")
                    print(f"Success: {result.is_successful}")
                    if result.is_successful:
                        print(
                            "Data preview:",
                            str(result.data)[:200] + "..."
                            if len(str(result.data)) > 200
                            else str(result.data),
                        )
                    else:
                        print("Errors:", result.errors)

            elif choice == "2":
                content = input("Enter content to analyze: ")
                if content:
                    detection = detect_format(content)
                    print(f"Detected format: {detection.format_type.name}")
                    print(f"Confidence: {detection.confidence:.2f}")
                    print("Indicators:", detection.indicators)

            elif choice == "3":
                file_path = input("Enter file path: ")
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    result = parse_anything(content)
                    print(f"\nFormat: {result.format_type.name}")
                    print(f"Success: {result.is_successful}")
                    if result.is_successful:
                        print(
                            "Data keys:",
                            list(result.data.keys())
                            if isinstance(result.data, dict)
                            else "Not a dictionary",
                        )
                    else:
                        print("Errors:", result.errors)

                except Exception as e:
                    print(f"Error reading file: {e}")

            elif choice == "4":
                print("Goodbye!")
                break

            else:
                print("Invalid choice. Please try again.")

    except ImportError:
        print("Error: Dynamic parser modules not available.")
        print("Please check your VArchiver installation.")


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description="Launch VArchiver Dynamic Anything Parser",
        epilog="""
Examples:
  %(prog)s                              # Launch GUI
  %(prog)s --file data.toon             # Launch GUI with file loaded
  %(prog)s --demo                       # Launch with demo data
  %(prog)s --cli                        # Force CLI mode
  %(prog)s --check-deps                 # Check dependencies only
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--file", "-f", help="Load specified file on startup")
    parser.add_argument(
        "--demo", "-d", action="store_true", help="Launch in demo mode with sample data"
    )
    parser.add_argument(
        "--cli", "-c", action="store_true", help="Force command-line interface mode"
    )
    parser.add_argument(
        "--check-deps", action="store_true", help="Check dependencies and exit"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        print(f"VArchiver Dynamic Parser v1.0.0")
        print(f"Python: {sys.version}")
        print(f"Working directory: {Path.cwd()}")
        print(f"Script location: {Path(__file__).parent}")

    # Check dependencies
    if args.check_deps:
        print("Checking dependencies...")
        if check_dependencies():
            print("✅ All dependencies are available!")
            return 0
        else:
            print("❌ Some dependencies are missing.")
            return 1

    # Force CLI mode
    if args.cli:
        launch_fallback_cli()
        return 0

    # Try GUI mode
    success = launch_gui(initial_file=args.file, demo_mode=args.demo)

    if not success:
        print("\nGUI mode failed. Would you like to try CLI mode? (y/n): ", end="")
        try:
            response = input().strip().lower()
            if response in ("y", "yes"):
                launch_fallback_cli()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")

    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)
