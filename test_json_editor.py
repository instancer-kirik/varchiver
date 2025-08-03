#!/usr/bin/env python3
"""
Test script for the improved JsonEditorWidget
"""

import sys
import os
import json
from pathlib import Path

# Add the varchiver directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox
from PyQt6.QtCore import Qt

# Import the JSON editor widget
from varchiver.widgets.json_editor_widget import JsonEditorWidget


def create_sample_json_data():
    """Create sample JSON data for testing improved features"""
    return {
        "metadata": {
            "name": "Sample Item Database",
            "version": "1.0",
            "description": "This is a sample JSON file for testing the improved JSON editor features. It contains various field types including long descriptions, enum fields, and arrays with objects that have IDs."
        },
        "items": [
            {
                "id": "resonator_t1",
                "name": "Basic Resonator",
                "description": "A simple harmonic resonator for basic frequency matching. This device represents the foundational technology that enabled early space exploration and communication systems across the United Systems territories.",
                "tech_tier": "Tier 1",
                "energy_type": "Resonant",
                "category": "Modular",
                "rarity": "common",
                "status": "implemented",
                "origin_faction": "United Systems",
                "legal_status": "Legal Globally",
                "lore_notes": "First generation resonance technology. Widely adopted due to its simplicity and reliability in early space exploration. These modules formed the backbone of early sensor arrays and communication systems before more advanced focusing techniques were developed. The technology was pioneered by the Resonance Research Division of the United Systems Scientific Council in the early expansion era.",
                "properties": {
                    "durability": 100,
                    "weight": 2.5,
                    "power_draw": 15
                }
            },
            {
                "id": "magitek_core_t2",
                "name": "Advanced Magitek Core",
                "description": "Sophisticated core integrating magical and technological energies for enhanced system performance and mystical applications.",
                "tech_tier": "Tier 2",
                "energy_type": "Magitek",
                "category": "Modular",
                "rarity": "uncommon",
                "status": "implemented",
                "origin_faction": "Nethbound",
                "legal_status": "Restricted",
                "lore_notes": "Advanced integration technology developed by the Nethbound Enclaves. Represents a breakthrough in mana-tech fusion, allowing for unprecedented spell stability and energy conversion efficiency.",
                "properties": {
                    "durability": 85,
                    "weight": 4.2,
                    "power_draw": 35
                }
            },
            {
                "id": "gravitic_field_t3",
                "name": "Elite Gravitic Field Generator",
                "description": "Powerful device for precise gravitational field manipulation, enabling advanced spatial control and quantum stability applications.",
                "tech_tier": "Tier 3",
                "energy_type": "Gravitic",
                "category": "Modular",
                "rarity": "rare",
                "status": "implemented",
                "origin_faction": "Lokex Frame",
                "legal_status": "Restricted",
                "lore_notes": "High-tier gravity control technology exclusive to the Lokex Frame engineering corps. Requires specialized training and certification to operate safely.",
                "properties": {
                    "durability": 60,
                    "weight": 8.7,
                    "power_draw": 75
                }
            }
        ],
        "factions": [
            {
                "id": "united_systems",
                "name": "United Systems",
                "type": "Government",
                "status": "active",
                "description": "Primary governing body overseeing most inhabited systems and trade routes in known space."
            },
            {
                "id": "nethbound",
                "name": "Nethbound Enclaves",
                "type": "Mystical Order",
                "status": "active",
                "description": "Magic-tech fusion specialists operating from hidden enclaves throughout the outer systems."
            }
        ],
        "settings": {
            "max_inventory_slots": 50,
            "default_currency": "zern",
            "debug_mode": False,
            "version_number": 1.2
        }
    }


class TestJsonEditorWindow(QMainWindow):
    """Main test window for JSON editor"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON Editor Test - Improved Features")
        self.setGeometry(100, 100, 1400, 900)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create JSON editor widget
        self.json_editor = JsonEditorWidget()
        layout.addWidget(self.json_editor)

        # Load sample data
        sample_data = create_sample_json_data()
        self.json_editor._data = sample_data
        self.json_editor._current_file_path = "sample_test_data.json"
        self.json_editor.populate_tree()

        print("JSON Editor Test loaded with sample data")
        print("\nTest the following new features:")
        print("1. ARRAY INDICES WITH IDs: Look at the 'items' array - indices now show like '0 [resonator_t1]'")
        print("2. CONTEXT MENU: Right-click on any field value to see options")
        print("3. TEXT DIALOG: Right-click on 'description' or 'lore_notes' fields for dialog editor")
        print("4. DROPDOWN MENUS: Right-click on fields like 'rarity', 'status', 'tech_tier' for predefined options")
        print("5. ENUM FIELDS: Try fields like 'energy_type', 'origin_faction', 'legal_status'")
        print("\nSample items loaded:")
        for item in sample_data.get('items', []):
            print(f"  - {item.get('id', 'unknown')}: {item.get('name', 'unnamed')}")


def main():
    """Main test function"""
    print("Starting JSON Editor Test (Improved Features)...")

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Create and show test window
    window = TestJsonEditorWindow()
    window.show()

    print("\nJSON Editor opened with test data.")
    print("Try expanding the tree and testing the new features!")

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
