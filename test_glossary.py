#!/usr/bin/env python3
"""
Test script for the GlossaryManagerWidget
"""

import sys
import os
from pathlib import Path

# Add the varchiver directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

# Import the glossary manager widget
from varchiver.widgets.glossary_manager_widget import GlossaryManagerWidget, GlossaryEntry


def load_csv_files():
    """Load glossary data from available CSV files"""
    glossary_data = {}

    # Define potential CSV file locations
    csv_files = [
        Path(__file__).parent / "varchiver" / "inventory" / "data" / "tech_terms_queue.csv",
        Path(__file__).parent.parent / "loreum" / "data" / "world_glossary.csv",
    ]

    for csv_file in csv_files:
        if csv_file.exists():
            print(f"Loading {csv_file}")
            try:
                import csv
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        term = row.get('term', '').strip()
                        if term:
                            related_terms = []
                            if 'related_terms' in row and row['related_terms']:
                                related_terms = [t.strip() for t in row['related_terms'].split(';') if t.strip()]

                            entry = GlossaryEntry(
                                term=term,
                                entry_type=(row.get('type') or '').strip(),
                                category=(row.get('category') or '').strip(),
                                description=(row.get('description') or '').strip(),
                                source=(row.get('source') or '').strip(),
                                related_terms=related_terms,
                                etymology_notes=(row.get('etymology_notes') or '').strip()
                            )
                            glossary_data[term] = entry
            except Exception as e:
                print(f"Error loading {csv_file}: {e}")
        else:
            print(f"CSV file not found: {csv_file}")

    # If no CSV files loaded, create minimal sample data
    if not glossary_data:
        print("No CSV files found, creating minimal sample data")
        sample_entry = GlossaryEntry(
            term="Sample Term",
            entry_type="Core Technology",
            category="Foundation",
            description="This is a sample entry for testing",
            source="test",
            related_terms=[],
            etymology_notes="Sample data"
        )
        glossary_data["Sample Term"] = sample_entry

    return glossary_data


class TestWindow(QMainWindow):
    """Main test window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Glossary Manager Test")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create glossary manager widget
        self.glossary_manager = GlossaryManagerWidget()
        layout.addWidget(self.glossary_manager)

        # Load data from CSV files
        csv_data = load_csv_files()
        self.glossary_manager.set_glossary_data(csv_data)

        print(f"Loaded {len(csv_data)} entries from CSV files")
        print("Loaded entries:")
        for term in sorted(csv_data.keys())[:10]:  # Show first 10 terms
            print(f"  - {term}")
        if len(csv_data) > 10:
            print(f"  ... and {len(csv_data) - 10} more")


def main():
    """Main test function"""
    print("Starting Glossary Manager Test...")

    app = QApplication(sys.argv)

    # Set application style (optional)
    app.setStyle('Fusion')

    # Create and show test window
    window = TestWindow()
    window.show()

    print("Test window created. Use the interface to:")
    print("1. View the sample glossary entries")
    print("2. Try adding new entries")
    print("3. Edit existing entries")
    print("4. Test search and filtering")
    print("5. Export/import CSV files")
    print("6. Test JSON save/load functionality")
    print("7. INFERRED STATUS: Click 'Set Item Database' to point to a JSON file")
    print("   - Status will be automatically inferred:")
    print("   - 'implemented' = term exists in JSON with full specs")
    print("   - 'partial' = exists in JSON but incomplete")
    print("   - 'conceptual' = detailed glossary entry but no JSON item")
    print("   - 'pending' = basic glossary entry only")
    print("   - 'unknown' = no database set")
    print("   - Status filter will update automatically with inferred values")

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
