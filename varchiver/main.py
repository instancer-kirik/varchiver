#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import argparse

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from .widgets.main_widget import MainWidget
from .utils.archive_utils import get_archive_type
from .utils.project_constants import PROJECT_CONFIGS

def parse_args(args):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Varchiver - Advanced Archive Management Tool')
    parser.add_argument('files', nargs='*', help='Files or directories to archive/extract')
    parser.add_argument('--extract', '-x', action='store_true', help='Extract mode')
    parser.add_argument('--browse', '-b', action='store_true', help='Browse archive contents')
    parser.add_argument('--output', '-o', help='Output directory for extraction')
    parser.add_argument('--password', '-p', help='Password for encrypted archives')
    parser.add_argument('--compression', '-c', type=int, choices=range(0, 10), default=5,
                       help='Compression level (0-9, default: 5)')
    parser.add_argument('--skip-patterns', '-s', nargs='+', help='Patterns to skip')
    parser.add_argument('--collision', choices=['skip', 'overwrite', 'rename'],
                       default='skip', help='Collision handling strategy')
    parser.add_argument('--preserve-permissions', action='store_true',
                       help='Preserve file permissions')
    return parser.parse_args(args)

def main(args=None):
    """Main entry point for Varchiver"""
    if args is None:
        args = sys.argv[1:]

    # Parse command line arguments
    args = parse_args(args)

    # Create Qt application if not already created
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setApplicationName(PROJECT_CONFIGS['name'])
        app.setApplicationVersion(PROJECT_CONFIGS['version'])
        app.setStyle('Fusion')
        
        # Set application icon
        icon = QIcon.fromTheme('archive-manager', QIcon.fromTheme('package'))
        app.setWindowIcon(icon)

    # Create main widget
    widget = MainWidget()
    widget.setWindowIcon(app.windowIcon())
    widget.show()

    # Handle command line arguments
    if args.files:
        if args.extract:
            # Extract mode
            if len(args.files) != 1:
                print("Error: Extract mode requires exactly one archive file", file=sys.stderr)
                return 1
            archive_file = args.files[0]
            if not os.path.isfile(archive_file):
                print(f"Error: Archive file not found: {archive_file}", file=sys.stderr)
                return 1
            widget.extract_archive(
                archive_file,
                output_dir=args.output,
                password=args.password,
                skip_patterns=args.skip_patterns,
                collision_strategy=args.collision,
                preserve_permissions=args.preserve_permissions
            )
        elif args.browse:
            # Browse mode
            if len(args.files) != 1:
                print("Error: Browse mode requires exactly one archive file", file=sys.stderr)
                return 1
            archive_file = args.files[0]
            if not os.path.isfile(archive_file):
                print(f"Error: Archive file not found: {archive_file}", file=sys.stderr)
                return 1
            widget._open_archive(archive_file, password=args.password)
        else:
            # Handle files passed from file manager
            valid_files = []
            for file_path in args.files:
                if os.path.isfile(file_path):
                    # Check if it's an archive file
                    archive_type = get_archive_type(file_path)
                    if archive_type:
                        valid_files.append(file_path)
            
            if valid_files:
                # Open first file and queue the rest
                widget._open_archive(valid_files[0])
                
                # Queue remaining files for extraction if any
                if len(valid_files) > 1:
                    for file_path in valid_files[1:]:
                        extraction_info = {
                            'archive_name': file_path,
                            'output_dir': os.path.dirname(file_path),
                            'password': args.password,
                            'collision_strategy': args.collision or 'skip',
                            'preserve_permissions': args.preserve_permissions,
                            'skip_patterns': args.skip_patterns
                        }
                        widget.extraction_queue.append(extraction_info)
                    widget.start_extract_button.setEnabled(True)
                    widget.update_status(f"Queued {len(valid_files)-1} archives for extraction")

    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
