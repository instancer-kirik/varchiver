#!/usr/bin/env python3
"""
Test script for the CSV Viewer/Editor Widget
"""

import sys
import os
import csv
import json
import tempfile
from pathlib import Path

# Add the varchiver directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt

# Import the CSV viewer widget
from varchiver.widgets.csv_viewer import CsvViewerWidget


def create_sample_csv_files():
    """Create sample CSV files with different structures for testing"""
    temp_dir = Path(tempfile.gettempdir()) / "csv_viewer_test"
    temp_dir.mkdir(exist_ok=True)

    sample_files = []

    # Sample 1: Simple inventory
    inventory_csv = temp_dir / "inventory.csv"
    with open(inventory_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['item', 'quantity', 'price', 'location'])
        writer.writeheader()
        writer.writerows([
            {'item': 'Plasma Rifle', 'quantity': '5', 'price': '1200', 'location': 'Armory'},
            {'item': 'Energy Cell', 'quantity': '150', 'price': '25', 'location': 'Storage'},
            {'item': 'Med Kit', 'quantity': '30', 'price': '50', 'location': 'Medical Bay'},
            {'item': 'Scanner', 'quantity': '8', 'price': '800', 'location': 'Science Lab'}
        ])
    sample_files.append(inventory_csv)

    # Sample 2: Contact list
    contacts_csv = temp_dir / "contacts.csv"
    with open(contacts_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'faction', 'role', 'location', 'notes'])
        writer.writeheader()
        writer.writerows([
            {'name': 'Commander Silva', 'faction': 'United Systems', 'role': 'Military Leader',
             'location': 'Command Station', 'notes': 'Coordinates fleet operations'},
            {'name': 'Dr. Chen', 'faction': 'Lokex Frame', 'role': 'Engineer',
             'location': 'Research Facility', 'notes': 'Specializes in gravity-tech'},
            {'name': 'Trader Voss', 'faction': 'Independent', 'role': 'Merchant',
             'location': 'Trading Post', 'notes': 'Deals in rare materials'}
        ])
    sample_files.append(contacts_csv)

    # Sample 3: Mission log
    missions_csv = temp_dir / "missions.csv"
    with open(missions_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'title', 'status', 'priority', 'description'])
        writer.writeheader()
        writer.writerows([
            {'id': 'M001', 'title': 'Artifact Recovery', 'status': 'Active', 'priority': 'High',
             'description': 'Recover ancient technology from Devast Vale ruins'},
            {'id': 'M002', 'title': 'Trade Route Patrol', 'status': 'Completed', 'priority': 'Medium',
             'description': 'Escort merchant convoy through Shelse region'},
            {'id': 'M003', 'title': 'Diplomatic Meeting', 'status': 'Pending', 'priority': 'Low',
             'description': 'Establish contact with Feap Wardens faction'}
        ])
    sample_files.append(missions_csv)

    # Sample 4: Large dataset for testing performance
    large_csv = temp_dir / "large_dataset.csv"
    with open(large_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'name', 'value', 'category', 'timestamp'])
        writer.writeheader()
        for i in range(1000):
            writer.writerow({
                'id': f'ID{i:04d}',
                'name': f'Item {i}',
                'value': str(i * 10 + 100),
                'category': ['Alpha', 'Beta', 'Gamma', 'Delta'][i % 4],
                'timestamp': f'2024-01-{(i % 30) + 1:02d}T10:00:00'
            })
    sample_files.append(large_csv)

    # Sample 5: JSON database for status inference testing
    json_db = temp_dir / "item_database.json"
    with open(json_db, 'w', encoding='utf-8') as f:
        json.dump({
            "items": [
                {
                    "id": "plasma_rifle_001",
                    "name": "Plasma Rifle",
                    "description": "High-energy plasma projectile weapon",
                    "tech_tier": 3,
                    "category": "Weapon",
                    "properties": {"damage": 150, "range": 500},
                    "blueprint": {"materials": ["plasma_core", "metal_frame"]},
                    "crafting_recipe_id": "recipe_plasma_rifle"
                },
                {
                    "id": "energy_cell_001",
                    "name": "Energy Cell",
                    "description": "Portable energy storage unit",
                    "tech_tier": 1,
                    "category": "Power"
                },
                {
                    "id": "scanner_001",
                    "name": "Scanner",
                    "description": "Multi-purpose scanning device"
                }
            ]
        }, f, indent=2)
    sample_files.append(json_db)

    return sample_files


