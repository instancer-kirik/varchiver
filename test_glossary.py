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


def create_sample_csv_files():
    """Create sample CSV files with different structures for testing flexible loading"""
    import csv
    import tempfile

    # Create temporary directory for sample files
    temp_dir = Path(tempfile.gettempdir()) / "varchiver_csv_test"
    temp_dir.mkdir(exist_ok=True)

    # Sample CSV 1: Standard glossary format
    standard_csv = temp_dir / "standard_glossary.csv"
    with open(standard_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['term', 'type', 'category', 'description', 'source'])
        writer.writeheader()
        writer.writerows([
            {'term': 'Quantum Drive', 'type': 'Technology', 'category': 'Propulsion',
             'description': 'Advanced faster-than-light propulsion system', 'source': 'standard'},
            {'term': 'Neural Interface', 'type': 'Technology', 'category': 'Computing',
             'description': 'Direct brain-computer interface technology', 'source': 'standard'}
        ])

    # Sample CSV 2: Different column names
    alt_csv = temp_dir / "alternative_format.csv"
    with open(alt_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'tech_type', 'classification', 'notes', 'origin'])
        writer.writeheader()
        writer.writerows([
            {'name': 'Plasma Cannon', 'tech_type': 'Weapon', 'classification': 'Energy Weapons',
             'notes': 'High-energy plasma projectile weapon', 'origin': 'alternative'},
            {'name': 'Shield Generator', 'tech_type': 'Defense', 'classification': 'Protective Systems',
             'notes': 'Energy-based protective barrier system', 'origin': 'alternative'}
        ])

    # Sample CSV 3: ID-based format
    id_csv = temp_dir / "id_based_format.csv"
    with open(id_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'title', 'tech_category', 'info', 'data_source'])
        writer.writeheader()
        writer.writerows([
            {'id': 'TECH001', 'title': 'Antimatter Engine', 'tech_category': 'Power Generation',
             'info': 'Clean antimatter-based power source', 'data_source': 'id_based'},
            {'id': 'TECH002', 'title': 'Holographic Display', 'tech_category': 'Interface',
             'info': 'Three-dimensional holographic projection system', 'data_source': 'id_based'}
        ])

    print(f"Created sample CSV files in {temp_dir}:")
    print(f"  1. {standard_csv.name} - Standard format (term, type, category, description, source)")
    print(f"  2. {alt_csv.name} - Alternative format (name, tech_type, classification, notes, origin)")
    print(f"  3. {id_csv.name} - ID-based format (id, title, tech_category, info, data_source)")

    return [standard_csv, alt_csv, id_csv]


def load_csv_files():
    """Load glossary data from available CSV files (legacy function for backward compatibility)"""
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

        # Create sample CSV files with different structures for testing
        sample_files = create_sample_csv_files()

        # Load data from CSV files (legacy method)
        csv_data = load_csv_files()
        self.glossary_manager.set_glossary_data(csv_data)

        print(f"Loaded {len(csv_data)} entries from CSV files")
        print("Loaded entries:")
        for term in sorted(csv_data.keys())[:10]:  # Show first 10 terms
            print(f"  - {term}")
        if len(csv_data) > 10:
            print(f"  ... and {len(csv_data) - 10} more")

        print(f"\nSample CSV files created for testing flexible loading:")
        for i, file_path in enumerate(sample_files, 1):
            print(f"  {i}. {file_path}")


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
    print("")
    print("== GLOSSARY MANAGEMENT (CSV-focused) ==")
    print("1. View the sample glossary entries")
    print("2. Try adding new entries")
    print("3. Edit existing entries")
    print("4. Test search and filtering")
    print("")
    print("== FLEXIBLE CSV LOADING ==")
    print("5. Click 'Open CSV File' to test flexible CSV loading:")
    print("   - Try loading the sample CSV files with different column structures")
    print("   - CSV structure preview shows detected columns and data")
    print("   - Column mapping dialog allows flexible field mapping")
    print("   - Supports different comparison keys (term, id, name, etc.)")
    print("")
    print("== CSV COMPARISON & ANALYSIS ==")
    print("6. Click 'Compare CSV Files' to test flexible comparison:")
    print("   - Compare CSV files with different column structures")
    print("   - Map columns independently for each file")
    print("   - Choose comparison key (term, id, name, etc.)")
    print("   - Export missing terms preserving original structure")
    print("")
    print("== JSON INTEGRATION ==")
    print("7. In main Varchiver: Switch to 'JSON Editor' mode to manage item databases")
    print("   - Use mode selector to switch between Glossary and JSON Editor modes")
    print("   - JSON Editor mode handles nested item data (properties, blueprints, etc.)")
    print("8. Click 'Set Item Database' to enable status inference:")
    print("   - Point to JSON item database for automatic status detection")
    print("   - 'implemented' = term exists in JSON with full specs")
    print("   - 'partial' = exists in JSON but incomplete")
    print("   - 'conceptual' = detailed glossary entry but no JSON item")
    print("   - 'pending' = basic glossary entry only")
    print("   - 'unknown' = no database set")
    print("")
    print("== ARCHITECTURE NOTES ==")
    print("- Main Varchiver has mode-based architecture:")
    print("  * 'Glossary' mode: CSV files only (flat, tabular glossary data)")
    print("  * 'JSON Editor' mode: JSON files only (nested item data)")
    print("  * Clean separation via modes prevents confusion")
    print("- This test runs Glossary Manager standalone for development/testing")
    print("- In production, use main Varchiver with mode switching")

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
