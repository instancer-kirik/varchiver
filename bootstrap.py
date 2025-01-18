#!/usr/bin/env python3
import sys
import os
import signal
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel
from PyQt6.QtGui import QIcon, QFont, QPixmap
from PyQt6.QtCore import Qt, QTimer

def signal_handler(signum, frame):
    """Handle interrupts by properly shutting down the application"""
    print("\nReceived interrupt signal. Shutting down...")
    app = QApplication.instance()
    if app:
        # Get the main window
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'handle_interrupt'):
                widget.handle_interrupt()
                break
        app.quit()

def main():
    """Bootstrap entry point that imports and runs the main application"""
    try:
        # Add the parent directory to Python path to find the main module
        parent_dir = str(Path(__file__).resolve().parent.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Import project constants first
        from varchiver.utils.project_constants import PROJECT_CONFIGS

        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName(PROJECT_CONFIGS['name'])
        app.setApplicationVersion(PROJECT_CONFIGS['version'])
        app.setStyle('Fusion')
        
        # Set application icon
        icon = QIcon.fromTheme('archive-manager', QIcon.fromTheme('package'))
        app.setWindowIcon(icon)

        # Create and show splash screen
        splash_pixmap = QPixmap(32, 32)  # Create a blank pixmap
        splash_pixmap.fill(Qt.GlobalColor.white)  # Fill with white background
        splash = QSplashScreen(splash_pixmap)
        
        # Add loading text to splash screen
        splash_label = QLabel(splash)
        splash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        splash_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 14px;
                padding: 10px;
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        splash_label.setText("Loading Varchiver...")
        splash_label.adjustSize()
        splash.resize(splash_label.size())
        splash.show()
        
        # Process events to show splash immediately
        app.processEvents()

        # Import main widget (this is where the delay happens)
        if "--release" in sys.argv:
            from varchiver.utils.release_manager import ReleaseManager
            widget = ReleaseManager()
        else:
            from varchiver.widgets.main_widget import MainWidget
            widget = MainWidget()
        
        widget.setWindowIcon(icon)
        
        # Show main window and close splash after a short delay
        def show_main():
            widget.show()
            splash.finish(widget)
        
        QTimer.singleShot(1, show_main)  # Show main window after 1 second
        
        # Start the event loop
        return app.exec()
        
    except Exception as e:
        print(f"Bootstrap Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    sys.exit(main())