class TestWindow(QMainWindow):
    """Main test window for CSV Viewer"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV Viewer/Editor Test")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Quick access buttons
        self.create_quick_access_toolbar(layout)

        # CSV Viewer widget
        self.csv_viewer = CsvViewerWidget()
        layout.addWidget(self.csv_viewer)

        # Connect signals
        self.csv_viewer.file_changed.connect(self.on_file_changed)
        self.csv_viewer.data_changed.connect(self.on_data_changed)

        # Create sample files
        self.sample_files = create_sample_csv_files()

    def create_quick_access_toolbar(self, layout):
        """Create toolbar with quick access to sample files"""
        toolbar_layout = QHBoxLayout()

        # Sample file buttons
        sample_files_info = [
            ("Load Inventory", 0, "Simple 4-column inventory data"),
            ("Load Contacts", 1, "Contact list with notes"),
            ("Load Missions", 2, "Mission log with status tracking"),
            ("Load Large Dataset", 3, "1000 rows for performance testing")
        ]

        for text, index, tooltip in sample_files_info:
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda checked, i=index: self.load_sample_file(i))
            toolbar_layout.addWidget(btn)

        toolbar_layout.addStretch()

        # Existing CSV files
        existing_files_info = [
            ("Load Tech Terms Queue", "varchiver/inventory/data/tech_terms_queue.csv"),
            ("Load World Glossary", "varchiver/inventory/world_glossary.csv")
        ]

        for text, file_path in existing_files_info:
            btn = QPushButton(text)
            btn.setToolTip(f"Load {file_path}")
            btn.clicked.connect(lambda checked, path=file_path: self.load_existing_file(path))
            toolbar_layout.addWidget(btn)

        toolbar_layout.addStretch()

        # Feature testing buttons
        features_info = [
            ("Set Test Database", 4, "Load sample JSON database for status inference"),
            ("Demo Filters", None, "Show filter widget usage"),
            ("Demo Comparison", None, "Show CSV comparison features")
        ]

        for text, index, tooltip in features_info:
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            if index is not None:
                btn.clicked.connect(lambda checked, i=index: self.load_sample_file(i))
            else:
                if "Filters" in text:
                    btn.clicked.connect(self.demo_filters)
                elif "Comparison" in text:
                    btn.clicked.connect(self.demo_comparison)
            toolbar_layout.addWidget(btn)

        layout.addLayout(toolbar_layout)

    def load_sample_file(self, index):
        """Load a sample CSV file"""
        if 0 <= index < len(self.sample_files):
            file_path = self.sample_files[index]
            self.csv_viewer.load_csv_file(file_path)

    def load_existing_file(self, file_path):
        """Load an existing CSV file"""
        full_path = Path(__file__).parent / file_path
        if full_path.exists():
            self.csv_viewer.load_csv_file(full_path)
        else:
            print(f"File not found: {full_path}")

    def on_file_changed(self, file_path):
        """Handle file change"""
        print(f"Loaded file: {file_path}")

    def on_data_changed(self):
        """Handle data change"""
        print("Data modified")

    def demo_filters(self):
        """Demonstrate filter functionality"""
        if not self.csv_viewer.model or not self.csv_viewer.model.rows:
            print("Load a CSV file first to demo filters")
            return

        print("\n=== FILTER DEMO ===")
        print("1. Try typing in the 'Global Search' box - searches all columns")
        print("2. Use column-specific filters in the left panel")
        print("3. Try different filter types: contains, equals, starts with, ends with")
        print("4. Enable/disable individual column filters")
        print("5. Watch the status bar update with filter counts")

    def demo_comparison(self):
        """Demonstrate CSV comparison functionality"""
        print("\n=== COMPARISON DEMO ===")
        print("1. Load a CSV file first")
        print("2. Click 'Compare Files' button in the toolbar")
        print("3. Select another CSV file to compare against")
        print("4. View the comparison results showing differences")
        print("5. Export missing records if needed")
        print("Note: For different column structures, the tool handles flexible mapping")


def main():
    """Main test function"""
    print("Starting CSV Viewer/Editor Test...")

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Create and show test window
    window = TestWindow()
    window.show()

    print("CSV Viewer Test Window created. Use the interface to:")
    print("")
    print("== QUICK ACCESS SAMPLES ==")
    print("• Click 'Load Inventory' - Simple 4-column product inventory")
    print("• Click 'Load Contacts' - Contact list with faction and notes")
    print("• Click 'Load Missions' - Mission tracking with status")
    print("• Click 'Load Large Dataset' - 1000 rows for performance testing")
    print("• Click 'Set Test Database' - Load JSON database for status inference")
    print("")
    print("== EXISTING PROJECT FILES ==")
    print("• Click 'Load Tech Terms Queue' - Your existing terms queue")
    print("• Click 'Load World Glossary' - Your existing world glossary")
    print("")
    print("== CORE FUNCTIONALITY ==")
    print("1. **Schema-Agnostic Loading**: Works with any CSV structure")
    print("2. **CSV Preview**: Shows file structure before loading")
    print("3. **Row Operations**: Add/Edit/Delete rows while preserving structure")
    print("4. **Add Row**: Creates new row with same columns as existing data")
    print("5. **Edit Row**: Double-click or select + Edit for full-form editing")
    print("6. **Save Changes**: Maintains original CSV format and structure")
    print("")
    print("== NEW ADVANCED FEATURES ==")
    print("7. **Live Filtering**: Left panel with global search + column filters")
    print("   - Global search across all columns")
    print("   - Column-specific filters (contains, equals, starts/ends with)")
    print("   - Enable/disable individual filters")
    print("   - Real-time filter status display")
    print("")
    print("8. **CSV Comparison**: Compare files with different structures")
    print("   - Click 'Compare Files' to compare with another CSV")
    print("   - Handles different column layouts automatically")
    print("   - Export missing records")
    print("   - Detailed comparison reports")
    print("")
    print("9. **Status Inference**: Connect CSV to JSON databases")
    print("   - Click 'Set Database' to load JSON item database")
    print("   - Automatically infer implementation status:")
    print("     * 'implemented' = exists in JSON with full specs")
    print("     * 'partial' = exists in JSON but incomplete")
    print("     * 'conceptual' = detailed CSV entry but no JSON item")
    print("     * 'pending' = basic CSV entry only")
    print("")
    print("== KEYBOARD SHORTCUTS ==")
    print("• Ctrl+O: Open file (with preview)")
    print("• Ctrl+S: Save file")
    print("• Ctrl+N: Add new row")
    print("• Enter: Edit selected row")
    print("• Delete: Delete selected rows")
    print("")
    print("== COMPLETE TEST SCENARIOS ==")
    print("1. **Structure Flexibility**: Load different CSV structures - notice adaptation")
    print("2. **Data Operations**: Add/edit/delete rows - maintains structure perfectly")
    print("3. **Filtering**: Use left panel filters - try global + column filters")
    print("4. **Comparison**: Load inventory.csv, then compare with contacts.csv")
    print("5. **Status Inference**: Load inventory.csv, set test database, see status")
    print("6. **Performance**: Load large dataset - test filtering and scrolling")
    print("7. **File Preview**: Use Ctrl+O - see structure preview before loading")
    print("")
    print("== MODULAR ARCHITECTURE BENEFITS ==")
    print("• **CsvDataModel**: Pure data handling, no UI coupling")
    print("• **CsvFilterWidget**: Reusable filtering component")
    print("• **CsvComparison**: Standalone comparison logic")
    print("• **StatusInferenceModule**: Pluggable status detection")
    print("• **CsvPreviewDialog**: File analysis before loading")
    print("• Total: ~1400 lines vs 1175-line monolith (better organized)")
    print("• Clean separation enables easy testing and future D port")

    # Create sample files info
    temp_dir = Path(tempfile.gettempdir()) / "csv_viewer_test"
    print(f"\nSample CSV files created in: {temp_dir}")

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
