#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import argparse

from PyQt6.QtWidgets import QApplication

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

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(PROJECT_CONFIGS['name'])
    app.setApplicationVersion(PROJECT_CONFIGS['version'])

    # Create main widget
    widget = MainWidget()
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
            widget.browse_archive(
                archive_file,
                password=args.password
            )
        else:
            # Archive mode
            # Verify files exist
            for file in args.files:
                if not os.path.exists(file):
                    print(f"Error: File not found: {file}", file=sys.stderr)
                    return 1
            # If output is specified, use it as archive name
            archive_name = args.output if args.output else None
            widget.compress_files(
                args.files,
                archive_name=archive_name,
                password=args.password,
                compression_level=args.compression,
                skip_patterns=args.skip_patterns,
                collision_strategy=args.collision
            )

    return app.exec()
